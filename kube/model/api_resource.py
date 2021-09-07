from typing import List

from kube.model.api_group import ApiGroup, CoreV1


class ApiResource:
    """Represents a REST resource available on the kube API server."""

    def __init__(
        self,
        *,
        group: ApiGroup,
        kind: str,
        name: str,
        namespaced: bool,
        verbs: List[str],
    ) -> None:
        self.group = group
        self.kind = kind
        self.name = name
        self.namespaced = namespaced
        self.verbs = verbs

        self.qualified_name = f"{self.name}.{self.group.name}"

    def __repr__(self) -> str:
        return "<%s group=%r, kind=%r, name=%r, namespaced=%r, verbs=%r>" % (
            self.__class__.__name__,
            self.group,
            self.kind,
            self.name,
            self.namespaced,
            self.verbs,
        )


PodKind = ApiResource(
    group=CoreV1,
    kind="Pod",
    name="pods",
    namespaced=True,
    verbs=[
        "create",
        "delete",
        "deletecollection",
        "get",
        "list",
        "patch",
        "update",
        "watch",
    ],
)
NamespaceKind = ApiResource(
    group=CoreV1,
    kind="Namespace",
    name="namespaces",
    namespaced=False,
    verbs=["create", "delete", "get", "list", "patch", "update", "watch"],
)
