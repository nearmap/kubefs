class ApiResource:
    """Represents a REST resource available on the kube API server."""

    def __init__(
        self, *, endpoint: str, kind: str, name: str, namespaced: bool
    ) -> None:
        self.endpoint = endpoint
        self.kind = kind
        self.name = name
        self.namespaced = namespaced


Pod = ApiResource(endpoint="/api/v1", kind="Pod", name="pods", namespaced=True)
Namespace = ApiResource(
    endpoint="/api/v1", kind="Namespace", name="namespaces", namespaced=False
)
