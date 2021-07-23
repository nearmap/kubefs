import os
import time
from typing import List, Tuple
from urllib.parse import urlparse

from dateutil.parser import parse as parse_date

from kube.channels.objects import OEvReceiver
from kube.events.objects import ObjectEvent
from podview.model import ScreenModel


class Listener:
    def __init__(self, receivers: List[OEvReceiver]) -> None:
        self.receivers = receivers
        self.screen: ScreenModel = ScreenModel()

    def parse_image(self, image_url) -> Tuple[str, str]:
        st = urlparse(image_url)

        path, _, hash = st.path.partition("@")
        _, _, digest = hash.partition(":")

        name = os.path.basename(path)
        return name, digest

    def update_model(self, event: ObjectEvent) -> None:
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

        cluster_model = self.screen.get_cluster(context)
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

        lines = []
        lines.append(
            "%s    %s  %s (%s)    %s "
            % (
                cluster_model.context.short_name,
                pod_model.name,
                pod_model.phase.current_value,
                pod_model.phase.current_elapsed_pretty or "",
                pod_model.image_hash.current_value
                and pod_model.image_hash.current_value[:6]
                or "",
            )
        )
        for cont in pod_model.iter_containers():
            lines.append(
                "    %s  %s  %s"
                % (
                    cont.name,
                    cont.state.current_value,
                    cont.image_hash.current_value and cont.image_hash.current_value[:6],
                )
            )
        print("\n" + "\n".join(lines) + "\n")

    def run(self, timeout: float):
        start_time = time.time()

        while True:
            if time.time() - start_time >= timeout:
                break

            for receiver in self.receivers:
                event = receiver.recv_nowait()
                if event:
                    self.update_model(event)

            time.sleep(0.001)
