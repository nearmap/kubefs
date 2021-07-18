import asyncio
import logging
import time
from asyncio.events import AbstractEventLoop
from typing import Any, List

import aiohttp

from akube.client import AsyncClient
from kube.channels.objects import OEvReceiver, create_oev_chan
from kube.config import Context
from kube.tools.logs import get_silent_logger


class AsyncClusterLoop:
    def __init__(
        self, *, loop: AbstractEventLoop, context: Context, logger=None
    ) -> None:
        self.loop = loop
        self.context = context

        self.logger = logger or logging.getLogger(context.short_name)

        self.is_running = False

        self.oev_sender = None

    async def run_forever(self):
        async with aiohttp.ClientSession() as session:
            logger = get_silent_logger()
            self.client = AsyncClient(
                session=session, context=self.context, logger=logger
            )
            self.is_running = True

            while True:
                if self.oev_sender:
                    await self.client.watch_objects(oev_sender=self.oev_sender)

                await asyncio.sleep(1)

    def sync_list_objects(self) -> List[Any]:
        self.logger.info("Entered list_objects()")
        future = asyncio.run_coroutine_threadsafe(self.client.list_objects(), self.loop)

        while not future.done():
            time.sleep(0.001)

        self.logger.info("Exiting list_objects()")
        return future.result()

    def start_watching(self) -> OEvReceiver:
        oev_sender, oev_receiver = create_oev_chan()
        self.oev_sender = oev_sender
        return oev_receiver
