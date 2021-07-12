from queue import Empty, Queue
from typing import Optional, Tuple

from kube.events.objects import ObjectEvent


class OEvSender:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def send(self, obj: ObjectEvent) -> None:
        self.queue.put_nowait(obj)


class OEvReceiver:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def recv(self) -> ObjectEvent:
        return self.queue.get()

    def recv_nowait(self) -> Optional[ObjectEvent]:
        try:
            return self.queue.get_nowait()
        except Empty:
            pass

        return None


def create_oev_chan() -> Tuple[OEvSender, OEvReceiver]:
    queue: Queue = Queue()
    sender = OEvSender(queue)
    receiver = OEvReceiver(queue)
    return sender, receiver
