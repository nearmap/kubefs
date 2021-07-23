import argparse
import fnmatch
import os
import time
from typing import List, Tuple
from urllib.parse import urlparse

from dateutil.parser import parse as parse_date

from akube.model.object_model import Pod
from kube.channels.objects import OEvReceiver
from kube.events.objects import ObjectEvent
from podview.model.model import ScreenModel


class ModelUpdater:
    def __init__(self, receivers: List[OEvReceiver], args: argparse.Namespace) -> None:
        self.receivers = receivers
        self.args = args

    def parse_image(self, image_url) -> Tuple[str, str]:
        st = urlparse(image_url)

        path, _, hash = st.path.partition("@")
        _, _, digest = hash.partition(":")

        name = os.path.basename(path)
        return name, digest

    def update_model(self, model: ScreenModel, event: ObjectEvent) -> None:
        context = event.context
        pod = event.object
        ts = event.time_created

        assert pod["kind"] == "Pod"

        pod_meta = pod["metadata"]
        pod_name = pod_meta["name"]
        pod_app_name = (pod_meta.get("labels") or {}).get("app")

        pod_status = pod["status"]
        pod_phase = pod_status["phase"]
        pod_start_time_val = pod_status.get("startTime")
        pod_start_time = pod_start_time_val and parse_date(pod_start_time_val)
        pod_cont_statuses = pod_status.get("containerStatuses") or []

        cluster_model = model.get_cluster(context)
        pod_model = cluster_model.get_pod(pod_name)
        pod_model.phase.set(value=pod_phase, ts=ts)
        pod_model.start_time.set(value=pod_start_time, ts=ts)

        for cont in pod_cont_statuses:
            cont_name = cont["name"]
            cont_ready = cont["ready"]
            cont_image_name, cont_image_hash = self.parse_image(cont["imageID"])
            cont_restarts = cont["restartCount"]

            cont_state_key = None
            cont_state = cont.get("state")
            if cont_state:
                cont_state_key = list(cont_state.keys())[0]

            container_model = pod_model.get_container(cont_name)
            container_model.ready.set(value=cont_ready, ts=ts)
            container_model.image_hash.set(value=cont_image_hash, ts=ts)
            container_model.restart_count.set(value=cont_restarts, ts=ts)
            container_model.state.set(value=cont_state_key, ts=ts)

            if pod_app_name and cont_image_name.startswith(pod_app_name):
                pod_model.image_hash.set(value=cont_image_hash, ts=ts)
            elif cont_name.startswith(pod_name):
                pod_model.image_hash.set(value=cont_image_hash, ts=ts)

    def filter_event(self, event: ObjectEvent) -> bool:
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
