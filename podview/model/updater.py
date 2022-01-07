import argparse
import fnmatch
import logging
import os
import re
import time
from datetime import timedelta
from typing import List, Tuple
from urllib.parse import urlparse

from kube.channels.objects import OEvReceiver
from kube.config import Context
from kube.events.objects import Action, ObjectEvent
from kube.model.object_model.kinds import Pod
from kube.model.object_model.status import (
    ContainerStateRunning,
    ContainerStateTerminated,
    ContainerStateWaiting,
    ContainerStatus,
    ContainerStatusVariant,
)
from kube.tools.timekeeping import date_now
from podview.model.colors import ColorPicker
from podview.model.model import ClusterModel, ContainerModel, PodModel, ScreenModel


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

    # Model updates

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
                        if dt is None:
                            dt = cont.state.finishedAt
                        elif cont.state.finishedAt and cont.state.finishedAt > dt:
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
            if pod.status.message:
                model.message.set(value=pod.status.message, ts=ts)
            if pod.status.reason:
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

            started_at = None
            finished_at = None

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

                started_at = state.startedAt
                finished_at = state.finishedAt

            if dt is not None:
                ts = dt.timestamp()

            color = self.color_picker.get_for_container_state(state.key)

            model.state.set(
                value=state.key, ts=ts, is_terminal_state=is_terminal_state, color=color
            )
            model.exit_code.set(value=exit_code or 0, ts=ts)
            model.message.set(value=message or "", ts=ts)
            model.reason.set(value=reason or "", ts=ts)

            if started_at:
                model.started_at.set(value=started_at, ts=ts)
            if finished_at:
                model.finished_at.set(value=finished_at, ts=ts)

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
        pod_model.namespace.set(pod.meta.namespace, ts=ts)
        pod_model.creation_timestamp.set(value=pod.meta.creationTimestamp, ts=ts)
        if pod.meta.deletionTimestamp is not None:
            pod_model.deletion_timestamp.set(value=pod.meta.deletionTimestamp, ts=ts)
        self.update_pod_phase(event, pod, pod_model)

        conts = pod.status.initContainerStatuses + pod.status.containerStatuses
        for cont in conts:
            cont_image_name, cont_image_hash = self.parse_imageID(cont.imageID)
            cont_image_tag = self.parse_image(cont.image)

            container_model = pod_model.get_container(cont.name)
            container_model.variant.set(cont.variant, ts=ts)
            container_model.ready.set(value=cont.ready, ts=ts)
            if cont.started is not None:
                container_model.started.set(value=cont.started, ts=ts)
            container_model.image_hash.set(value=cont_image_hash, ts=ts)
            container_model.image_tag.set(value=cont_image_tag, ts=ts)
            container_model.restart_count.set(value=cont.restartCount, ts=ts)
            self.update_container_state(event, cont, container_model)

            if pod_app_name and cont_image_name.startswith(pod_app_name):
                pod_model.image_hash.set(value=cont_image_hash, ts=ts)
            elif cont.name.startswith(pod.meta.name):
                pod_model.image_hash.set(value=cont_image_hash, ts=ts)

    # Garbage collection

    def init_container_terminated_long_ago(self, cont: ContainerModel) -> bool:
        if (
            cont.variant.current_value == ContainerStatusVariant.INIT_CONTAINER
            and cont.state.current_value == "terminated"
            and cont.exit_code.current_value == 0
            and cont.finished_at.current_value is not None
            and date_now() - cont.finished_at.current_value > timedelta(hours=1)
        ):
            return True

        return False

    def pod_deleted_long_ago(self, pod: PodModel) -> bool:
        if (
            pod.phase.current_value == "deleted"
            and pod.deletion_timestamp.current_value is not None
            and date_now() - pod.deletion_timestamp.current_value > timedelta(hours=1)
        ):
            return True

        return False

    def garbage_collect(self, model: ScreenModel) -> None:
        for cluster in model.iter_clusters():
            for pod in cluster.iter_pods():
                # hide pods that were deleted >1h ago
                if self.pod_deleted_long_ago(pod):
                    pod.is_visible = False

                for cont in pod.iter_containers():
                    # hide init containers that terminated successfully >1h ago
                    if self.init_container_terminated_long_ago(cont):
                        cont.is_visible = False

    # Event processing

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

    def run(self, model: ScreenModel, timeout: float, drain_queue: bool = False):
        start_time = time.time()
        pause = max(timeout / 10, 0.001)

        while True:
            # draining mode
            if drain_queue:
                # if the size of every queues is >0 we stay in draining mode
                # and do not time out
                cum_size = 0
                for receiver in self.receivers:
                    cum_size += receiver.queue.qsize()

                # ... otherwise we exit draining mode and go into timeout mode
                if cum_size == 0:
                    drain_queue = False

            # timeout mode
            elif time.time() - start_time >= timeout:
                break

            # process each receiver queue
            for receiver in self.receivers:
                event = receiver.recv_nowait()
                if event and self.filter_event(event):
                    self.update_model(model, event)

            time.sleep(pause)

        # garbage collect in case anything in the model (either pre-existing or
        # just added in the update) should not be displayed
        self.garbage_collect(model)

        for receiver in self.receivers:
            self.logger.debug("receiver queue size: %r", receiver.queue.qsize())
