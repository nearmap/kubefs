import asyncio
import json
import logging
from typing import Any, List, Optional

from aiohttp import BasicAuth, ClientSession

from kube.channels.objects import OEvSender
from kube.config import Context
from kube.events.objects import Action, ObjectEvent


class AsyncClient:
    def __init__(
        self, *, session: ClientSession, context: Context, logger=None
    ) -> None:
        self.session = session
        self.context = context
        self.logger = logger or logging.getLogger("aclient")

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

        self.logger.info("Listing %s objects on %s", kind, url)
        async with self.session.get(
            url, ssl=self.ssl_context, auth=self.basic_auth
        ) as response:

            self.logger.debug("Parsing %s response as json", kind)
            js = await response.json()

            try:
                items = js["items"]
            except KeyError:
                self.logger.error("Failed to parse %s response items: %r", kind, js)
                return []

            for item in items:
                item["apiVersion"] = js["apiVersion"]
                item["kind"] = js["kind"].replace("List", "")

            self.logger.debug("Returning %s items", kind)
            return items

    def parse_action(self, item) -> Action:
        action_str = item["type"]

        for attname in dir(Action):
            attvalue = getattr(Action, attname)
            if attname.startswith("_") or callable(attvalue):
                continue

            if attname == action_str:
                return attvalue

        raise RuntimeError("Failed to parse action from item: %r" % action_str)

    async def watch_objects(
        self, *, prefix="/api/v1", kind="pods", oev_sender: OEvSender
    ) -> None:
        url = f"{self.context.cluster.server}{prefix}/watch/{kind}"

        self.logger.info("Watching %s objects on %s", kind, url)
        async with self.session.get(
            url, ssl=self.ssl_context, auth=self.basic_auth
        ) as response:

            while True:
                self.logger.debug("Reading %s response line as json", kind)
                line = await response.content.readline()
                if not line:
                    break

                self.logger.debug("Parsing %s response line as json", kind)
                dct = json.loads(line)

                action = self.parse_action(dct)
                event = ObjectEvent(
                    context=self.context, action=action, object=dct["object"]
                )

                self.logger.debug("Returning %s item", kind)
                oev_sender.send(event)
