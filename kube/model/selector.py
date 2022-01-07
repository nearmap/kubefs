from typing import Optional

from kube.model.api_resource import ApiResource
from kube.model.client_params import ClientOperationParams


class ObjectSelector:
    def __init__(
        self,
        *,
        res: ApiResource,
        namespace: Optional[str] = None,
        podname: Optional[str] = None,
        contname: Optional[str] = None,
        client_op_params: Optional[ClientOperationParams] = None,
    ) -> None:
        if namespace and not res.namespaced:
            raise ValueError("Cannot search by namespace for %s" % res.kind)

        self.res = res
        self.namespace = namespace
        self.podname = podname
        self.contname = contname

        self.client_op_params = client_op_params

    def __repr__(self) -> str:
        return "<%s res=%r, namespace=%r>" % (
            self.__class__.__name__,
            self.res,
            self.namespace,
        )

    def pretty(self):
        slug = ""

        if self.namespace is not None:
            slug = f"{self.namespace}/{slug}"

        slug = f"{slug}{self.res.kind}"

        return slug
