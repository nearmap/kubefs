#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse

from akube.main import launch_in_thread
from kube.config import get_selector
from kube.tools.logs import configure_logging


def main(args: argparse.Namespace) -> None:
    configure_logging()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)
    assert len(contexts) == 1

    context = contexts[0]

    async_loop = launch_in_thread(context)

    items = async_loop.sync_list_objects()
    for item in items:
        print(item)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--context",
        dest="context",
        action="store",
        required=True,
        help=(f"Kube contexts to select - " f"matched like a filesystem wildcard"),
    )
    args = parser.parse_args()

    main(args)
