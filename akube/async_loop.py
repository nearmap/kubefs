from akube.client import AsyncClient
import asyncio
from threading import Event, Thread
from typing import Dict

from akube.cluster_loop import AsyncClusterLoop
from kube.config import Context


class AsyncLoop:
    _instance = None

    def __init__(
        self, *, loop: asyncio.BaseEventLoop, initialized_event: Event
    ) -> None:
        self.loop = loop
        self.initialized_event = initialized_event

        self.cluster_loops: Dict[Context, AsyncClusterLoop] = {}

    @classmethod
    def get_instance(cls) -> "AsyncLoop":
        if cls._instance is None:
            raise RuntimeError("AsyncLoop has no instance yet")

        return cls._instance

    async def initialize(self) -> None:
        self.__class__._instance = self

        # tell the world we are up and running
        self.initialized_event.set()

    async def get_cluster_loop(self, context: Context) -> AsyncClusterLoop:
        cluster_loop = self.cluster_loops.get(context)

        if cluster_loop is None:
            cluster_loop = AsyncClusterLoop(context=context)
            self.cluster_loops[context] = cluster_loop

            self.loop.create_task(cluster_loop.mainloop())
            await cluster_loop.wait_until_initialized()

        await cluster_loop.do()

        return cluster_loop

    async def get_client(self, context: Context) -> AsyncClient:
        cluster_loop = await self.get_cluster_loop(context)
        client = await cluster_loop.get_client()
        return client

    async def mainloop(self):
        await self.initialize()

        while True:
            await asyncio.sleep(3600)


def launch_in_background_thread() -> AsyncLoop:
    loop = asyncio.get_event_loop()
    loop.set_debug(True)

    initialized_event = Event()
    async_loop = AsyncLoop(loop=loop, initialized_event=initialized_event)

    thread = Thread(target=loop.run_until_complete, args=[async_loop.mainloop()])
    thread.start()

    # wait until the loop has started running on a separate thread and is ready
    # to be used
    initialized_event.wait()

    return async_loop


def get_loop() -> AsyncLoop:
    return AsyncLoop.get_instance()
