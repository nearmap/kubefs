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
    def __init__(self, *, async_loop: "AsyncLoop", context: Context) -> None:
        self.async_loop = async_loop
        self.context = context

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
        task = loop.create_task(
            self.client.watch_objects(selector=selector, oev_sender=oev_sender)
        )

        async with self.watches_lock:
            self.watches[selector] = task

    async def stop_watch(self, selector: ObjectSelector) -> None:
        async with self.watches_lock:
            task = self.watches.get(selector)

        if task:
            try:
                task.cancel()
            except CancelledError:
                pass

    async def mainloop(self):
        async with aiohttp.ClientSession() as session:
            logger = logging.getLogger('aclient')
            logger.setLevel(logging.WARN)
            # logger = get_silent_logger()

            self.client = AsyncClient(
                session=session, context=self.context, logger=logger
            )

            # once we have a client we announce we are ready for use
            self.initialized_event.set()

            while True:
                await asyncio.sleep(3600)
