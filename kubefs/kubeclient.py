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

    def list_configmaps_from_all_namespaces(self):
        result = self.corev1_client.list_config_map_for_all_namespaces()
        return result.items

    def list_deployments_from_all_namespaces(self):
        result = self.appsv1_client.list_deployment_for_all_namespaces()
        return result.items

    def list_endpoints_from_all_namespaces(self):
        result = self.corev1_client.list_endpoints_for_all_namespaces()
        return result.items

    def list_namespaces(self):
        result = self.corev1_client.list_namespace()
        return result.items

    def list_nodes(self):
        result = self.corev1_client.list_node()
        return result.items

    def list_pods_from_all_namespaces(self):
        result = self.corev1_client.list_pod_for_all_namespaces()
        return result.items

    def list_replicasets_from_all_namespaces(self):
        result = self.appsv1_client.list_replica_set_for_all_namespaces()
        return result.items

    def list_secrets_from_all_namespaces(self):
        result = self.corev1_client.list_secret_for_all_namespaces()
        return result.items

    def list_services_from_all_namespaces(self):
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
