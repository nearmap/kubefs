class ApiGroup:
    def __init__(self, *, name: str, endpoint: str) -> None:
        self.name = name
        # preferredVersion.groupVersion
        self.endpoint = endpoint


CoreV1 = ApiGroup(name="core", endpoint="/api/v1")
