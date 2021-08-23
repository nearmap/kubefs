from typing import Any, List, Optional

from akube.async_loop import AsyncLoop
from akube.model.api_group import CoreV1
from akube.model.api_resource import ApiResource
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvReceiver, create_oev_chan
from kube.config import Context
from kube.events.objects import Action, ObjectEvent


class SyncClusterFacade:
    def __init__(self, *, async_loop: AsyncLoop, context: Context) -> None:
        self.async_loop = async_loop
        self.context = context

    def list_api_resources(self) -> List[ApiResource]:
        async def list_resources():
            cluster_loop = await self.async_loop.get_cluster_loop(self.context)
            client = await cluster_loop.get_client()

            # hamfisted solution to the problem of pods/nodes/events being used
            # by more than one api group
            names = set()

            all_resources = await client.list_api_resources(CoreV1)
            for resource in all_resources:
                names.add(resource.name)

            groups = await client.list_api_groups()
            for group in groups:
                resources = await client.list_api_resources(group)
                for resource in resources:
                    if resource.name in names:
                        continue

                    names.add(resource.name)
                    all_resources.append(resource)

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
