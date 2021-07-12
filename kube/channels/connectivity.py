from queue import Queue
from typing import Tuple

from kube.channels.generic import ChanReceiver, ChanSender
from kube.events.connectivity import ConnectivityEvent

CEvSender = ChanSender[ConnectivityEvent]
CEvReceiver = ChanReceiver[ConnectivityEvent]


def create_cev_chan() -> Tuple[CEvSender, CEvReceiver]:
    queue: Queue = Queue()
    sender = CEvSender(queue)
    receiver = CEvReceiver(queue)
    return sender, receiver
