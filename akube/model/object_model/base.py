from typing import Any, Dict, Optional

from akube.model.object_model.meta import ObjectMeta
from akube.model.object_model.status import ObjectStatus
from akube.model.object_model.types import RawObject


class ObjectWrapper:
    _meta_cls = ObjectMeta
    _status_cls = None

    def __init__(self, obj: RawObject) -> None:
        self.apiVersion: str = obj["apiVersion"]
        self.kind: str = obj["kind"]

        # make sure we are wrapping what we think we're wrapping
        assert self.kind == self.__class__.__name__

        self.meta: ObjectMeta = self._meta_cls(obj)
        self.status: Optional[ObjectStatus] = (
            self._status_cls(obj) if self._status_cls else None
        )
