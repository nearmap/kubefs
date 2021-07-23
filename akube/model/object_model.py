from datetime import datetime
from typing import Any, Dict

from dateutil.parser import parse as parse_date

RawObject = Dict[str, Any]


class _ObjectMeta:
    def __init__(self, obj: RawObject) -> None:
        self._meta = obj["metadata"]

        self.creationTimestamp: datetime = parse_date(self._meta["creationTimestamp"])
        self.name: str = self._meta["name"]
        self.resourceVersion: int = int(self._meta["resourceVersion"])
        self.uid: str = self._meta["uid"]


class _NamespacedMeta(_ObjectMeta):
    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)

        self.namespace: str = self._meta["namespace"]
        self.labels: Dict[str, str] = self._meta["labels"]
        self.annotations: Dict[str, str] = self._meta["annotations"]


class _KubeObjectWrapper:
    _meta_cls = _ObjectMeta

    def __init__(self, obj: RawObject) -> None:
        self.apiVersion = obj["apiVersion"]
        self.kind = obj["kind"]
        self.meta = self._meta_cls(obj)

        # make sure we are wrapping what we think we're wrapping
        assert self.kind == self.__class__.__name__


class Namespace(_KubeObjectWrapper):
    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)


class Pod(_KubeObjectWrapper):
    _meta_cls = _NamespacedMeta

    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)
