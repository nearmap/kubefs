from queue import Queue
from typing import Tuple

from kube.channels.generic import ChanReceiver, ChanSender
from kube.events.objects import ObjectEvent

OEvSender = ChanSender[ObjectEvent]
OEvReceiver = ChanReceiver[ObjectEvent]


def create_oev_chan() -> Tuple[OEvSender, OEvReceiver]:
    queue: Queue = Queue()
    sender = OEvSender(queue)
    receiver = OEvReceiver(queue)
    return sender, receiver
