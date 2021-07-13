#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import time
from threading import Thread
from typing import List, Sequence, Tuple

from colored import bg, fg
from colored.colored import stylize
from kubernetes import config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.configuration import Configuration

from kube.channels.connectivity import create_cev_chan
from kube.channels.exit import ExitSender, create_exit_chan
from kube.channels.objects import OEvReceiver, create_oev_chan
from kube.config import Context, get_selector
from kube.events.objects import Action
from kube.listener import ObjectClass, ObjectListener
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
    context: Context, object_class: ObjectClass
) -> Tuple[OEvReceiver, ExitSender]:
    config.load_kube_config(config_file=context.file.filepath, context=context.name)
    configuration = Configuration.get_default_copy()
    api_client = ApiClient(configuration=configuration)

    cev_sender, cev_receiver = create_cev_chan()
    exit_sender, exit_receiver = create_exit_chan()
    oev_sender, oev_receiver = create_oev_chan()

    listener = ObjectListener(
        context=context,
        api_client=api_client,
        object_class=object_class,
        cev_receiver=cev_receiver,
        exit_receiver=exit_receiver,
        oev_sender=oev_sender,
    )

    list_thread = Thread(target=listener.run)
    list_thread.start()

    return oev_receiver, exit_sender


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

    chans = [launch(ctx, object_class) for ctx in contexts]
    oev_receivers = [oev_recv for oev_recv, _ in chans]
    exit_senders = [exit for _, exit in chans]

    try:
        run_forever(contexts, oev_receivers)
    except KeyboardInterrupt:
        printer.loudln("\nSending exit msg to all threads - allow a few seconds to exit")
        for exit_sender in exit_senders:
            exit_sender.send_exit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--context",
        dest="context",
        action="store",
        required=True,
        help=(f"Kube contexts to select - matched like a filesystem wildcard"),
    )
    args = parser.parse_args()

    main(args)
