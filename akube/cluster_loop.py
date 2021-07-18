import asyncio
from asyncio import Event

import aiohttp

from akube.client import AsyncClient
from kube.config import Context
from kube.tools.logs import get_silent_logger


class AsyncClusterLoop:
    def __init__(self, *, context: Context) -> None:
        self.context = context

        self.initialized_event = Event()

        self.client = None

    async def wait_until_initialized(self):
        await self.initialized_event.wait()

    async def get_client(self) -> AsyncClient:
        if self.client is None:
            raise RuntimeError("Have no client yet")

        return self.client

    async def mainloop(self):
        async with aiohttp.ClientSession() as session:
            logger = get_silent_logger()
            self.client = AsyncClient(
                session=session, context=self.context, logger=logger
            )

            # once we have a client we announce we are ready for use
            self.initialized_event.set()

            while True:
                await asyncio.sleep(3600)
