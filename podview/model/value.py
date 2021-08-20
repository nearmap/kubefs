import time
from datetime import timedelta
from typing import Generic, Optional, TypeVar

from podview.common.timekeeping import humanize_delta

V = TypeVar("V")


class Value(Generic[V]):
    def __init__(self) -> None:
        # the current value for the attribute
        self.current_value: Optional[V] = None
        # the timestamp when that value was (first) set
        self.current_time: Optional[float] = None
        # if the current value represents a state, is it a terminal state or and
        # intermediate state? for terminal states elapsed pretty will show 'ago'
        self.current_is_terminal_state: bool = False

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

    def set(self, value: V, ts: float, is_terminal_state: bool = False) -> None:
        if value != self.current_value:
            self.previous_value = self.current_value
            self.previous_time = self.current_time

            self.current_value = value
            self.current_time = ts
            self.current_is_terminal_state = is_terminal_state

    @property
    def current_elapsed_pretty(self) -> Optional[str]:
        if self.current_time:
            delta = time.time() - self.current_time
            fmt = humanize_delta(timedelta(seconds=delta))

            if self.current_is_terminal_state:
                fmt = f"{fmt} ago"

            return fmt

        return None
