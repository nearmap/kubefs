import logging
import random
import time
from datetime import timedelta
from queue import Empty, Queue
from threading import Thread
from typing import Optional, Sequence, Tuple
from urllib.parse import urljoin

import humanize
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout

from kube.config import Context
from kube.tools.logs import get_silent_logger


class ConnectivityEvent:
    def __init__(
        self, context: Context, time_last_reachable: float, time_last_unreachable: float
    ) -> None:
        self.context = context
        self.time_created = time.time()
        self.time_last_reachable = time_last_reachable
        self.time_last_unreachable = time_last_unreachable


class BecameReachable(ConnectivityEvent):
    pass


class BecameUnreachable(ConnectivityEvent):
    pass


class ConnectivityState:
    """
    Stores the state of connectivity to a given server.
    Notifies reporters listening on the queue whenever the state changes.
    """

    def __init__(self, context: Context, notify_queue: Queue) -> None:
        self.context = context
        self.notify_queue = notify_queue

        # the server starts out unreachable until we are told otherwise
        self.is_reachable = False

        self.time_last_reachable = None
        self.time_last_unreachable = None

    def update_reachable(self):
        if self.is_reachable is False:
            event = BecameReachable(
                context=self.context,
                time_last_reachable=self.time_last_reachable,
                time_last_unreachable=self.time_last_unreachable,
            )
            self.notify_queue.put(event)

        self.is_reachable = True
        self.time_last_reachable = time.time()

    def update_unreachable(self):
        if self.is_reachable is True:
            event = BecameUnreachable(
                context=self.context,
                time_last_reachable=self.time_last_reachable,
                time_last_unreachable=self.time_last_unreachable,
            )
            self.notify_queue.put(event)

        self.is_reachable = False
        self.time_last_unreachable = time.time()


class PollingConnectivityDetector:
    """
    Runs a loop where it tries to perform a trivial HTTP request against the API
    server every poll interval to detect whether we have connectivity to the
    server.

    The main purpose is to detect network disconnects and re-connects due to
    wifi network, mobile network and VPN network connections coming and going.

    We could use a fully fledged kube client here and eg. list the namespaces.
    But we really want to make these requests as cheap as possible for the
    server.
    """

    def __init__(
        self,
        *,
        context: Context,
        notify_queue: Queue,
        shutdown_queue: Queue,
        path="/livez",
        timeout_conn_s=3,
        timeout_read_s=1,
        poll_intervals_s: Tuple[float, float],
        logger=None,
    ):
        self.context = context
        self.shutdown_queue = shutdown_queue
        self.path = path
        self.timeout_conn_s = timeout_conn_s
        self.timeout_read_s = timeout_read_s
        self.poll_intervals_s = poll_intervals_s or (45, 60)
        self.logger = logger or logging.getLogger(f"{__name__}.detector")

        self.state = ConnectivityState(context=context, notify_queue=notify_queue)

    def create_client(self) -> requests.Session:
        """Create a client and make sure it does not retry because we want it to
        be highly responsive."""

        session = requests.Session()
        session.mount(
            prefix=self.context.cluster.server, adapter=HTTPAdapter(max_retries=0)
        )
        return session

    def test_connectivity(self) -> bool:
        session = self.create_client()

        url = urljoin(self.context.cluster.server, self.path)
        timeouts = (self.timeout_conn_s, self.timeout_read_s)
        is_reachable = False

        try:
            # We expect to get a 401 if the server is reachable but any status
            # code is fine because it proves we have a network path to the
            # server and that there is an HTTP server on the other end.
            session.get(url=url, timeout=timeouts)
            is_reachable = True

        except (ConnectionError, Timeout):
            pass

        except Exception as exc:
            raise  # unhandled for now

        if is_reachable:
            self.state.update_reachable()
        else:
            self.state.update_unreachable()

        return is_reachable

    def get_jittered_poll_interval(self):
        lower, upper = self.poll_intervals_s
        return random.uniform(lower, upper)

    def should_shutdown(self, timeout_s: float) -> bool:
        try:
            if self.shutdown_queue.get(timeout=timeout_s) is not None:
                return True
        except Empty:
            pass

        return False

    def run(self) -> None:
        while True:
            self.logger.info(
                "Starting connectivity test for %r", self.context.short_name
            )

            loop_start = time.time()
            is_reachable = self.test_connectivity()
            elapsed_s = time.time() - loop_start

            outcome = "reachable" if is_reachable else "unreachable"
            self.logger.info(
                "Completed connectivity test for %r in %.3fs with outcome: %s",
                self.context.short_name,
                elapsed_s,
                outcome.upper(),
            )

            # sleep until the end of the interval, but at least 1s
            poll_interval_s = self.get_jittered_poll_interval()
            wait_until_next_s = max(poll_interval_s - elapsed_s, 1)
            self.logger.debug(
                "Waiting %.1fs until next connectivity test for %r",
                wait_until_next_s,
                self.context.short_name,
            )

            # While we sleep poll the shutdown queue to see if we need to terminate
            if self.should_shutdown(timeout_s=wait_until_next_s):
                self.logger.info(
                    "Shutting down detector for %r", self.context.short_name
                )
                break


