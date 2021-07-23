from akube.model.object_model.base import ObjectWrapper
from akube.model.object_model.meta import NamespacedMeta, ObjectMeta
from akube.model.object_model.status import ObjectStatus, PodStatus
from akube.model.object_model.types import RawObject


class Namespace(ObjectWrapper):
    _meta_cls = ObjectMeta
    _status_cls = ObjectStatus

    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)


class Pod(ObjectWrapper):
    _meta_cls = NamespacedMeta
    _status_cls = PodStatus

    def __init__(self, obj: RawObject) -> None:
        super().__init__(obj)

        # help mypy a bit here
        self.meta: NamespacedMeta
        self.status: PodStatus
