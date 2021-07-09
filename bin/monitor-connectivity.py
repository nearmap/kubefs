#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
from queue import Queue
from threading import Thread

from kube.connectivity import ConnectivityDetector, DemoLoggingReporter
from kube.tools.logs import configure_logging, get_silent_logger


def main(args: argparse.Namespace) -> None:
    configure_logging()

    detector_logger = get_silent_logger()
    if args.noisy_detector:
        detector_logger = None

    queue = Queue()
    detector = ConnectivityDetector(
        apiserver_baseurl=args.server_url,
        poll_interval_s=5,
        queue=queue,
        logger=detector_logger,
    )
    reporter = DemoLoggingReporter(queue)

    conn_thread = Thread(target=detector.run)
    conn_thread.start()

    reporter.run_forever()


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
