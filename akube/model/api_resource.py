class ApiResource:
    """Represents a REST resource available on the kube API server."""

    def __init__(
        self, *, endpoint: str, kind: str, name: str, namespaced: bool
    ) -> None:
        self.endpoint = endpoint
        self.kind = kind
        self.name = name
        self.namespaced = namespaced

    def __repr__(self) -> str:
        return "<%s kind=%r, name=%r, namespaced=%r, endpoint=%r>" % (
            self.__class__.__name__,
            self.kind,
            self.name,
            self.namespaced,
            self.endpoint,
        )


PodKind = ApiResource(endpoint="/api/v1", kind="Pod", name="pods", namespaced=True)
NamespaceKind = ApiResource(
    endpoint="/api/v1", kind="Namespace", name="namespaces", namespaced=False
)
