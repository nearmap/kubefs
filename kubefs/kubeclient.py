from kubernetes import client, config


class KubeClient:
    def __init__(self, context: str):
        self.context = context
        self._corev1_client = None  # lazy
        self._appsv1_client = None  # lazy

    @property
    def corev1_client(self):
        if not self._corev1_client:
            config.load_kube_config(context=self.context)
            self._corev1_client = client.CoreV1Api()

        return self._corev1_client

    @property
    def appsv1_client(self):
        if not self._appsv1_client:
            config.load_kube_config(context=self.context)
            self._appsv1_client = client.AppsV1Api()

        return self._appsv1_client

    def get_configmaps(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_config_map(namespace)
        else:
            result = self.corev1_client.list_config_map_for_all_namespaces()
        return result.items

    def get_deployments(self, *, namespace: str = None):
        if namespace:
            result = self.appsv1_client.list_namespaced_deployment(namespace)
        else:
            result = self.appsv1_client.list_deployment_for_all_namespaces()
        return result.items

    def get_endpoints(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_endpoints(namespace)
        else:
            result = self.corev1_client.list_endpoints_for_all_namespaces()
        return result.items

    def get_namespaces(self):
        result = self.corev1_client.list_namespace()
        return result.items

    def get_nodes(self):
        result = self.corev1_client.list_node()
        return result.items

    def get_pods(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_pod(namespace)
        else:
            result = self.corev1_client.list_pod_for_all_namespaces()
        return result.items

    def get_replicasets(self, *, namespace: str = None):
        if namespace:
            result = self.appsv1_client.list_namespaced_replica_set(namespace)
        else:
            result = self.appsv1_client.list_replica_set_for_all_namespaces()
        return result.items

    def get_secrets(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_secret(namespace)
        else:
            result = self.corev1_client.list_secret_for_all_namespaces()
        return result.items

    def get_services(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_service(namespace)
        else:
            result = self.corev1_client.list_service_for_all_namespaces()
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
