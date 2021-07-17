import asyncio
import logging
import time
from asyncio.events import AbstractEventLoop
from threading import Thread
from typing import Any, List, Optional

import aiohttp

from akube.client import AsyncClient


class AsyncLoop:
    _instance = None

    def __init__(self, loop: AbstractEventLoop, logger=None) -> None:
        self.loop = loop
        self.logger = logging.getLogger("aloop")

        self.client: Optional[AsyncClient] = None
        self.is_running = False

    @classmethod
    def get_instance(cls) -> "AsyncLoop":
        if cls._instance is None:
            raise RuntimeError("AsyncLoop has no instance yet")

        return cls._instance

    async def mainloop(self):
        async with aiohttp.ClientSession() as session:
            self.client = AsyncClient(session=session, baseurl="http://127.0.0.1:8001")

            # mark ourselves as fully initialized now
            self.__class__._instance = self
            self.is_running = True

            while True:
                # print("run_forever loop")
                await asyncio.sleep(0.001)
                # items = await self.client.list_objects()
                # print(items)

    def sync_list_objects(self) -> List[Any]:
        self.logger.info("Entered list_objects()")
        task = self.loop.create_task(self.client.list_objects())

        while not task.done():
            time.sleep(0.001)

        self.logger.info("Exiting list_objects()")
        return task.result()


def launch_in_thread():
    loop = asyncio.get_event_loop()
    async_loop = AsyncLoop(loop)

    thread = Thread(target=loop.run_until_complete, args=[async_loop.mainloop()])
    thread.start()

    # wait for our async loop to enter its mainloop
    while not async_loop.is_running:
        time.sleep(0.001)

    return async_loop


def get_loop() -> AsyncLoop:
    return AsyncLoop.get_instance()
