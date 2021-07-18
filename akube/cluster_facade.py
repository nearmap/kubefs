from typing import Any, List, Optional

from akube.async_loop import AsyncLoop
from akube.model.api_resource import ApiResource
from kube.channels.objects import OEvReceiver, create_oev_chan
from kube.config import Context


class SyncClusterFacade:
    def __init__(self, *, async_loop: AsyncLoop, context: Context) -> None:
        self.async_loop = async_loop
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

    def list(self) -> List[Any]:
        async def list_namespaces():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            client = await cluster_loop.get_client()
            items = await client.list_objects()
            return items

        return self.async_loop.run_coro_until_completion(list_namespaces())

    def watch(self) -> OEvReceiver:
        oev_sender, oev_receiver = create_oev_chan()

        async def watch_pods():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            client = await cluster_loop.get_client()
            loop = self.async_loop.get_loop()
            # TODO: this should be "tell cluster_loop to start a watch"
            loop.create_task(client.watch_objects(oev_sender=oev_sender))

        self.async_loop.launch_coro(watch_pods())
        return oev_receiver
