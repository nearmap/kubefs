import asyncio
import logging
from typing import Any, List, Optional

from kube.async_loop import AsyncLoop
from kube.channels.objects import OEvReceiver, create_oev_chan
from kube.config import Context
from kube.events.objects import Action, ObjectEvent
from kube.model.api_group import CoreV1
from kube.model.api_resource import ApiResource
from kube.model.selector import ObjectSelector


class SyncClusterFacade:
    def __init__(self, *, async_loop: AsyncLoop, context: Context, logger=None) -> None:
        self.async_loop = async_loop
        self.context = context
        self.logger = logger or logging.getLogger("facade")

    def list_api_resources(self) -> List[ApiResource]:
        async def list_resources():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            client = await cluster_loop.get_client()

            groups = [CoreV1]
            non_core_groups = await client.list_api_groups()
            groups.extend(non_core_groups)

            all_resources = []

            coros = [client.list_api_resources(group) for group in groups]
            resource_lists = await asyncio.gather(*coros)

            for resources in resource_lists:
                all_resources.extend(resources)

            return all_resources

        return self.async_loop.run_coro_until_completion(list_resources())

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
        oev_chan = create_oev_chan()

        async def start_watch():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            await cluster_loop.start_watch(selector, oev_chan.sender)

        self.async_loop.run_coro_until_completion(start_watch())
        return oev_chan.receiver

    def stop_watching(self, *, selector: ObjectSelector) -> None:
        async def stop_watch():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            await cluster_loop.stop_watch(selector)

        self.async_loop.run_coro_until_completion(stop_watch())

    def list_then_watch(self, *, selector: ObjectSelector) -> OEvReceiver:
        oev_chan = create_oev_chan()

        async def list_watch():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            client = await cluster_loop.get_client()

            items = []
            try:
                items = await client.list_objects(selector)
            except Exception as exc:
                event = ObjectEvent(
                    context=self.context,
                    action=Action.LISTED,
                    object=exc,
                )
                oev_chan.sender.send(event)
                return  # fail fast if list failed

            for item in items:
                event = ObjectEvent(
                    context=self.context, action=Action.LISTED, object=item
                )
                oev_chan.sender.send(event)

            await cluster_loop.start_watch(selector, oev_chan.sender)

        self.async_loop.launch_coro(list_watch())
        return oev_chan.receiver
