#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import time

from akube.async_loop import get_loop, launch_in_background_thread
from akube.main import launch_in_thread
from kube.config import get_selector
from kube.events.objects import ObjectEvent
from kube.tools.logs import configure_logging
import asyncio


def main(args: argparse.Namespace) -> None:
    configure_logging()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)
    context = contexts[0]

    async_loop = launch_in_background_thread()
    fut = asyncio.run_coroutine_threadsafe(async_loop.get_client(context), async_loop.loop)

    while not fut.done():
        time.sleep(0.001)

    print(fut.result())


def zmain(args: argparse.Namespace) -> None:
    configure_logging()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    async_loop = launch_in_thread(contexts)

    # for context in contexts:
    #     items = async_loop.sync_list_objects(context)
    #     for item in items:
    #         print(context.short_name, item)
    # return

    receivers = []
    for context in contexts:
        oev_receiver = async_loop.add_watch(context)
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
