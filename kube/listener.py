import enum
import logging
import re
import time
from threading import Thread
from typing import Any, Optional, Tuple

from kubernetes import config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.configuration import Configuration
from kubernetes.client.exceptions import ApiException
from kubernetes.dynamic.client import DynamicClient

from kube.channels.connectivity import CEvReceiver
from kube.channels.exit import ExitReceiver, ExitSender, create_exit_chan
from kube.channels.objects import OEvReceiver, OEvSender, create_oev_chan
from kube.config import Context
from kube.events.connectivity import BecameReachable, BecameUnreachable
from kube.events.objects import Action, ObjectEvent


class ObjectClass:
    def __init__(self, *, api_version: str, kind: str) -> None:
        self.api_version = api_version
        self.kind = kind


class State(enum.Enum):
    CONNECTING = 1
    LISTING = 2
    WATCHING = 3
    EXITING = 4


class ObjectListener:
    # Reason: Expired: too old resource version: 13130 (154867)
    rx_too_old = re.compile("too old resource version: \d+ \((\d+)\)")

    def __init__(
        self,
        *,
        context: Context,
        api_client: ApiClient,
        object_class: ObjectClass,
        cev_receiver: CEvReceiver,
        exit_receiver: ExitReceiver,
        oev_sender: OEvSender,
        watch_timeout_s=60,
        logger=None,
    ) -> None:
        self.context = context
        self.api_client = api_client
        self.object_class = object_class
        self.cev_receiver = cev_receiver
        self.exit_receiver = exit_receiver
        self.oev_sender = oev_sender
        self.watch_timeout_s = watch_timeout_s
        self.logger = logger or logging.getLogger(__name__)

        self.time_last_listing = None
        self.time_last_watch = None
        self.highest_resource_version = 0

        # self.state = State.LISTING
        self.state = State.WATCHING

    def should_exit(self) -> bool:
        if self.state is State.EXITING:
            return True

        should_exit = self.exit_receiver.should_exit()

        if should_exit:
            self.state = State.EXITING

        return should_exit

    def notify(self, item: Any, watched=False) -> None:
        dct = item
        action = Action.LISTED

        if watched:
            dct = item["raw_object"]
            action = self.parse_action(item)

        resource_version = int(dct["metadata"]["resourceVersion"])
        if resource_version > self.highest_resource_version:
            self.highest_resource_version = resource_version

        event = ObjectEvent(context=self.context, action=action, object=dct)
        self.oev_sender.send(event)

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

                    # detect exit condition in between items without completing
                    # the watch timeout period
                    if self.should_exit():
                        return

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

    def run(self) -> None:
        while True:
            print("loop", self.state)
            if self.should_exit():
                self.logger.info(
                    "Shutting down listener for %s", self.context.short_name
                )
                break

            if self.state is not State.CONNECTING:
                event = self.cev_receiver.recv_nowait()
                if event and isinstance(event, BecameUnreachable):
                    self.state = State.CONNECTING
                    self.logger.info("Lost connectivity to %s", self.context.short_name)
                    continue

            if self.state is State.CONNECTING:
                event = self.cev_receiver.recv()
                if isinstance(event, BecameReachable):
                    # # disconnected long enough to have to list again?
                    # state = listing
                    self.state = State.WATCHING
                    self.logger.info(
                        "Re-established connectivity to %s", self.context.short_name
                    )
                    continue

            elif self.state is State.LISTING:
                self.logger.debug(
                    "Starting to list objects in %s", self.context.short_name
                )
                self.list_objects()
                self.logger.debug(
                    "Completed listing objects in %s", self.context.short_name
                )

                self.state = State.WATCHING
                continue

            elif self.state is State.WATCHING:
                self.logger.debug(
                    "Starting to watch objects in %s", self.context.short_name
                )
                self.watch_objects()
                self.logger.debug(
                    "Completed watching objects in %s", self.context.short_name
                )
                continue


def launch_listener(
    context: Context,
    cev_receiver: CEvReceiver,
    object_class: ObjectClass,
) -> Tuple[OEvReceiver, ExitSender]:
    """
    Launches the listener in a background thread.
    """

    config.load_kube_config(config_file=context.file.filepath, context=context.name)
    configuration = Configuration.get_default_copy()
    api_client = ApiClient(configuration=configuration)

    exit_sender, exit_receiver = create_exit_chan()
    oev_sender, oev_receiver = create_oev_chan()

    logger = logging.getLogger("listener")
    # logger.level = logging.INFO
    logger.level = logging.DEBUG

    listener = ObjectListener(
        context=context,
        api_client=api_client,
        object_class=object_class,
        cev_receiver=cev_receiver,
        exit_receiver=exit_receiver,
        oev_sender=oev_sender,
        logger=logger,
    )

    list_thread = Thread(target=listener.run)
    list_thread.start()

    return oev_receiver, exit_sender
