from datetime import timedelta
from typing import Generic, Optional, TypeVar

import humanize

V = TypeVar("V")


class Value(Generic[V]):
    def __init__(self) -> None:
        self.current_value: Optional[V] = None
        self.current_time: Optional[float] = None

        self.previous_value: Optional[V] = None
        self.previous_time: Optional[float] = None

    def __repr__(self) -> str:
        return "<%s curval=%r, curtime=%r, prevval=%r, prevtime=%r>" % (
            self.__class__.__name__,
            self.current_value,
            self.current_time,
            self.previous_value,
            self.previous_time,
        )

    def set(self, value: V, ts: float):
        self.previous_value = self.current_value
        self.previous_time = self.current_time

        self.current_value = value
        self.current_time = ts

    @property
    def current_elapsed_pretty(self) -> Optional[str]:
        if self.current_time and self.previous_time:
            delta = self.current_time - self.previous_time
            return humanize.naturaldelta(timedelta(seconds=delta))

        return None
