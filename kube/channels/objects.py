from queue import Queue

from kube.channels.generic import ChanReceiver, ChanSender
from kube.events.objects import ObjectEvent

OEvSender = ChanSender[ObjectEvent]
OEvReceiver = ChanReceiver[ObjectEvent]


class OEvChan:
    def __init__(self, sender: OEvSender, receiver: OEvReceiver) -> None:
        self.sender = sender
        self.receiver = receiver


def create_oev_chan() -> OEvChan:
    queue: Queue = Queue()
    sender = OEvSender(queue)
    receiver = OEvReceiver(queue)
    return OEvChan(sender=sender, receiver=receiver)
