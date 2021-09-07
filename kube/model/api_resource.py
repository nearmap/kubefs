from kube.model.api_group import ApiGroup, CoreV1


class ApiResource:
    """Represents a REST resource available on the kube API server."""

    def __init__(
        self, *, group: ApiGroup, kind: str, name: str, namespaced: bool
    ) -> None:
        self.group = group
        self.kind = kind
        self.name = name
        self.namespaced = namespaced

        self.qualified_name = f"{self.name}.{self.group.name}"

    def __repr__(self) -> str:
        return "<%s kind=%r, name=%r, namespaced=%r, endpoint=%r>" % (
            self.__class__.__name__,
            self.kind,
            self.name,
            self.namespaced,
            self.group.endpoint,
        )


PodKind = ApiResource(group=CoreV1, kind="Pod", name="pods", namespaced=True)
NamespaceKind = ApiResource(
    group=CoreV1, kind="Namespace", name="namespaces", namespaced=False
)
