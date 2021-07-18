import asyncio
from asyncio import Event

import aiohttp

from akube.client import AsyncClient
from kube.config import Context


class AsyncClusterLoop:
    def __init__(self, *, context: Context) -> None:
        self.context = context

        self.initialized_event = Event()

        self.client = None

    async def wait_until_initialized(self):
        await self.initialized_event.wait()

    async def get_client(self) -> AsyncClient:
        return self.client

    async def mainloop(self):
        async with aiohttp.ClientSession() as session:
            self.client = AsyncClient(session=session, context=self.context)
            self.initialized_event.set()

            while True:
                await asyncio.sleep(3600)

    async def do(self):
        print(self.client)
