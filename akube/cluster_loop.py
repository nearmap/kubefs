import asyncio
import logging
import time
from asyncio.events import AbstractEventLoop
from typing import Any, List

import aiohttp

from akube.client import AsyncClient
from kube.config import Context


class ClusterLoop:
    def __init__(
        self, *, loop: AbstractEventLoop, context: Context, logger=None
    ) -> None:
        self.loop = loop
        self.context = context

        self.logger = logging.getLogger(context.short_name)

        self.is_running = False

    async def run_forever(self):
        async with aiohttp.ClientSession() as session:
            self.client = AsyncClient(session=session, context=self.context)
            self.is_running = True

            while True:
                await asyncio.sleep(0.001)

    def sync_list_objects(self) -> List[Any]:
        self.logger.info("Entered list_objects()")
        task = self.loop.create_task(self.client.list_objects())

        while not task.done():
            time.sleep(0.001)

        self.logger.info("Exiting list_objects()")
        return task.result()
