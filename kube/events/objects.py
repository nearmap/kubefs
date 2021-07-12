import enum
import time
from typing import Any


class Action(enum.Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    LISTED = "LISTED"


class ObjectEvent:
    def __init__(self, *, action: Action, object: Any) -> None:
        self.action = action
        self.object = object

        self.time_created = time.time()
