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

    chans = [launch_detector(ctx, want_logger=args.noisy_detector) for ctx in contexts]
    cev_receivers = [notif for notif, _ in chans]
    exit_senders = [exit for _, exit in chans]

    reporter = DemoLoggingReporter(cev_receivers)

    try:
        reporter.run_forever()
    except KeyboardInterrupt:
        for exit_sender in exit_senders:
            exit_sender.send_exit()


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
