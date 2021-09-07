class ApiGroup:
    """
    The kube object:

    {
      "name": "apiregistration.k8s.io",
      "versions": [
        {
          "groupVersion": "apiregistration.k8s.io/v1",
          "version": "v1"
        },
        {
          "groupVersion": "apiregistration.k8s.io/v1beta1",
          "version": "v1beta1"
        }
      ],
      "preferredVersion": {
        "groupVersion": "apiregistration.k8s.io/v1",
        "version": "v1"
      }
    }

    We treat each version as an ApiGroup, where `groupVersion` becomes `endpoint`.
    """

    def __init__(self, *, name: str, endpoint: str) -> None:
        self.name = name
        self.endpoint = endpoint

    def __repr__(self) -> str:
        return "<%s name=%r, endpoint=%r>" % (
            self.__class__.__name__,
            self.name,
            self.endpoint,
        )


CoreV1 = ApiGroup(name="core", endpoint="/api/v1")
