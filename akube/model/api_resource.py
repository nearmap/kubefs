from typing import Any, Dict

ApiObj = Dict[str, Any]


class ApiResource:
    """Represents a REST resource available on the kube API server."""

    def __init__(self, *, endpoint: str, obj: ApiObj) -> None:
        self.endpoint = endpoint
        self.obj = obj

    @property
    def kind(self) -> str:
        return self.obj["kind"]

    @property
    def name(self) -> str:
        return self.obj["name"]

    @property
    def namespaced(self) -> bool:
        return self.obj["namespaced"]
