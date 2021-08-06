from asyncio.locks import Lock
from ssl import SSLContext
from typing import Optional

from aiohttp import BasicAuth


class ClientState:
    def __init__(
        self, *, basic_auth: Optional[BasicAuth] = None, ssl_context: SSLContext
    ) -> None:
        self.basic_auth = basic_auth
        self.ssl_context = ssl_context

        self.resource_version_lock = Lock()
        self.resource_version = 0

    async def get_resource_version(self) -> int:
        async with self.resource_version_lock:
            return self.resource_version

    async def update_resource_version(self, *, version: int) -> None:
        async with self.resource_version_lock:
            if version > self.resource_version:
                self.resource_version = version
