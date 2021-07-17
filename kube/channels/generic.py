from queue import Empty, Queue
from typing import Generic, Optional, TypeVar

T = TypeVar("T")


class ChanSender(Generic[T]):
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def send(self, obj: T) -> None:
        self.queue.put_nowait(obj)


class ChanReceiver(Generic[T]):
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def recv(self) -> T:
        return self.queue.get()

    def recv_nowait(self) -> Optional[T]:
        try:
            return self.queue.get_nowait()
        except Empty:
            pass

        return None
