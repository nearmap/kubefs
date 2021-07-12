"""
Channel used be one thread (usually the spawning thread) to signal the other
thread to exit.
"""

from queue import Empty, Full, Queue
from typing import Tuple


class ExitSender:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def send_exit(self):
        try:
            self.queue.put_nowait(True)
        except Full:
            pass  # exit() was already called before, nothing to do here


class ExitReceiver:
    def __init__(self, queue: Queue) -> None:
        self.queue = queue

    def should_exit(self, timeout=None) -> bool:
        block = True if timeout is not None else False

        try:
            if self.queue.get(block=block, timeout=timeout) is not None:
                return True
        except Empty:
            pass

        return False


def create_exit_chan() -> Tuple[ExitSender, ExitReceiver]:
    queue: Queue = Queue(maxsize=1)
    sender = ExitSender(queue)
    receiver = ExitReceiver(queue)
    return sender, receiver
