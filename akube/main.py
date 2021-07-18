import asyncio
import logging
import time
from asyncio.events import AbstractEventLoop
from threading import Thread
from typing import Any, Dict, List, Sequence

from akube.cluster_loop_orig import AsyncClusterLoop
from kube.channels.objects import OEvReceiver
from kube.config import Context


class AsyncLoop:
    _instance = None

    def __init__(
        self, loop: AbstractEventLoop, contexts: Sequence[Context], logger=None
    ) -> None:
        self.loop = loop
        self.contexts = contexts
        self.logger = logger or logging.getLogger("aloop")

        self.is_running = False
        self.cluster_loops: Dict[Context, AsyncClusterLoop] = {}

    @classmethod
    def get_instance(cls) -> "AsyncLoop":
        if cls._instance is None:
            raise RuntimeError("AsyncLoop has no instance yet")

        return cls._instance

    async def mainloop(self):
        # launch all the cluster loops
        tasks = []
        for context in self.contexts:
            cluster_loop = AsyncClusterLoop(loop=self.loop, context=context)
            self.cluster_loops[context] = cluster_loop
            task = self.loop.create_task(cluster_loop.run_forever())
            tasks.append(task)

        # wait until cluster loops have initialized
        all_started = False
        while not all_started:
            for cluster_loop in self.cluster_loops.values():
                all_started = cluster_loop.is_running

            await asyncio.sleep(0)

        # mark ourselves as fully initialized now
        self.__class__._instance = self
        self.is_running = True

        while True:
            await asyncio.sleep(1)

    def sync_list_objects(self, context: Context) -> List[Any]:
        cluster_loop = self.cluster_loops[context]
        return cluster_loop.sync_list_objects()

    def add_watch(self, context: Context) -> OEvReceiver:
        cluster_loop = self.cluster_loops[context]
        return cluster_loop.start_watching()


def launch_in_thread(contexts: Sequence[Context]) -> AsyncLoop:
    loop = asyncio.get_event_loop()
    loop.set_debug(True)
    async_loop = AsyncLoop(loop=loop, contexts=contexts)

    thread = Thread(target=loop.run_until_complete, args=[async_loop.mainloop()])
    thread.start()

    # wait for our async loop to enter its mainloop
    while not async_loop.is_running:
        time.sleep(0.001)

    return async_loop


def get_loop() -> AsyncLoop:
    return AsyncLoop.get_instance()
