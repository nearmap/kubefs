from typing import Optional

from akube.model.api_resource import ApiResource


class ObjectSelector:
    def __init__(self, *, res: ApiResource, namespace: Optional[str] = None) -> None:
        if namespace and not res.namespaced:
            raise ValueError("Cannot search by namespace for %s" % res.kind)

        self.res = res
        self.namespace = namespace