class DemoLoggingReporter:
    """
    A demo consumer of BecameReachable / BecameUnreachable which logs whenever
    the connectivity state changes.
    """

    def __init__(self, queues: Sequence[Queue], logger=None) -> None:
        self.queues = queues
        self.logger = logger or logging.getLogger(f"{__name__}.demo_reporter")

    def report(self, event: ConnectivityEvent) -> None:
        """
        Example log lines:

        Established connectivity to API server 'apiserver' at http://127.0.0.1:8001
        Lost connectivity to API server 'apiserver' at http://127.0.0.1:8001, was reachable for 10 minutes
        """

        verb = None
        prev_state = None
        phrase_since = ""
        elapsed_s = None

        if isinstance(event, BecameReachable):
            prev_state = "unreachable"
            if event.time_last_reachable is not None:
                verb = "Re-established"
                elapsed_s = time.time() - event.time_last_reachable
            else:
                verb = "Established"

        elif isinstance(event, BecameUnreachable):
            prev_state = "reachable"
            verb = "Lost"
            if event.time_last_unreachable is not None:
                elapsed_s = time.time() - event.time_last_unreachable

        else:
            raise NotImplementedError

        if elapsed_s:
            elapsed_pretty = humanize.naturaldelta(timedelta(seconds=elapsed_s))
            phrase_since = f", was {prev_state} for {elapsed_pretty}"

        sentence = (
            f"{verb} connectivity to API server "
            f"'{event.context.short_name}' at {event.context.cluster.server}{phrase_since}"
        )

        self.logger.info(sentence)

    def poll_queue(self, queue: Queue) -> Optional[ConnectivityEvent]:
        try:
            return queue.get_nowait()
        except Empty:
            return None

    def run_forever(self):
        while True:
            for queue in self.queues:
                event = self.poll_queue(queue)
                if event:
                    self.report(event)

            time.sleep(0.01)


def launch_detector(context: Context, want_logger=True) -> Tuple[Queue, Queue]:
    """
    Launches the detector in a background thread.
    """

    detector_logger: Optional[logging.Logger] = get_silent_logger()
    if want_logger:
        detector_logger = None

    notify_queue: Queue = Queue()
    shutdown_queue: Queue = Queue()

    detector = PollingConnectivityDetector(
        context=context,
        poll_intervals_s=(4, 6),
        notify_queue=notify_queue,
        shutdown_queue=shutdown_queue,
        logger=detector_logger,
    )

    conn_thread = Thread(target=detector.run)
    conn_thread.start()

    return notify_queue, shutdown_queue
