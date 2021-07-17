#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split

import argparse
import curses
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
from podview.display import Display


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
        context,
        want_logger=False,
    )
    namespace = find_matching_namespace(args, context)
    oev_receiver, lis_exit_sender = launch_listener(
        context, cev_receiver, object_class, namespace
    )
    return oev_receiver, [det_exit_sender, lis_exit_sender]


def main(args: argparse.Namespace) -> None:
    configure_logging()

    printer = TerminalPrinter()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    object_class = ObjectClass(api_version="v1", kind="Pod")

    chans = [launch(args, ctx, object_class) for ctx in contexts]
    oev_receivers = [oev_recv for oev_recv, _ in chans]
    exit_sender_pairs = [exits for _, exits in chans]

    display = Display(oev_receivers=oev_receivers)

    try:
        display.start()
    except KeyboardInterrupt:
        pass
    finally:
        curses.endwin()
        printer.loudln(
            "\nSending exit msg to all threads - allow a few seconds to exit"
        )
        for pair in exit_sender_pairs:
            for exit_sender in pair:
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
    parser.add_argument(
        "--namespace",
        dest="namespace",
        action="store",
        help=(f"Kube namespace to select - matched like a filesystem wildcard"),
    )
    parser.add_argument(
        "--pod",
        dest="pod",
        action="store",
        required=True,
        help=(f"Kube pod name to select - matched like a filesystem wildcard"),
    )
    args = parser.parse_args()

    main(args)
