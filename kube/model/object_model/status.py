from datetime import datetime
from typing import List, Optional

from kube.model.object_model.helpers import maybe_parse_date
from kube.model.object_model.types import RawObject


class ContainerState:
    def __init__(self, obj: RawObject) -> None:
        self._obj = obj
        self.key: str


class ContainerStateRunning(ContainerState):
    def __init__(self, obj: RawObject) -> None:
        self.key = "running"
        self.startedAt: Optional[datetime] = maybe_parse_date(obj.get("startedAt"))


class ContainerStateTerminated(ContainerState):
    def __init__(self, obj: RawObject) -> None:
        self.key = "terminated"
        self.startedAt: Optional[datetime] = maybe_parse_date(obj.get("startedAt"))
        self.finishedAt: Optional[datetime] = maybe_parse_date(obj.get("finishedAt"))
        self.exitCode: Optional[int] = obj.get("exitCode")
        self.message: Optional[str] = obj.get("message")
        self.reason: Optional[str] = obj.get("reason")


class ContainerStateWaiting(ContainerState):
    def __init__(self, obj: RawObject) -> None:
        self.key = "waiting"
        self.message: Optional[str] = obj.get("message")
        self.reason: Optional[str] = obj.get("reason")


def parse_container_state(obj: RawObject) -> Optional[ContainerState]:
    key = list(obj.keys())[0]

    if key == "running":
        return ContainerStateRunning(obj[key])
    elif key == "terminated":
        return ContainerStateTerminated(obj[key])
    elif key == "waiting":
        return ContainerStateWaiting(obj[key])

    return None


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
            self.state = parse_container_state(state)

        lastState = obj.get("lastState")
        if lastState:
            self.lastState = parse_container_state(lastState)


class ObjectStatus:
    def __init__(self, obj: RawObject) -> None:
        self._status = obj["status"]

        self.phase: Optional[str] = self._status["phase"]


class PodStatus(ObjectStatus):
    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)

        self.startTime: Optional[datetime] = None
        self.reason: Optional[str] = None
        self.message: Optional[str] = None
        self.containerStatuses: List[ContainerStatus] = []

        self.startTime = maybe_parse_date(self._status.get("startTime"))
        self.message = self._status.get("message")
        self.reason = self._status.get("reason")
        self.containerStatuses = [
            ContainerStatus(cont) for cont in self._status.get("containerStatuses", [])
        ]
