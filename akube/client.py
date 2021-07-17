import logging

from aiohttp import ClientSession


class AsyncClient:
    def __init__(self, *, session: ClientSession, baseurl: str, logger=None) -> None:
        self.session = session
        self.baseurl = baseurl
        self.logger = logging.getLogger("aclient")

    async def list_objects(self, prefix="/api/v1", kind="namespaces"):
        url = f"{self.baseurl}{prefix}/{kind}"

        self.logger.info("Fetching %s", url)
        async with self.session.get(url) as response:

            self.logger.debug("Parsing response as json")
            js = await response.json()

            try:
                items = js["items"]
            except KeyError:
                self.logger.error("Failed to parse response items: %r", js)

            for item in items:
                item["apiVersion"] = js["apiVersion"]
                item["kind"] = js["kind"].replace("List", "")

            self.logger.debug("Returning items")
            return items
