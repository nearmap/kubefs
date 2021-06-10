from kubernetes import client, config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.configuration import Configuration

from kubefs.kubeconfig import Context


class KubeClient:
    def __init__(self, context: Context):
        self.context = context
        self._corev1_client = None  # lazy
        self._appsv1_client = None  # lazy

        self.std_kwargs = dict(
            # connect: 2s, read: 15s
            _request_timeout=(2, 15),
        )

    def create_api_client(self) -> ApiClient:
        # disable retries because we would rather have a more responsive fs than
        # make the user wait while we retry in the background
        configuration = Configuration.get_default_copy()
        configuration.retries = 0

        api_client = ApiClient(configuration=configuration)
        return api_client

    @property
    def corev1_client(self):
        if not self._corev1_client:
            config.load_kube_config(
                config_file=self.context.filepath, context=self.context.name
            )
            api_client = self.create_api_client()
            self._corev1_client = client.CoreV1Api(api_client=api_client)

        return self._corev1_client

    @property
    def appsv1_client(self):
        if not self._appsv1_client:
            config.load_kube_config(
                config_file=self.context.filepath, context=self.context.name
            )
            api_client = self.create_api_client()
            self._appsv1_client = client.AppsV1Api(api_client=api_client)

        return self._appsv1_client

    def get_configmaps(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_config_map(
                namespace, **self.std_kwargs
            )
        else:
            result = self.corev1_client.list_config_map_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items

    def get_daemonsets(self, *, namespace: str = None):
        if namespace:
            result = self.appsv1_client.list_namespaced_daemon_set(
                namespace, **self.std_kwargs
            )
        else:
            result = self.appsv1_client.list_daemon_set_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items

    def get_deployments(self, *, namespace: str = None):
        if namespace:
            result = self.appsv1_client.list_namespaced_deployment(
                namespace, **self.std_kwargs
            )
        else:
            result = self.appsv1_client.list_deployment_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items

    def get_endpoints(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_endpoints(
                namespace, **self.std_kwargs
            )
        else:
            result = self.corev1_client.list_endpoints_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items

    def get_namespaces(self):
        result = self.corev1_client.list_namespace(**self.std_kwargs)
        return result.items

    def get_nodes(self):
        result = self.corev1_client.list_node(**self.std_kwargs)
        return result.items

    def get_pods(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_pod(
                namespace, **self.std_kwargs
            )
        else:
            result = self.corev1_client.list_pod_for_all_namespaces(**self.std_kwargs)
        return result.items

    def get_replicasets(self, *, namespace: str = None):
        if namespace:
            result = self.appsv1_client.list_namespaced_replica_set(
                namespace, **self.std_kwargs
            )
        else:
            result = self.appsv1_client.list_replica_set_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items

    def get_secrets(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_secret(
                namespace, **self.std_kwargs
            )
        else:
            result = self.corev1_client.list_secret_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items

    def get_services(self, *, namespace: str = None):
        if namespace:
            result = self.corev1_client.list_namespaced_service(
                namespace, **self.std_kwargs
            )
        else:
            result = self.corev1_client.list_service_for_all_namespaces(
                **self.std_kwargs
            )
        return result.items


class KubeClientCache:
    # context -> client
    client_cache = {}

    @classmethod
    def get_client(cls, context: Context) -> KubeClient:
        client = cls.client_cache.get(context.name)

        if not client:
            cls.client_cache[context.name] = KubeClient(context)

        return cls.client_cache[context.name]
