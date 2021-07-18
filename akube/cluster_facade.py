from typing import Any, List, Optional

from akube.async_loop import AsyncLoop
from akube.model.api_resource import ApiResource
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvReceiver, create_oev_chan
from kube.config import Context


class SyncClusterFacade:
    def __init__(self, *, async_loop: AsyncLoop, context: Context) -> None:
        self.async_loop = async_loop
        self.context = context

    def list_api_resources(self) -> List[ApiResource]:
        pass

    def list_objects(self, *, selector: ObjectSelector) -> List[Any]:
        async def list_objects():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            client = await cluster_loop.get_client()
            items = await client.list_objects(selector)
            return items

        return self.async_loop.run_coro_until_completion(list_objects())

    def get_resource(
        self, *, apires: ApiResource, namespace: Optional[str], name: str
    ) -> Optional[Any]:
        pass

    def start_watching(self, *, selector: ObjectSelector) -> OEvReceiver:
        oev_sender, oev_receiver = create_oev_chan()

        async def start_watch():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            await cluster_loop.start_watch(selector, oev_sender)

        self.async_loop.run_coro_until_completion(start_watch())
        return oev_receiver

    def stop_watching(self, *, selector: ObjectSelector) -> None:
        async def stop_watch():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            await cluster_loop.stop_watch(selector)

        self.async_loop.run_coro_until_completion(stop_watch())
