#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
from queue import Queue
from threading import Thread

from kubernetes import config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.configuration import Configuration

from kube.channels.connectivity import create_cev_chan
from kube.channels.exit import create_exit_chan
from kube.channels.objects import create_oev_chan
from kube.config import get_selector
from kube.listener import ObjectClass, ObjectListener
from kube.tools.logs import configure_logging


def main(args: argparse.Namespace) -> None:
    configure_logging()

    selector = get_selector()
    contexts = selector.fnmatch_context(args.context)

    assert len(contexts) == 1
    context = contexts[0]

    config.load_kube_config(config_file=context.file.filepath, context=context.name)

    configuration = Configuration.get_default_copy()
    api_client = ApiClient(configuration=configuration)

    # object_class = ObjectClass(api_version="v1", kind="Namespace")
    object_class = ObjectClass(api_version="v1", kind="Pod")
    # object_class = ObjectClass(api_version="v1", kind="Event")
    cev_sender, cev_receiver = create_cev_chan()
    exit_sender, exit_receiver = create_exit_chan()
    oev_sender, oev_receiver = create_oev_chan()

    listener = ObjectListener(
        api_client=api_client,
        object_class=object_class,
        cev_receiver=cev_receiver,
        exit_receiver=exit_receiver,
        oev_sender=oev_sender,
    )

    list_thread = Thread(target=listener.run)
    list_thread.start()

    while True:
        event = oev_receiver.recv()
        kind = event.object["kind"]
        name = event.object["metadata"]["name"]
        ver = event.object["metadata"]["resourceVersion"]
        print(event.action, kind, name, ver)


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
