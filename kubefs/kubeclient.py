from kubernetes import client, config


class KubeClient:
    def __init__(self, context: str):
        self.context = context
        self._client = None  # lazy

    @property
    def client(self):
        if not self._client:
            config.load_kube_config(context=self.context)
            self._client = client.CoreV1Api()

        return self._client

    def list_pods_from_all_namespaces(self):
        result = self.client.list_pod_for_all_namespaces(watch=False)
        return result.items


class KubeClientCache:
    # context -> client
    client_cache = {}

    @classmethod
    def get_client(cls, context: str) -> KubeClient:
        client = cls.client_cache.get(context)

        if not client:
            cls.client_cache[context] = KubeClient(context)

        return cls.client_cache[context]
