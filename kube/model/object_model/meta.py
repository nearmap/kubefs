from datetime import datetime
from typing import Dict, Optional

from dateutil.parser import parse as parse_date

from kube.model.object_model.helpers import maybe_parse_date
from kube.model.object_model.types import RawObject


class ObjectMeta:
    def __init__(self, obj: RawObject) -> None:
        self._meta = obj["metadata"]

        self.creationTimestamp: datetime = parse_date(self._meta["creationTimestamp"])
        self.deletionTimestamp: Optional[datetime] = maybe_parse_date(
            self._meta.get("deletionTimestamp")
        )
        self.name: str = self._meta["name"]
        self.resourceVersion: int = int(self._meta["resourceVersion"])
        self.uid: str = self._meta["uid"]


class NamespacedMeta(ObjectMeta):
    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)

        self.namespace: str = self._meta["namespace"]
        self.labels: Dict[str, str] = self._meta.get("labels") or {}
        self.annotations: Dict[str, str] = self._meta.get("annotations") or {}
