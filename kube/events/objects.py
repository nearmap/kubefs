import enum
import time
from typing import Any

from kube.config import Context


class Action(enum.Enum):
    ADDED = "ADDED"
    MODIFIED = "MODIFIED"
    DELETED = "DELETED"
    LISTED = "LISTED"


class ObjectEvent:
    def __init__(self, *, context: Context, action: Action, object: Any) -> None:
        self.context = context
        self.action = action
        self.object = object

        self.time_created = time.time()
