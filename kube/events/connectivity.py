import time

from kube.config import Context


class ConnectivityEvent:
    def __init__(
        self, context: Context, time_last_reachable: float, time_last_unreachable: float
    ) -> None:
        self.context = context
        self.time_created = time.time()
        self.time_last_reachable = time_last_reachable
        self.time_last_unreachable = time_last_unreachable


class BecameReachable(ConnectivityEvent):
    pass


class BecameUnreachable(ConnectivityEvent):
    pass
