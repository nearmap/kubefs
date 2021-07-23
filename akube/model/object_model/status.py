from datetime import datetime
from typing import List, Optional

from akube.model.object_model.helpers import maybe_parse_date
from akube.model.object_model.types import RawObject


class ContainerState:
    def __init__(self, obj: RawObject) -> None:
        pass


class ContainerStatus:
    def __init__(self, obj: RawObject) -> None:
        self.name: str = obj["name"]
        self.ready: bool = obj["ready"]
        self.restartCount: int = obj["restartCount"]
        self.image: str = obj["image"]
        self.imageID: str = obj["imageID"]

        self.started: Optional[bool] = obj.get("started")
        self.state: Optional[ContainerState] = None
        self.lastState: Optional[ContainerState] = None

        state = obj.get("state")
        if state:
            self.state = ContainerState(state)

        lastState = obj.get("lastState")
        if lastState:
            self.lastState = ContainerState(lastState)


class ObjectStatus:
    def __init__(self, obj: RawObject) -> None:
        self._status = obj["status"]

        self.phase = self._status["phase"]


class PodStatus(ObjectStatus):
    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)

        self.startTime: Optional[datetime] = None
        self.reason: Optional[str] = None
        self.message: Optional[str] = None
        self.containerStatuses: List[ContainerStatus] = None

        self.startTime = maybe_parse_date(obj.get("startTime"))
        self.message = obj.get("message")
        self.reason = obj.get("reason")
        self.containerStatuses = [
            ContainerStatus(cont) for cont in obj.get("containerStatuses", [])
        ]
