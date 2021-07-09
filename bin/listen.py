#!/usr/bin/env python

import sys

sys.path.append(".")

# isort: split
import argparse
import os
from queue import Queue
from threading import Thread

from kubernetes import config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.configuration import Configuration

from kube.listener import ObjectClass, ObjectListener
from kube.tools.logs import configure_logging


def main(args: argparse.Namespace) -> None:
    configure_logging()

    config_fp = os.path.join(os.path.expandvars("$HOME/.kube"), args.config_file)
    context_name = args.context
    config.load_kube_config(config_file=config_fp, context=context_name)

    configuration = Configuration.get_default_copy()
    api_client = ApiClient(configuration=configuration)

    # object_class = ObjectClass(api_version="v1", kind="Namespace")
    object_class = ObjectClass(api_version="v1", kind="Pod")
    # object_class = ObjectClass(api_version="v1", kind="Event")
    conn_listen_queue: Queue = Queue()
    notify_queue: Queue = Queue()
    shutdown_queue: Queue = Queue()

    listener = ObjectListener(
        api_client=api_client,
        object_class=object_class,
        conn_listen_queue=conn_listen_queue,
        notify_queue=notify_queue,
        shutdown_queue=shutdown_queue,
    )

    list_thread = Thread(target=listener.run)
    list_thread.start()

    while True:
        event = notify_queue.get()
        kind = event.object["kind"]
        name = event.object["metadata"]["name"]
        ver = event.object["metadata"]["resourceVersion"]
        print(event.action, kind, name, ver)


if __name__ == "__main__":
    default_config_file = "minikube"
    default_context = "minikube"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config-file",
        dest="config_file",
        action="store",
        default=default_config_file,
        help="Display logs from detector (default: %s)" % default_config_file,
    )
    parser.add_argument(
        "--context",
        dest="context",
        action="store",
        default=default_context,
        help="Display logs from detector (default: %s)" % default_context,
    )
    args = parser.parse_args()

    main(args)
