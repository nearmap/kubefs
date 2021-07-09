import logging
import time
from datetime import timedelta
from queue import Empty, Queue
from urllib.parse import urljoin

import humanize
import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError, Timeout


class Server:
    def __init__(self, name: str, baseurl: str) -> None:
        self.name = name
        self.baseurl = baseurl


class Event:
    def __init__(
        self, server: Server, time_last_reachable: float, time_last_unreachable: float
    ) -> None:
        self.server = server
        self.time_last_reachable = time_last_reachable
        self.time_last_unreachable = time_last_unreachable


class BecameReachable(Event):
    pass


class BecameUnreachable(Event):
    pass


class ConnectivityState:
    """
    Stores the state of connectivity to a given server.
    Notifies reporters listening on the queue whenever the state changes.
    """

    def __init__(self, server: Server, notify_queue: Queue) -> None:
        self.server = server
        self.notify_queue = notify_queue

        # the server starts out unreachable until we are told otherwise
        self.is_reachable = False

        self.time_last_reachable = None
        self.time_last_unreachable = None

    def report_reachable(self):
        if self.is_reachable is False:
            event = BecameReachable(
                server=self.server,
                time_last_reachable=self.time_last_reachable,
                time_last_unreachable=self.time_last_unreachable,
            )
            self.notify_queue.put(event)

        self.is_reachable = True
        self.time_last_reachable = time.time()

    def report_unreachable(self):
        if self.is_reachable is True:
            event = BecameUnreachable(
                server=self.server,
                time_last_reachable=self.time_last_reachable,
                time_last_unreachable=self.time_last_unreachable,
            )
            self.notify_queue.put(event)

        self.is_reachable = False
        self.time_last_unreachable = time.time()


class ConnectivityDetector:
    """
    Runs a loop where it tries to perform a trivial HTTP request against the API
    server every poll interval to detect whether we have connectivity to the
    server.

    The main purpose is to detect network disconnects and re-connects due to
    wifi network, mobile network and VPN network connections coming and going.
    """

    def __init__(
        self,
        *,
        apiserver: Server,
        notify_queue: Queue,
        shutdown_queue: Queue,
        path="/livez",
        timeout_conn_s=3,
        timeout_read_s=1,
        poll_interval_s=60,
        logger=None,
    ):
        self.apiserver = apiserver
        self.shutdown_queue = shutdown_queue
        self.path = path
        self.timeout_conn_s = timeout_conn_s
        self.timeout_read_s = timeout_read_s
        self.poll_interval_s = poll_interval_s
        self.logger = logger or logging.getLogger(f"{__name__}.detector")

        self.state = ConnectivityState(server=apiserver, notify_queue=notify_queue)

    def create_client(self) -> requests.Session:
        """Create a client and make sure it does not retry because we want it to
        be highly responsive."""

        session = requests.Session()
        session.mount(prefix=self.apiserver.baseurl, adapter=HTTPAdapter(max_retries=0))
        return session

    def test_connectivity(self) -> bool:
        session = self.create_client()

        url = urljoin(self.apiserver.baseurl, self.path)
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
            self.state.report_reachable()
        else:
            self.state.report_unreachable()

        return is_reachable

    def should_shutdown(self, timeout_s: float) -> bool:
        try:
            if self.shutdown_queue.get(timeout=timeout_s) is not None:
                return True
        except Empty:
            pass

        return False

    def run(self) -> None:
        while True:
            self.logger.info("Starting connectivity test")

            loop_start = time.time()
            is_reachable = self.test_connectivity()
            elapsed_s = time.time() - loop_start

            outcome = "reachable" if is_reachable else "unreachable"
            self.logger.info(
                "Completed connectivity test in %.3fs with outcome: %s",
                elapsed_s,
                outcome.upper(),
            )

            # sleep until the end of the interval, but at least 1s
            wait_until_next_s = max(self.poll_interval_s - elapsed_s, 1)
            self.logger.debug(
                "Waiting %.1fs until next connectivity test", wait_until_next_s
            )

            # While we sleep poll the shutdown queue to see if we need to terminate
            if self.should_shutdown(timeout_s=wait_until_next_s):
                self.logger.info("Shutting down")
                break


class DemoLoggingReporter:
    """
    A demo consumer of BecameReachable / BecameUnreachable which logs whenever
    the connectivity state changes.
    """

    def __init__(self, queue: Queue, logger=None) -> None:
        self.queue = queue
        self.logger = logger or logging.getLogger(f"{__name__}.demo_reporter")

    def report(self, event: Event) -> None:
        verb = None
        state = None
        phrase_since = ""
        elapsed_s = None

        if isinstance(event, BecameReachable):
            state = "reachable"
            if event.time_last_reachable is not None:
                verb = "Re-established"
                elapsed_s = time.time() - event.time_last_reachable
            else:
                verb = "Established"

        elif isinstance(event, BecameUnreachable):
            state = "unreachable"
            verb = "Lost"
            if event.time_last_unreachable is not None:
                elapsed_s = time.time() - event.time_last_unreachable

        else:
            raise NotImplementedError

        if elapsed_s:
            elapsed_pretty = humanize.naturaldelta(timedelta(seconds=elapsed_s))
            phrase_since = f", was last {state} {elapsed_pretty} ago"

        sentence = (
            f"{verb} connectivity to the API server "
            f"'{event.server.name}' at {event.server.baseurl}{phrase_since}"
        )

        self.logger.info(sentence)

    def run_forever(self):
        while True:
            event = self.queue.get()
            self.report(event)
