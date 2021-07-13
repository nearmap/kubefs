#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import time
from typing import List, Sequence, Tuple

from colored import bg, fg
from colored.colored import stylize

from kube.channels.exit import ExitSender
from kube.channels.objects import OEvReceiver
from kube.config import Context, get_selector
from kube.connectivity import launch_detector
from kube.events.objects import Action
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


def launch(
    args: argparse.Namespace, context: Context, object_class: ObjectClass
) -> Tuple[OEvReceiver, List[ExitSender]]:
    cev_receiver, det_exit_sender = launch_detector(
        context, want_logger=args.noisy_detector
    )
    oev_receiver, lis_exit_sender = launch_listener(context, cev_receiver, object_class)
    return oev_receiver, [det_exit_sender, lis_exit_sender]


def run_forever(contexts: List[Context], oev_receivers: Sequence[OEvReceiver]) -> None:
    while True:
        for oev_receiver in oev_receivers:
            event = oev_receiver.recv_nowait()
            if event:
                kind = event.object["kind"]
                name = event.object["metadata"]["name"]
                ver = event.object["metadata"]["resourceVersion"]

                ctx_cols = CONTEXT_COLORS[
                    contexts.index(event.context) % len(CONTEXT_COLORS)
                ]
                act_cols = ACTION_COLORS[event.action]

                ctx = stylize(event.context.short_name, styles=ctx_cols)
                act = stylize(event.action.value, styles=act_cols)

                print(ctx, act, kind, name, ver)

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
    args = parser.parse_args()

    main(args)
