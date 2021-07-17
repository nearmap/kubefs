#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
from akube.main import launch_in_thread
from kube.tools.logs import configure_logging


def main():
    configure_logging()

    async_loop = launch_in_thread()

    items = async_loop.sync_list_objects()
    for item in items:
        print(item)


if __name__ == "__main__":
    main()
