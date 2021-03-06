import asyncio
import time
from asyncio.events import AbstractEventLoop
from asyncio.exceptions import CancelledError
from threading import Event, Thread
from typing import Any, Dict

from kube.cluster_loop import AsyncClusterLoop
from kube.config import Context


class AsyncLoop:
    _instance = None

    def __init__(self, *, loop: AbstractEventLoop, initialized_event: Event) -> None:
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
            cluster_loop = AsyncClusterLoop(async_loop=self, context=context)
            self.cluster_loops[context] = cluster_loop

            self.loop.create_task(cluster_loop.mainloop())
            await cluster_loop.wait_until_initialized()

        return cluster_loop

    async def mainloop(self):
        await self.initialize()

        while True:
            await asyncio.sleep(3600)

    async def safe_mainloop(self):
        """
        We need this wrapper function because mainloop() is used as an
        entrypoint for Thread and thus we need to catch CancelledError to have a
        graceful shutdown.
        """

        try:
            await self.mainloop()
        except CancelledError:
            return

    # Helpers to facilitate running tasks on the async loop from another thread

    def get_loop(self) -> AbstractEventLoop:
        return self.loop

    def launch_coro(self, coro) -> None:
        asyncio.run_coroutine_threadsafe(coro, self.loop)

    def run_coro_until_completion(self, coro) -> Any:
        fut = asyncio.run_coroutine_threadsafe(coro, self.loop)

        while not fut.done():
            time.sleep(0.001)

        return fut.result()

    def shutdown(self):
        "Shutdown the AsyncLoop and join the thread it runs in."

        for task in asyncio.all_tasks(loop=self.loop):
            try:
                task.cancel()
            except CancelledError:
                pass

        self.loop.stop()


def launch_in_background_thread() -> AsyncLoop:
    loop = asyncio.get_event_loop()
    # loop.set_debug(True)

    initialized_event = Event()
    async_loop = AsyncLoop(loop=loop, initialized_event=initialized_event)

    thread = Thread(
        name="AsyncThread",
        target=loop.run_until_complete,
        args=[async_loop.safe_mainloop()],
    )
    thread.start()

    # wait until the loop has started running on a separate thread and is ready
    # to be used
    initialized_event.wait()

    return async_loop


def get_loop() -> AsyncLoop:
    return AsyncLoop.get_instance()
