from typing import Any, List, Optional

from akube.model.api_resource import ApiResource
from kube.channels.objects import OEvReceiver
from kube.config import Context


class SyncClusterFacade:
    def __init__(self, *, context: Context) -> None:
        self.context = context

    def list_api_resources(self) -> List[ApiResource]:
        pass

    def list_resources(self, *, apires: ApiResource) -> List[Any]:
        pass

    def get_resource(
        self, *, apires: ApiResource, namespace: Optional[str], name: str
    ) -> Optional[Any]:
        pass

    def start_watching(
        self, *, apires: ApiResource, namespace: Optional[str]
    ) -> OEvReceiver:
        pass

    def stop_watching(self, *, apires: ApiResource, namespace: Optional[str]) -> None:
        pass
