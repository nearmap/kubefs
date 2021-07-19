import asyncio
import logging
from asyncio import Event, Lock, Task
from asyncio.exceptions import CancelledError
from typing import Dict

import aiohttp

from akube.client import AsyncClient
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvSender
from kube.config import Context
from kube.tools.logs import get_silent_logger


class AsyncClusterLoop:
    def __init__(
        self, *, async_loop: "AsyncLoop", context: Context, logger=None
    ) -> None:
        self.async_loop = async_loop
        self.context = context
        self.logger = logger or logging.getLogger("cluster_loop")

        self.initialized_event = Event()
        self.client = None

        self.watches_lock = Lock()
        self.watches: Dict[ObjectSelector, Task] = {}

    async def wait_until_initialized(self):
        await self.initialized_event.wait()

    async def get_client(self) -> AsyncClient:
        if self.client is None:
            raise RuntimeError("Have no client yet")

        return self.client

    async def start_watch(
        self, selector: ObjectSelector, oev_sender: OEvSender
    ) -> None:
        loop = self.async_loop.get_loop()
        coro = self.client.watch_objects(selector=selector, oev_sender=oev_sender)
        task = loop.create_task(coro)

        async with self.watches_lock:
            self.watches[selector] = task

    async def stop_watch(self, selector: ObjectSelector) -> None:
        async with self.watches_lock:
            task = self.watches.pop(selector, None)

        if task is None:
            raise RuntimeError("No such watch for selector %r" % selector)

        try:
            task.cancel()
        except CancelledError:
            pass

    async def detect_stopped_watches(self):
        async with self.watches_lock:
            for selector, task in self.watches.items():
                if not task.done():
                    continue

                exc = task.exception()
                if exc is not None:
                    self.logger.error(
                        "Watch with selector %r errored out: %r", selector, exc
                    )
                    return

                # okay, it didn't crash but... it exited for some reason?
                self.logger.warn(
                    "Watch with selector %r completed prematurely", selector
                )

    async def mainloop(self):
        async with aiohttp.ClientSession() as session:
            logger = logging.getLogger("aclient")
            # logger.setLevel(logging.WARN)
            # logger = get_silent_logger()

            self.client = AsyncClient(
                session=session, context=self.context, logger=logger
            )

            # once we have a client we announce we are ready for use
            self.initialized_event.set()

            while True:
                await self.detect_stopped_watches()
                await asyncio.sleep(1)
