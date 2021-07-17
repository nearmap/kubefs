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

    async_loop = launch_in_thread(contexts)

    for context in contexts:
        items = async_loop.sync_list_objects(context)
        for item in items:
            print(context.short_name, item)


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
