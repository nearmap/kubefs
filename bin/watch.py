#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split

import argparse
import fnmatch
from typing import Optional

from akube.async_loop import get_loop, launch_in_background_thread
from akube.cluster_facade import SyncClusterFacade
from akube.model.api_resource import Namespace, Pod
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvReceiver
from kube.config import Context, get_selector
from kube.tools.logs import configure_logging
from kube.tools.terminal import TerminalPrinter
from podview.listener import Listener


def find_matching_namespace(
    args: argparse.Namespace, context: Context
) -> Optional[str]:
    if not args.namespace:
        return None

    async_loop = get_loop()
    facade = SyncClusterFacade(async_loop=async_loop, context=context)
    selector = ObjectSelector(res=Namespace)
    namespace_objs = facade.list_objects(selector=selector)
    namespaces = [namespace["metadata"]["name"] for namespace in namespace_objs]

    namespaces = fnmatch.filter(namespaces, args.namespace)
    assert len(namespaces) == 1

    return namespaces[0]


def launch(args: argparse.Namespace, context: Context) -> OEvReceiver:
    async_loop = get_loop()
    facade = SyncClusterFacade(async_loop=async_loop, context=context)

    namespace = find_matching_namespace(args, context)
    selector = ObjectSelector(res=Pod, namespace=namespace)

    # list first to advance the resourceVersion in the client to the current
    # point in time - so we can skip events that are in the past
    facade.list_objects(selector=selector)

    return facade.start_watching(selector=selector)


def main(args: argparse.Namespace) -> None:
    configure_logging()
    launch_in_background_thread()

    printer = TerminalPrinter()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    oev_receivers = [launch(args, ctx) for ctx in contexts]
    listener = Listener(oev_receivers)

    try:
        listener.run(36000000)
    except KeyboardInterrupt:
        printer.loudln("\nCtrl-C received")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--context",
        dest="context",
        action="store",
        required=True,
        help=(f"Kube contexts to select - matched like a filesystem wildcard"),
    )
    parser.add_argument(
        "--namespace",
        dest="namespace",
        action="store",
        help=(f"Kube namespace to select - matched like a filesystem wildcard"),
    )
    # parser.add_argument(
    #     "--pod",
    #     dest="pod",
    #     action="store",
    #     required=True,
    #     help=(f"Kube pod name to select - matched like a filesystem wildcard"),
    # )
    args = parser.parse_args()

    main(args)
