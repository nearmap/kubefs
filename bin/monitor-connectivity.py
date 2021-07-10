#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse

from kube.config import get_selector
from kube.connectivity import DemoLoggingReporter, launch_detector
from kube.tools.logs import configure_logging


def main(args: argparse.Namespace) -> None:
    configure_logging()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    queues = [launch_detector(ctx, want_logger=False) for ctx in contexts]
    notify_queues = [notif for notif, _ in queues]
    shutdown_queues = [shut for _, shut in queues]

    reporter = DemoLoggingReporter(notify_queues)

    try:
        reporter.run_forever()
    except KeyboardInterrupt:
        for shutdown_queue in shutdown_queues:
            shutdown_queue.put(True)


if __name__ == "__main__":
    default_context = "*"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--noisy-detector",
        dest="noisy_detector",
        action="store_true",
        help="Display logs from detector (default: False)",
    )
    parser.add_argument(
        "--context",
        dest="context",
        action="store",
        default=default_context,
        help=(
            f"Kube contexts to select - "
            f"matched like a filesystem wildcard, default: {default_context}"
        ),
    )
    args = parser.parse_args()

    main(args)
