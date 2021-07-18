#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import time

from typing import List
from kube.channels.objects import OEvReceiver
from akube.async_loop import launch_in_background_thread
from kube.config import get_selector
from kube.events.objects import ObjectEvent
from kube.tools.logs import configure_logging
from akube.cluster_facade import SyncClusterFacade


def main(args: argparse.Namespace) -> None:
    configure_logging()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    async_loop = launch_in_background_thread()

    # context = contexts[0]
    # facade = SyncClusterFacade(async_loop=async_loop, context=context)
    # items = facade.list()
    # for item in items:
    #     print(item)

    receivers: List[OEvReceiver] = []
    for context in contexts:
        facade = SyncClusterFacade(async_loop=async_loop, context=context)
        oev_receiver = facade.watch()
        receivers.append(oev_receiver)

    while True:
        for receiver in receivers:
            event: ObjectEvent = receiver.recv_nowait()
            if event:
                print(
                    event.context.short_name,
                    event.action,
                    event.object["metadata"]["name"],
                )

        time.sleep(0.01)


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
