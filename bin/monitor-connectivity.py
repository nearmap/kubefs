#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import logging
from queue import Queue
from threading import Thread
from typing import Optional

from kube.connectivity import ConnectivityDetector, DemoLoggingReporter, Server
from kube.tools.logs import configure_logging, get_silent_logger


def main(args: argparse.Namespace) -> None:
    configure_logging()

    detector_logger: Optional[logging.Logger] = get_silent_logger()
    if args.noisy_detector:
        detector_logger = None

    notify_queue: Queue = Queue()
    shutdown_queue: Queue = Queue()

    apiserver = Server(name="apiserver", baseurl=args.server_url)

    detector = ConnectivityDetector(
        apiserver=apiserver,
        poll_interval_s=5,
        notify_queue=notify_queue,
        shutdown_queue=shutdown_queue,
        logger=detector_logger,
    )
    reporter = DemoLoggingReporter(notify_queue)

    conn_thread = Thread(target=detector.run)
    conn_thread.start()

    try:
        reporter.run_forever()
    except KeyboardInterrupt:
        shutdown_queue.put(True)


if __name__ == "__main__":
    defautl_server_url = "http://127.0.0.1:8001"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--noisy-detector",
        dest="noisy_detector",
        action="store_true",
        help="Display logs from detector (default: False)",
    )
    parser.add_argument(
        "--server-url",
        dest="server_url",
        action="store",
        default=defautl_server_url,
        help=f"API server to test against, default: {defautl_server_url}",
    )
    args = parser.parse_args()

    main(args)
