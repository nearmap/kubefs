#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import fnmatch
import pprint
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import deepdiff
from colored import bg, fg
from colored.colored import stylize

from akube.async_loop import get_loop, launch_in_background_thread
from akube.cluster_facade import SyncClusterFacade
from akube.model.api_resource import Namespace, Pod
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvReceiver
from kube.config import Context, get_selector
from kube.events.objects import Action
from kube.tools.logs import configure_logging
from kube.tools.terminal import TerminalPrinter

CONTEXT_COLORS = [
    [bg("dodger_blue_1"), fg("white")],
    [bg("indian_red_1a"), fg("white")],
    [bg("chartreuse_3a"), fg("white")],
    [bg("royal_blue_1"), fg("white")],
    [bg("light_pink_3"), fg("white")],
    [bg("green_3b"), fg("white")],
]

ACTION_COLORS = {
    Action.ADDED: [fg("green")],
    Action.MODIFIED: [fg("yellow")],
    Action.DELETED: [fg("dark_gray")],
    Action.LISTED: [fg("cyan")],
}

STORE: Dict[str, Any] = {}


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


def show_change(prev, cur) -> Tuple[str, Any]:
    rx_list_item = re.compile("\[(\d+)\]")
    ddiff = deepdiff.DeepDiff(prev, cur)
    values_changed = ddiff.get("values_changed")
    if values_changed:
        for key in values_changed.keys():
            if "status" in key:
                lookup_key = key.replace("root", "")
                older = eval("prev%s" % lookup_key)
                newer = eval("cur%s" % lookup_key)

                key_name = lookup_key
                key_name = re.sub("\]\[", ".", key_name)
                key_name = re.sub("[\[\]']", "", key_name)

                chunks = rx_list_item.split(lookup_key)
                if len(chunks) == 3:
                    # import ipdb as pdb; pdb.set_trace() # BREAKPOINT
                    prefix = chunks[0]
                    index = int(chunks[1])
                    lst = eval("prev%s" % prefix)

                    prefix = re.sub("\]\[", ".", prefix)
                    prefix = re.sub("[\[\]']", "", prefix)

                    try:
                        last = eval("lst[%s]['type']" % index)
                        key_name = "%s.%s" % (prefix, last)
                    except KeyError:
                        pass

                key_name = stylize(key_name, styles=[fg("magenta")])
                return "%s: %s -> %s" % (key_name, older, newer), None
    return "", ddiff


def run_forever(contexts: List[Context], oev_receivers: Sequence[OEvReceiver]) -> None:
    while True:
        for oev_receiver in oev_receivers:
            event = oev_receiver.recv_nowait()
            if event:
                uid = event.object["metadata"]["uid"]

                prev = STORE.get(uid)
                change, ddiff = "", None
                if prev and event.action is Action.MODIFIED:
                    change, ddiff = show_change(prev, event.object)

                kind = event.object["kind"]
                name = event.object["metadata"]["name"]
                ver = event.object["metadata"]["resourceVersion"]

                ctx_cols = CONTEXT_COLORS[
                    contexts.index(event.context) % len(CONTEXT_COLORS)
                ]
                act_cols = ACTION_COLORS[event.action]

                ctx = stylize(event.context.short_name, styles=ctx_cols)
                act = stylize(event.action.value, styles=act_cols)

                print(ctx, act, kind, name, change)
                if ddiff:
                    pprint.pprint(ddiff)

                # cache in store
                STORE[uid] = event.object

        time.sleep(0.01)


def main(args: argparse.Namespace) -> None:
    configure_logging()
    async_loop = launch_in_background_thread()

    printer = TerminalPrinter()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    oev_receivers = [launch(args, ctx) for ctx in contexts]

    try:
        run_forever(contexts, oev_receivers)
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
    args = parser.parse_args()

    main(args)
