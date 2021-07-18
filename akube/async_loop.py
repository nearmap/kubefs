from asyncio.base_events import BaseEventLoop
import time
import asyncio
from threading import Event, Thread
from typing import Any, Dict

from akube.cluster_loop import AsyncClusterLoop
from kube.config import Context


class AsyncLoop:
    _instance = None

    def __init__(
        self, *, loop: BaseEventLoop, initialized_event: Event
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
        # make get_instance work
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

        return cluster_loop

    async def mainloop(self):
        await self.initialize()

        while True:
            await asyncio.sleep(3600)

    # Helpers to facilitate running tasks on the async loop from another thread

    def get_loop(self) -> BaseEventLoop:
        return self.loop

    def launch_coro(self, coro) -> None:
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run_coro_until_completion(self, coro) -> Any:
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)

        while not fut.done():
            time.sleep(0.001)

        return fut.result()


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
