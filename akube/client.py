import json
import logging
import random
import re
from asyncio.exceptions import TimeoutError
from asyncio.locks import Lock
from typing import Any, List, Optional, Tuple
from urllib.parse import urlencode

from aiohttp import BasicAuth, ClientSession
from aiohttp.client import ClientTimeout
from aiohttp.client_exceptions import ClientPayloadError

from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvSender
from kube.config import Context
from kube.events.objects import Action, ObjectEvent
from kube.tools.logs import CtxLogger


class ApiError(Exception):
    # too old resource version: 355452234 (358305898)
    rx = re.compile("too old resource version: \d+ \((\d+)\)")

    def __init__(self, code: int, reason: str, message: str) -> None:
        super().__init__()

        self.code = code
        self.reason = reason
        self.message = message

    def __repr__(self) -> str:
        return "%s(code=%r, reason=%r, message=%r)" % (
            self.__class__.__name__,
            self.code,
            self.reason,
            self.message,
        )

    def __str__(self) -> str:
        return self.__repr__()

    def is_retryable(self):
        return self.code in (500, 502, 503, 504)

    def is_resource_version_too_old(self):
        return self.rx.search(self.message) is not None

    def extract_resource_version(self):
        match = self.rx.search(self.message)
        assert match is not None
        return int(match.group(1))


