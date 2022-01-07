from typing import Optional

from kube import client
from kube.channels.objects import OEvReceiver
from kube.cluster_facade import SyncClusterFacade
from kube.model.api_resource import PodKind
from kube.model.client_params import LogStreamingParams
from kube.model.selector import ObjectSelector
from podview.model.model import ContainerModel, PodModel


class PodTarget:
    def __init__(self, pod: PodModel, container: ContainerModel) -> None:
        self.pod = pod
        self.container = container

        # the number of times we have streamed from this target
        self.streamed_count = 0
        # how many log lines to fetch from back in time when it's the first time
        # we stream from this target
        self.tail_lines_first_time = 100

        self.selector: Optional[ObjectSelector] = None
        self.oev_receiver: Optional[OEvReceiver] = None

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} pod={self.pod.name}, cont={self.container.name}>"

    def format_name(self) -> str:
        assert isinstance(self.selector, ObjectSelector)
        assert isinstance(self.selector.client_op_params, LogStreamingParams)

        lines = self.selector.client_op_params.tail_lines
        return f"{self.pod.name}/{self.container.name} (tail_lines: {lines})"

    def start_streaming(self, facade: SyncClusterFacade) -> None:
        tail_lines = self.tail_lines_first_time if self.streamed_count == 0 else 0
        client_op_params = LogStreamingParams(tail_lines=tail_lines)

        self.selector = ObjectSelector(
            res=PodKind,
            namespace=self.pod.namespace.current_value,
            podname=self.pod.name,
            contname=self.container.name,
            client_op_params=client_op_params,
        )

        self.oev_receiver = facade.start_stream_pod_logs(selector=self.selector)
        self.streamed_count += 1

    def stop_streaming(self, facade: SyncClusterFacade) -> None:
        assert isinstance(self.selector, ObjectSelector)

        facade.stop_stream_pod_logs(selector=self.selector)
        self.oev_receiver = None
