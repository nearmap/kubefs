import time
from datetime import timedelta
from typing import Generic, Optional, TypeVar

import humanize

V = TypeVar("V")


class Value(Generic[V]):
    def __init__(self) -> None:
        # the current value for the attribute
        self.current_value: Optional[V] = None
        # the timestamp when that value was (first) set
        self.current_time: Optional[float] = None

        # the previous value for the attribute
        self.previous_value: Optional[V] = None
        # the timestamp when that value was (first) set
        self.previous_time: Optional[float] = None

    def __repr__(self) -> str:
        return "<%s curval=%r, curtime=%r, prevval=%r, prevtime=%r>" % (
            self.__class__.__name__,
            self.current_value,
            self.current_time,
            self.previous_value,
            self.previous_time,
        )

    def set(self, value: V, ts: float) -> None:
        if value != self.current_value:
            self.previous_value = self.current_value
            self.previous_time = self.current_time

            self.current_value = value
            self.current_time = ts

    @property
    def current_elapsed_pretty(self) -> Optional[str]:
        if self.current_time:
            delta = time.time() - self.current_time
            return humanize.naturaldelta(timedelta(seconds=delta))

        return None
