from typing import Optional

from kube.channels.objects import OEvReceiver
from kube.cluster_facade import SyncClusterFacade
from kube.model.api_resource import PodKind
from kube.model.selector import ObjectSelector
from podview.model.model import ContainerModel, PodModel


class PodTarget:
    def __init__(self, pod: PodModel, container: ContainerModel) -> None:
        self.pod = pod
        self.container = container

        self.selector: Optional[ObjectSelector] = None
        self.oev_receiver: Optional[OEvReceiver] = None

    def start_streaming(self, facade: SyncClusterFacade) -> None:
        self.selector = ObjectSelector(
            res=PodKind,
            namespace=self.pod.namespace.current_value,
            podname=self.pod.name,
            contname=self.container.name,
        )

        self.oev_receiver = facade.start_stream_pod_logs(selector=self.selector)

    def stop_streaming(self, facade: SyncClusterFacade) -> None:
        facade.stop_stream_pod_logs(selector=self.selector)
        self.oev_receiver = None
