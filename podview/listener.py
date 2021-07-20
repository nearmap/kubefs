import time
import os
from typing import List, Tuple

from dateutil.parser import parse as parse_date
from urllib.parse import urlparse

from kube.channels.objects import OEvReceiver
from kube.events.objects import ObjectEvent
from podview.model import ScreenModel


class Listener:
    def __init__(self, receivers: List[OEvReceiver]) -> None:
        self.receivers = receivers
        self.screen: ScreenModel = ScreenModel()

    def parse_image(self, image_url) -> Tuple[str, str]:
        st = urlparse(image_url)

        path, _, hash = st.path.partition('@')
        _, _, digest = hash.partition(':')

        name = os.path.basename(path)
        return name, digest

    def update_view(self, event: ObjectEvent) -> None:
        context = event.context
        object = event.object
        ts = event.time_created

        assert object['kind'] == 'Pod'

        obj_meta = object["metadata"]
        obj_name = obj_meta["name"]

        obj_status = object["status"]
        obj_phase = obj_status["phase"]
        obj_start_time = parse_date(obj_status["startTime"])
        obj_cont_stats = obj_status['container_statuses']

        cluster = self.screen.get_cluster(context)
        pod = cluster.get_pod(obj_name)
        pod.phase.set(value=obj_phase, ts=ts)
        pod.start_time.set(value=obj_start_time, ts=ts)

        for cont in obj_cont_stats:
            cont_name = cont['name']
            cont_image_name, cont_image_hash = self.parse_image(cont['imageId'])
            cont_restarts = cont['restartCount']
            cont_state = list(cont['state'].keys())[0]

            cont = pod.get_container(cont_name)
            cont.image_hash.set(value=cont_image_hash, ts=ts)
            cont.state.set(value=cont_state, ts=ts)
            cont.restart_count.set(value=cont_restarts, ts=ts)

            if cont_image_name.startswith(obj_name):
                pod.image_hash.set(value=cont_image_hash, ts=ts)

    def run(self):
        for receiver in self.receivers:
            event = receiver.recv_nowait()
            if event:
                self.update_view(event)

        # use a time budget instead
        time.sleep(0.001)
