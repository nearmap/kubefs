from queue import Empty, Queue
from typing import Optional, Tuple

from kube.events.connectivity import ConnectivityEvent


class CEvSender:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def send(self, obj: ConnectivityEvent) -> None:
        self.queue.put_nowait(obj)


class CEvReceiver:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def recv(self) -> ConnectivityEvent:
        return self.queue.get()

    def recv_nowait(self) -> Optional[ConnectivityEvent]:
        try:
            return self.queue.get_nowait()
        except Empty:
            pass

        return None


def create_cev_chan() -> Tuple[CEvSender, CEvReceiver]:
    queue: Queue = Queue()
    sender = CEvSender(queue)
    receiver = CEvReceiver(queue)
    return sender, receiver
