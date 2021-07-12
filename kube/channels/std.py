from queue import Empty, Queue
from typing import Any, Optional, Tuple


class StdSender:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def send(self, obj: Any) -> None:
        self.queue.put_nowait(obj)


class StdReceiver:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def recv(self) -> Any:
        return self.queue.get()

    def recv_nowait(self) -> Optional[Any]:
        try:
            return self.queue.get_nowait()
        except Empty:
            pass

        return None


def create_std_chan() -> Tuple[StdSender, StdReceiver]:
    queue: Queue = Queue()
    sender = StdSender(queue)
    receiver = StdReceiver(queue)
    return sender, receiver
