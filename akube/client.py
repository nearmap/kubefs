import base64
import logging
import ssl
import tempfile
from typing import Any, List, Optional

from aiohttp import BasicAuth, ClientSession

from kube.config import Context


class AsyncClient:
    def __init__(
        self, *, session: ClientSession, context: Context, logger=None
    ) -> None:
        self.session = session
        self.context = context
        self.logger = logging.getLogger("aclient")

        self.ssl_context = self.context.create_ssl_context()
        self.basic_auth = self.create_basic_auth(context)

    def create_basic_auth(self, context: Context) -> Optional[BasicAuth]:
        if context.user.username and context.user.password:
            return BasicAuth(
                login=context.user.username, password=context.user.password
            )

        return None

    async def list_objects(self, prefix="/api/v1", kind="namespaces") -> List[Any]:
        url = f"{self.context.cluster.server}{prefix}/{kind}"

        self.logger.info("Fetching %s", url)
        async with self.session.get(
            url, ssl=self.ssl_context, auth=self.basic_auth
        ) as response:

            self.logger.debug("Parsing response as json")
            js = await response.json()

            try:
                items = js["items"]
            except KeyError:
                self.logger.error("Failed to parse response items: %r", js)
                return []

            for item in items:
                item["apiVersion"] = js["apiVersion"]
                item["kind"] = js["kind"].replace("List", "")

            self.logger.debug("Returning items")
            return items
