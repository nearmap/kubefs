import argparse
import fnmatch
import logging
import os
import time
from typing import List, Tuple
from urllib.parse import urlparse

from akube.model.object_model.kinds import Pod
from akube.model.object_model.status import (
    ContainerStateRunning,
    ContainerStateTerminated,
    ContainerStateWaiting,
    ContainerStatus,
)
from kube.channels.objects import OEvReceiver
from kube.config import Context
from kube.events.objects import Action, ObjectEvent
from podview.model.colors import ColorPicker
from podview.model.model import ContainerModel, PodModel, ScreenModel


class ModelUpdater:
    def __init__(
        self,
        contexts: List[Context],
        receivers: List[OEvReceiver],
        args: argparse.Namespace,
        logger=None,
    ) -> None:
        self.contexts = contexts
        self.receivers = receivers
        self.args = args
        self.logger = logger or logging.getLogger(__name__)

        self.color_picker = ColorPicker.get_instance()

    def parse_image(self, image_url) -> str:
        _, _, digest = image_url.partition(":")
        return digest

    def parse_imageID(self, image_url) -> Tuple[str, str]:
        st = urlparse(image_url)

        path, _, hash = st.path.partition("@")
        _, _, digest = hash.partition(":")

        name = os.path.basename(path)
        return name, digest

    def update_pod_phase(self, event: ObjectEvent, pod: Pod, model: PodModel) -> None:
        # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-phase

        phase = pod.status.phase
        if phase:
            phase = phase.lower()
            dt = None
            ts = event.time_created
            is_terminal_state = False

            if phase == "pending":
                dt = pod.meta.creationTimestamp
            elif phase == "running":
                dt = pod.status.startTime
            elif phase in ("succeeded", "failed", "unknown"):
                # we don't have an insightful timestamp at the pod level to use
                # reach into the container statuses for the most recent finishedAt
                for cont in pod.status.containerStatuses:
                    if isinstance(cont.state, ContainerStateTerminated):
                        if dt is None or cont.state.finishedAt > dt:
                            dt = cont.state.finishedAt

                is_terminal_state = True

            # deleted pods still show up in phase 'running'
            if event.action is Action.DELETED:
                phase = "deleted"
                dt = pod.meta.deletionTimestamp
                is_terminal_state = True

            if dt is not None:
                ts = dt.timestamp()

            color = self.color_picker.get_for_pod_phase(phase)

            model.phase.set(
                value=phase, ts=ts, is_terminal_state=is_terminal_state, color=color
            )
            model.message.set(value=pod.status.message, ts=ts)
            model.reason.set(value=pod.status.reason, ts=ts)

    def update_container_state(
        self, event: ObjectEvent, cont: ContainerStatus, model: ContainerModel
    ) -> None:
        # https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-states
        state = cont.state
        if state:
            dt = None
            ts = event.time_created
            is_terminal_state = False

            exit_code = None
            message = None
            reason = None

            if isinstance(state, ContainerStateWaiting):
                message = state.message
                reason = state.reason
            elif isinstance(state, ContainerStateRunning):
                dt = state.startedAt
            elif isinstance(state, ContainerStateTerminated):
                dt = state.finishedAt
                is_terminal_state = True

                exit_code = state.exitCode
                message = state.message
                reason = state.reason

            if dt is not None:
                ts = dt.timestamp()

            color = self.color_picker.get_for_container_state(state.key)

            model.state.set(
                value=state.key, ts=ts, is_terminal_state=is_terminal_state, color=color
            )
            model.exit_code.set(value=exit_code, ts=ts)
            model.message.set(value=message, ts=ts)
            model.reason.set(value=reason, ts=ts)

    def update_model(self, model: ScreenModel, event: ObjectEvent) -> None:
        context = event.context
        pod = Pod(event.object)
        ts = event.time_created

        pod_app_name = pod.meta.labels.get("app")

        cluster_model = model.get_cluster(context)
        cluster_model.name.set(
            value=context.short_name,
            ts=ts,
            color=self.color_picker.get_for_context(context),
        )

        pod_model = cluster_model.get_pod(pod.meta.name)
        pod_model.creation_timestamp.set(value=pod.meta.creationTimestamp, ts=ts)
        pod_model.deletion_timestamp.set(value=pod.meta.deletionTimestamp, ts=ts)
        self.update_pod_phase(event, pod, pod_model)

        for cont in pod.status.containerStatuses:
            cont_image_name, cont_image_hash = self.parse_imageID(cont.imageID)
            cont_image_tag = self.parse_image(cont.image)

            container_model = pod_model.get_container(cont.name)
            container_model.ready.set(value=cont.ready, ts=ts)
            container_model.started.set(value=cont.started, ts=ts)
            container_model.image_hash.set(value=cont_image_hash, ts=ts)
            container_model.image_tag.set(value=cont_image_tag, ts=ts)
            container_model.restart_count.set(value=cont.restartCount, ts=ts)
            self.update_container_state(event, cont, container_model)

            if pod_app_name and cont_image_name.startswith(pod_app_name):
                pod_model.image_hash.set(value=cont_image_hash, ts=ts)
            elif cont.name.startswith(pod.meta.name):
                pod_model.image_hash.set(value=cont_image_hash, ts=ts)

    def filter_event(self, event: ObjectEvent) -> bool:
        if isinstance(event.object, Exception):
            raise event.object  # re-raise as uncaught exception

        pod = Pod(event.object)
        app_name = pod.meta.labels.get("app")

        matches_name = fnmatch.fnmatch(pod.meta.name, self.args.pod)
        matches_app_name = False

        if app_name:
            matches_app_name = fnmatch.fnmatch(app_name, self.args.pod)

        return matches_name or matches_app_name

    def run(self, model: ScreenModel, timeout: float):
        start_time = time.time()
        pause = max(timeout / 10, 0.001)

        while True:
            if time.time() - start_time >= timeout:
                break

            for receiver in self.receivers:
                event = receiver.recv_nowait()
                if event and self.filter_event(event):
                    self.update_model(model, event)

            time.sleep(pause)