class AsyncClient:
    def __init__(
        self, *, session: ClientSession, context: Context, logger=None
    ) -> None:
        self.session = session
        self.context = context
        self.logger = logger or logging.getLogger("aclient")

        self.ssl_context = self.context.create_ssl_context()
        self.basic_auth = self.create_basic_auth(context)

        self.resource_version_lock = Lock()
        self.resource_version = 0

    def create_basic_auth(self, context: Context) -> Optional[BasicAuth]:
        if context.user.username and context.user.password:
            return BasicAuth(
                login=context.user.username, password=context.user.password
            )

        return None

    # Logging

    def get_ctx_logger(self, selector: ObjectSelector) -> CtxLogger:
        return CtxLogger(
            logger=self.logger,
            extra=(self.context.short_name, selector.pretty()),
            prefix="[%s] [%s] ",
        )

    def get_ctx_logger_seqno(self, selector: ObjectSelector, seqno: int) -> CtxLogger:
        return CtxLogger(
            logger=self.logger,
            extra=(self.context.short_name, selector.pretty(), seqno),
            prefix="[%s] [%s] [%s] ",
        )

    # Manage resourceVersion

    async def get_resource_version(self) -> int:
        async with self.resource_version_lock:
            return self.resource_version

    async def update_resource_version(self, *, dct=None, exc: ApiError = None) -> None:
        assert dct or exc

        if dct:
            version = int(dct["metadata"]["resourceVersion"])
        else:
            version = exc.extract_resource_version()

        async with self.resource_version_lock:
            if version > self.resource_version:
                self.resource_version = version

    # Parsing responses

    def parse_watch_action(self, item) -> Action:
        action_str = item["type"]

        for attname in dir(Action):
            attvalue = getattr(Action, attname)
            if attname.startswith("_") or callable(attvalue):
                continue

            if attname == action_str:
                return attvalue

        raise RuntimeError("Failed to parse action from item: %r" % item)

    def maybe_parse_error(self, dct) -> None:
        # if it's a watch item them the object is wrapped
        if dct.get("type") == "ERROR":
            dct = dct["object"]

        if dct.get("status") == "Failure":
            message = dct["message"]
            reason = dct["reason"]
            code = dct["code"]
            raise ApiError(code=code, reason=reason, message=message)

    async def construct_url(
        self, selector: ObjectSelector, watch: bool = False, timeout: int = None
    ) -> str:
        server = self.context.cluster.server
        prefix = selector.res.endpoint
        name = selector.res.name
        url = f"{server}{prefix}/{name}"

        if selector.namespace:
            namespace = selector.namespace
            url = f"{server}{prefix}/namespaces/{namespace}/{name}"

        query_args = {}

        if watch:
            query_args["watch"] = 1
            query_args["resourceVersion"] = await self.get_resource_version()
            # TODO: add resourceVersionMatch?

        if timeout is not None:
            query_args["timeoutSeconds"] = timeout

        # TODO: add fieldSelector
        # TODO: add labelSelector

        if query_args:
            query = urlencode(query_args)
            url = f"{url}?{query}"

        return url

    async def list_objects(self, selector: ObjectSelector) -> List[Any]:
        log = self.get_ctx_logger(selector)

        kind = selector.res.kind
        url = await self.construct_url(selector)

        kwargs = dict(
            url=url,
            ssl_context=self.ssl_context,
            auth=self.basic_auth,
            timeout=ClientTimeout(
                sock_connect=3,
                sock_read=15,
            ),
        )

        log.info("Listing %s objects on %s", kind, url)
        async with self.session.get(**kwargs) as response:

            log.debug("Parsing %s response as json", kind)
            js = await response.json()

            try:
                self.maybe_parse_error(js)
            except ApiError:
                log.exception("List request failed")
                return []

            try:
                items = js["items"]
            except KeyError:
                log.error("Failed to parse %s response items: %r", kind, js)
                return []

            for item in items:
                item["apiVersion"] = js["apiVersion"]
                item["kind"] = js["kind"].replace("List", "")
                await self.update_resource_version(dct=item)

            log.debug("Returning %s items", kind)
            return items

    async def watch_attempt(self, selector: ObjectSelector, oev_sender: OEvSender) -> None:
        kind = selector.res.kind
        url = await self.construct_url(selector, watch=True)

        kwargs = dict(
            url=url,
            ssl_context=self.ssl_context,
            auth=self.basic_auth,
            timeout=ClientTimeout(
                sock_connect=3,
                sock_read=300,
            ),
        )

        # a bit TCP like: choose a random seqno which will be used in every log
        # line and incremented for every loop iteration (to distinguish loop
        # iterations from each other in log output)
        seqno = random.randint(0, 10000)

        log = self.get_ctx_logger_seqno(selector, seqno)

        log.info("Watching %s objects on %s", kind, url)
        async with self.session.get(**kwargs) as response:

            # read one line at a time, b'\n' terminated
            while True:
                log.debug("Waiting for %s response line", kind)
                line = await response.content.readline()

                if not line:
                    log.info("Received empty line, exiting")
                    break

                log.debug("Parsing %s response line [len: %s] as json", kind, len(line))
                dct = json.loads(line)

                # may raise
                self.maybe_parse_error(dct)

                action = self.parse_watch_action(dct)
                event = ObjectEvent(
                    context=self.context, action=action, object=dct["object"]
                )

                await self.update_resource_version(dct=dct["object"])

                log.debug("Returning %s item", kind)
                oev_sender.send(event)

                seqno += 1

    async def watch_objects(
        self, *, selector: ObjectSelector, oev_sender: OEvSender
    ) -> None:
        log = self.get_ctx_logger(selector)

        while True:
            try:
                await self.watch_attempt(selector, oev_sender)

            except (TimeoutError, ClientPayloadError) as exc:
                # the server timed out the watch - we expect this to happen
                # after the normal server timeout interval (5-15min)
                log.info("Watch request completed - restarting")

            except ApiError as exc:
                # if the http error looks transient - try again
                if exc.is_retryable():
                    log.warn(
                        "Watch request failed with retryable error: %r - retrying", exc
                    )
                    continue

                # the server said our resourceVersion is too old, but also told
                # us an acceptable resourceVersion so let's use that
                if exc.is_resource_version_too_old():
                    await self.update_resource_version(exc=exc)
                    continue

                # if the http error seems permanet then log a traceback and exit
                log.exception(
                    "Watch request failed with non-retryable error - giving up"
                )
                raise

            except Exception:
                # we don't know what the error is so log a traceback and exit
                log.exception("Watch request failed with unexpected error - giving up")
                raise
