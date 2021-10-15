import asyncio
import json
import logging
import re
from asyncio.exceptions import TimeoutError
from asyncio.locks import Lock
from typing import Any, List
from urllib.parse import urlencode

from aiohttp import ClientSession
from aiohttp.client import ClientTimeout
from aiohttp.client_exceptions import (
    ClientConnectorCertificateError,
    ClientConnectorError,
    ClientConnectorSSLError,
    ClientOSError,
    ClientPayloadError,
    ServerTimeoutError,
    TooManyRedirects,
)

from kube.auth import AuthProvider
from kube.channels.objects import OEvSender
from kube.config import Context
from kube.events.objects import Action, ObjectEvent
from kube.model.api_group import ApiGroup
from kube.model.api_resource import ApiResource
from kube.model.selector import ObjectSelector
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
        return self.code in (429, 500, 502, 503, 504)

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
        self.logger = logger or logging.getLogger("client")

        self.ssl_context = self.context.create_ssl_context()
        self.auth_provider = AuthProvider(context)

        self.resource_version_lock = Lock()
        self.resource_version = 0

    # Logging

    def get_ctx_logger(self, selector: ObjectSelector) -> CtxLogger:
        return CtxLogger(
            logger=self.logger,
            extra={"context": self.context.short_name, "selector": selector.pretty()},
            prefix="[%(context)s] [%(selector)s] ",
        )

    # Manage resourceVersion

    async def get_resource_version(self) -> int:
        async with self.resource_version_lock:
            return self.resource_version

    async def update_resource_version(self, *, dct=None, exc: ApiError = None) -> None:
        assert dct or exc
        version = None

        if dct:
            version_str = dct["metadata"].get("resourceVersion")
            if version_str:
                version = int(version_str)
        elif exc is not None:
            version = exc.extract_resource_version()

        if version is None:
            return

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
        prefix = selector.res.group.endpoint
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

    def send_error(self, exc: Exception, oev_sender: OEvSender) -> None:
        event = ObjectEvent(
            context=self.context,
            action=Action.ADDED,
            object=exc,
        )
        oev_sender.send(event)

    async def list_api_groups(self) -> List[ApiGroup]:
        server = self.context.cluster.server
        url = f"{server}/apis"

        kwargs = dict(
            ssl_context=self.ssl_context,
            auth=self.auth_provider.get_auth(),
            timeout=ClientTimeout(
                sock_connect=3,
                total=15,
            ),
        )

        self.logger.info("Listing api groups on %s", url)
        async with self.session.get(url, allow_redirects=True, **kwargs) as response:

            self.logger.debug("Parsing api group response as json")
            js = await response.json()

            # may raise
            self.maybe_parse_error(js)

            items = js["groups"]

            api_groups = []
            for item in items:
                name = item["name"]
                for version_dct in item["versions"]:
                    endpoint = version_dct["groupVersion"]

                    api_group = ApiGroup(
                        name=name,
                        endpoint=f"/apis/{endpoint}",
                        version=version_dct["version"],
                    )
                    api_groups.append(api_group)

            self.logger.debug("Returning api groups")
            return api_groups

    async def list_api_resources(self, group: ApiGroup) -> List[ApiResource]:
        server = self.context.cluster.server
        url = f"{server}{group.endpoint}"

        kwargs = dict(
            ssl_context=self.ssl_context,
            auth=self.auth_provider.get_auth(),
            timeout=ClientTimeout(
                sock_connect=3,
                total=15,
            ),
        )

        self.logger.info("Listing %s api resources on %s", group.name, url)
        async with self.session.get(url, allow_redirects=True, **kwargs) as response:

            self.logger.debug("Parsing %s api resource response as json", group.name)
            try:
                js = await response.json()
            except Exception:
                self.logger.error("error: %s", response)
                raise

            # may raise
            self.maybe_parse_error(js)

            items = js["resources"]

            api_resources = []
            for item in items:
                name = item["name"]

                api_resource = ApiResource(
                    group=group,
                    kind=item["kind"],
                    name=name,
                    namespaced=item["namespaced"],
                    verbs=item["verbs"],
                )
                api_resources.append(api_resource)

            self.logger.debug("Returning %s api resources", group.name)
            return api_resources

    async def list_attempt(self, selector: ObjectSelector) -> List[Any]:
        log = self.get_ctx_logger(selector)

        kind = selector.res.kind
        url = await self.construct_url(selector)

        kwargs = dict(
            ssl_context=self.ssl_context,
            auth=self.auth_provider.get_auth(),
            timeout=ClientTimeout(
                sock_connect=3,
                total=15,
            ),
        )

        log.info("Listing %s objects on %s", kind, url)
        async with self.session.get(url, allow_redirects=True, **kwargs) as response:

            log.debug("Parsing %s response as json", kind)
            js = await response.json()

            # may raise
            self.maybe_parse_error(js)

            items = js["items"]

            for item in items:
                item["apiVersion"] = js["apiVersion"]
                item["kind"] = js["kind"].replace("List", "")
                await self.update_resource_version(dct=item)

            log.debug("Returning %s items", kind)
            return items

    async def list_objects(self, selector: ObjectSelector) -> List[Any]:
        log = self.get_ctx_logger(selector)

        retries = 0
        max_retries = 3
        retriable_connection_errors = (
            ClientConnectorError,
            ServerTimeoutError,
            TimeoutError,
            TooManyRedirects,
            ClientOSError,
            ClientConnectorCertificateError,
            ClientConnectorSSLError,
        )

        while True:

            try:
                return await self.list_attempt(selector)

            except retriable_connection_errors as exc:
                if retries < max_retries:
                    retries += 1
                    log.warn(
                        "List request failed with retryable error: %r - retrying", exc
                    )

                    await asyncio.sleep(0.3)
                    continue

                log.exception(
                    "List request failed with non-retryable error - giving up"
                )
                raise

            except ApiError as exc:
                # if the http error looks transient - try again
                if exc.is_retryable() and retries < max_retries:
                    retries += 1
                    log.warn(
                        "List request failed with retryable error: %r - retrying", exc
                    )

                    await asyncio.sleep(0.3)
                    continue

                log.exception(
                    "List request failed with non-retryable error - giving up"
                )
                raise

            except Exception:
                # we don't know what the error is so log a traceback and exit
                log.exception("List request failed with unexpected error - giving up")
                raise

    async def watch_attempt(
        self, selector: ObjectSelector, oev_sender: OEvSender
    ) -> None:
        log = self.get_ctx_logger(selector)

        kind = selector.res.kind
        url = await self.construct_url(selector, watch=True)

        kwargs = dict(
            ssl_context=self.ssl_context,
            auth=self.auth_provider.get_auth(),
            timeout=ClientTimeout(
                sock_connect=3,
                total=300,
            ),
        )

        log.info("Watching %s objects on %s", kind, url)
        async with self.session.get(url, allow_redirects=True, **kwargs) as response:

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

    async def watch_objects(
        self, *, selector: ObjectSelector, oev_sender: OEvSender
    ) -> None:
        log = self.get_ctx_logger(selector)

        successful_completion_exceptions = (
            TimeoutError,
            ClientPayloadError,
        )
        retriable_connection_errors = (
            ClientConnectorError,
            ServerTimeoutError,
            TooManyRedirects,
            ClientOSError,
            ClientConnectorCertificateError,
            ClientConnectorSSLError,
        )

        while True:
            try:
                await self.watch_attempt(selector, oev_sender)

            except successful_completion_exceptions as exc:
                # the server timed out the watch - we expect this to happen
                # after the normal server timeout interval (5-15min)
                # (this could also happen if the server is unreachable....)
                log.info("Watch request completed - restarting: %r", exc)
                await asyncio.sleep(1)  # don't retry aggressively

            except retriable_connection_errors as exc:
                log.warn(
                    "Watch request failed with retryable error: %r - retrying", exc
                )

                await asyncio.sleep(1)  # don't retry aggressively
                continue

            except ApiError as exc:
                # if the http error looks transient - try again
                if exc.is_retryable():
                    log.warn(
                        "Watch request failed with retryable error: %r - retrying", exc
                    )

                    await asyncio.sleep(1)  # don't retry aggressively
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
                self.send_error(exc, oev_sender)
                break

            except Exception as exc:
                # we don't know what the error is so log a traceback and exit
                log.exception("Watch request failed with unexpected error - giving up")
                self.send_error(exc, oev_sender)
                break

    async def stream_pod_logs_attempt(
        self, selector: ObjectSelector, oev_sender: OEvSender
    ) -> None:
        log = self.get_ctx_logger(selector)

        server = self.context.cluster.server
        prefix = selector.res.group.endpoint
        name = selector.res.name
        namespace = selector.namespace
        podname = selector.podname
        contname = selector.contname

        query_args = {
            "container": contname,
            "follow": 1,
            "tailLines": 0,
        }
        query = urlencode(query_args)

        url = f"{server}{prefix}/namespaces/{namespace}/{name}/{podname}/log?{query}"

        kwargs = dict(
            ssl_context=self.ssl_context,
            auth=self.auth_provider.get_auth(),
            timeout=ClientTimeout(
                sock_connect=3,
                total=300,
            ),
        )

        log.info("Streaming pod logs on %s", url)
        async with self.session.get(url, allow_redirects=True, **kwargs) as response:

            # read one line at a time, b'\n' terminated
            while True:
                log.debug("Waiting for response line")
                line = await response.content.readline()

                if not line:
                    log.info("Received empty line, exiting")
                    break

                event = ObjectEvent(
                    context=self.context,
                    action=Action.LOG_LINE,
                    object=line,
                )

                log.debug("Returning log line")
                oev_sender.send(event)

    async def stream_pod_logs(
        self, *, selector: ObjectSelector, oev_sender: OEvSender
    ) -> None:
        log = self.get_ctx_logger(selector)

        successful_completion_exceptions = (
            TimeoutError,
            ClientPayloadError,
        )
        retriable_connection_errors = (
            ClientConnectorError,
            ServerTimeoutError,
            TooManyRedirects,
            ClientOSError,
            ClientConnectorCertificateError,
            ClientConnectorSSLError,
        )

        while True:
            try:
                await self.stream_pod_logs_attempt(selector, oev_sender)

            except successful_completion_exceptions as exc:
                log.info("Stream pod logs request completed - restarting: %r", exc)
                await asyncio.sleep(1)  # don't retry aggressively

            except retriable_connection_errors as exc:
                log.warn(
                    "Stream pod logs request failed with retryable error: %r - retrying",
                    exc,
                )

                await asyncio.sleep(1)  # don't retry aggressively
                continue

            except ApiError as exc:
                # if the http error looks transient - try again
                if exc.is_retryable():
                    log.warn(
                        "Stream pod logs request failed with retryable error: %r - retrying",
                        exc,
                    )

                    await asyncio.sleep(1)  # don't retry aggressively
                    continue

                # if the http error seems permanet then log a traceback and exit
                log.exception(
                    "Stream pod logs request failed with non-retryable error - giving up"
                )
                self.send_error(exc, oev_sender)
                break

            except Exception as exc:
                # we don't know what the error is so log a traceback and exit
                log.exception(
                    "Stream pod logs request failed with unexpected error - giving up"
                )
                self.send_error(exc, oev_sender)
                break
