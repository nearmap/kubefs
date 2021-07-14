#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import pprint
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import deepdiff
from colored import bg, fg
from colored.colored import stylize

from kube.channels.exit import ExitSender
from kube.channels.objects import OEvReceiver
from kube.config import Context, get_selector
from kube.connectivity import launch_detector
from kube.events.objects import Action
from kube.finder import Finder
from kube.listener import ObjectClass, launch_listener
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

    finder = Finder(context)
    object_class = ObjectClass(api_version="v1", kind="Namespace")

    namespaces = finder.list_all(object_class)
    namespaces = finder.fnmatch_objects(args.namespace, namespaces)
    assert len(namespaces) == 1

    return namespaces[0]["metadata"]["name"]


def launch(
    args: argparse.Namespace, context: Context, object_class: ObjectClass
) -> Tuple[OEvReceiver, List[ExitSender]]:
    cev_receiver, det_exit_sender = launch_detector(
        context, want_logger=args.noisy_detector
    )
    namespace = find_matching_namespace(args, context)
    oev_receiver, lis_exit_sender = launch_listener(
        context, cev_receiver, object_class, namespace
    )
    return oev_receiver, [det_exit_sender, lis_exit_sender]


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

    printer = TerminalPrinter()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    # object_class = ObjectClass(api_version="v1", kind="Namespace")
    object_class = ObjectClass(api_version="v1", kind="Pod")
    # object_class = ObjectClass(api_version="v1", kind="Event")

    chans = [launch(args, ctx, object_class) for ctx in contexts]
    oev_receivers = [oev_recv for oev_recv, _ in chans]
    exit_sender_pairs = [exits for _, exits in chans]

    try:
        run_forever(contexts, oev_receivers)
    except KeyboardInterrupt:
        printer.loudln(
            "\nSending exit msg to all threads - allow a few seconds to exit"
        )
        for pair in exit_sender_pairs:
            for exit_sender in pair:
                exit_sender.send_exit()


if __name__ == "__main__":
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
