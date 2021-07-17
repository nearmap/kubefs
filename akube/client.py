import logging
import ssl
from typing import Any, List

from aiohttp import ClientSession

from kube.config import Context


class AsyncClient:
    def __init__(
        self, *, session: ClientSession, context: Context, logger=None
    ) -> None:
        self.session = session
        self.context = context
        self.logger = logging.getLogger("aclient")

        self.ssl_context = self.create_ssl_context()

    def create_ssl_context(self) -> ssl.SSLContext:
        ssl_context = ssl.create_default_context(
            cafile=self.context.cluster.ca_cert_path
        )

        ssl_context.load_cert_chain(
            certfile=self.context.user.client_cert_path,
            keyfile=self.context.user.client_key_path,
        )

        return ssl_context

    async def list_objects(self, prefix="/api/v1", kind="namespaces") -> List[Any]:
        url = f"{self.context.cluster.server}{prefix}/{kind}"

        self.logger.info("Fetching %s", url)
        async with self.session.get(url, ssl=self.ssl_context) as response:

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
