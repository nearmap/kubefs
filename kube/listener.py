import enum
import logging
import re
import time
from queue import Empty, Queue
from typing import Any, Dict, Optional

from kubernetes.client.api_client import ApiClient
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic.client import DynamicClient


class ObjectClass:
    def __init__(self, *, api_version: str, kind: str) -> None:
        self.api_version = api_version
        self.kind = kind


class Action(enum.Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    LISTED = "LISTED"


class ObjectEvent:
    def __init__(self, *, action: Action, object: Dict[Any, Any]) -> None:
        self.action = action
        self.object = object

        self.time_created = time.time()


class State(enum.Enum):
    CONNECTING = 1
    LISTING = 2
    WATCHING = 3


class ObjectListener:
    # Reason: Expired: too old resource version: 13130 (154867)
    rx_too_old = re.compile("too old resource version: \d+ \((\d+)\)")

    def __init__(
        self,
        *,
        api_client: ApiClient,
        object_class: ObjectClass,
        conn_listen_queue: Queue,
        notify_queue: Queue,
        shutdown_queue: Queue,
        watch_timeout_s=60,
        logger=None,
    ) -> None:
        self.api_client = api_client
        self.object_class = object_class
        self.conn_listen_queue = conn_listen_queue
        self.notify_queue = notify_queue
        self.shutdown_queue = shutdown_queue
        self.watch_timeout_s = watch_timeout_s
        self.logger = logger or logging.getLogger(__name__)

        self.time_last_listing = None
        self.time_last_watch = None
        self.highest_resource_version = 0

    def notify(self, item: Dict[Any, Any], watched=False) -> None:
        dct = item
        action = Action.LISTED

        if watched:
            dct = item["raw_object"]
            action = self.parse_action(item)

        resource_version = int(dct["metadata"]["resourceVersion"])
        if resource_version > self.highest_resource_version:
            self.highest_resource_version = resource_version

        event = ObjectEvent(action=action, object=dct)
        self.notify_queue.put(event)

    def list_objects(self):
        client = DynamicClient(self.api_client)

        collection = client.resources.get(
            api_version=self.object_class.api_version,
            kind=self.object_class.kind,
        )

        result = collection.get()
        for item in result.items:
            dct = result._ResourceInstance__serialize(item)
            self.notify(dct)

        self.time_last_listing = time.time()

    def parse_action(self, item) -> Action:
        action_str = item["type"]

        for attname in dir(Action):
            attvalue = getattr(Action, attname)
            if attname.startswith("_") or callable(attvalue):
                continue

            if attname == action_str:
                return attvalue

        raise RuntimeError("Failed to parse action from item: %r" % action_str)

    def parse_resource_version(self, exc: ApiException) -> Optional[int]:
        match = self.rx_too_old.search(exc.reason)
        if match:
            return int(match.group(1))

        return None

    def watch_objects(self):
        client = DynamicClient(self.api_client)

        collection = client.resources.get(
            api_version=self.object_class.api_version,
            kind=self.object_class.kind,
        )

        while True:
            watch = collection.watch(
                resource_version=self.highest_resource_version,
                timeout=self.watch_timeout_s,
            )

            try:
                for item in watch:
                    self.notify(item, watched=True)

                break

            except ApiException as exc:
                # The kube api is rather unhelpful and errors out when we send a
                # resourceVersion that is too old, but the client has no way of
                # knowing up front what the "sufficiently recent resource
                # version" is. Happily, the version number is part of the
                # response itself.
                if exc.status == 410:
                    version = self.parse_resource_version(exc)
                    if version is not None:
                        self.highest_resource_version = version
                        continue

                raise

        self.time_last_watch = time.time()

    def should_shutdown(self) -> bool:
        try:
            if self.shutdown_queue.get_nowait() is not None:
                return True
        except Empty:
            pass

        return False

    def run(self) -> None:
        state = State.LISTING

        while True:
            if self.should_shutdown():
                self.logger.info("Shutting down")
                break

            # if state is not States.CONNECTING and not poll conn queue:
            #     state = connecting  # lost conn
            #     continue

            # if state is States.CONNECTING:
            #     if poll conn queue:  # non-blocking
            #         # disconnected long enough to have to list again?
            #         state = listing
            #         # else
            #         state = watching
            #     continue

            elif state is State.LISTING:
                self.logger.info("Starting to list objects")
                self.list_objects()
                self.logger.info("Completed listing objects")

                state = State.WATCHING
                continue

            elif state is State.WATCHING:
                self.logger.info("Starting to watch objects")
                self.watch_objects()
                self.logger.info("Completed watching objects")

                continue
