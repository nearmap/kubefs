import argparse
import fnmatch
import logging
import os
import time
from typing import List, Tuple
from urllib.parse import urlparse

from akube.model.object_model.kinds import Pod
from kube.channels.objects import OEvReceiver
from kube.events.objects import ObjectEvent
from podview.model.model import ScreenModel


class ModelUpdater:
    def __init__(
        self, receivers: List[OEvReceiver], args: argparse.Namespace, logger=None
    ) -> None:
        self.receivers = receivers
        self.args = args
        self.logger = logger or logging.getLogger(__name__)

    def parse_image(self, image_url) -> Tuple[str, str]:
        st = urlparse(image_url)

        path, _, hash = st.path.partition("@")
        _, _, digest = hash.partition(":")

        name = os.path.basename(path)
        return name, digest

    def update_model(self, model: ScreenModel, event: ObjectEvent) -> None:
        context = event.context
        pod = Pod(event.object)
        ts = event.time_created

        pod_app_name = pod.meta.labels.get("app")

        cluster_model = model.get_cluster(context)
        pod_model = cluster_model.get_pod(pod.meta.name)
        pod_model.phase.set(value=pod.status.phase, ts=ts)
        pod_model.start_time.set(value=pod.status.startTime, ts=ts)

        for cont in pod.status.containerStatuses:
            cont_image_name, cont_image_hash = self.parse_image(cont.imageID)

            container_model = pod_model.get_container(cont.name)
            container_model.ready.set(value=cont.ready, ts=ts)
            container_model.image_hash.set(value=cont_image_hash, ts=ts)
            container_model.restart_count.set(value=cont.restartCount, ts=ts)
            if cont.state:
                container_model.state.set(value=cont.state.key, ts=ts)

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
