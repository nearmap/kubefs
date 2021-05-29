from kubefs.fs_model import Directory, File
from kubefs.kubeconfig import Context
from kubefs.kubeclient import KubeClientCache
from kubefs.text import serialize_kube_obj


class KubeClusterConfigMapsDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            configmaps = self.client.list_configmaps_from_all_namespaces()
            for configmap in configmaps:
                block = serialize_kube_obj(
                    api_version="v1", kind="ConfigMap", obj=configmap
                )
                files.append(
                    File(name=configmap.metadata.name, contents=block.encode())
                )

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterDeploymentsDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            deployments = self.client.list_deployments_from_all_namespaces()
            for deployment in deployments:
                block = serialize_kube_obj(
                    api_version="apps/v1", kind="Deployment", obj=deployment
                )
                files.append(
                    File(name=deployment.metadata.name, contents=block.encode())
                )

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterEndpointsDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            endpoints = self.client.list_endpoints_from_all_namespaces()
            for endpoint in endpoints:
                block = serialize_kube_obj(
                    api_version="v1", kind="Endpoints", obj=endpoint
                )
                files.append(File(name=endpoint.metadata.name, contents=block.encode()))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterNodesDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            nodes = self.client.list_nodes()
            for node in nodes:
                block = serialize_kube_obj(api_version="v1", kind="Node", obj=node)
                files.append(File(name=node.metadata.name, contents=block.encode()))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterNamespacesDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            namespaces = self.client.list_namespaces()
            for namespace in namespaces:
                block = serialize_kube_obj(
                    api_version="v1", kind="Namespace", obj=namespace
                )
                files.append(
                    File(name=namespace.metadata.name, contents=block.encode())
                )

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterPodsDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            pods = self.client.list_pods_from_all_namespaces()
            for pod in pods:
                block = serialize_kube_obj(api_version="v1", kind="Pod", obj=pod)
                files.append(File(name=pod.metadata.name, contents=block.encode()))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterReplicaSetsDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            replicasets = self.client.list_replicasets_from_all_namespaces()
            for replicaset in replicasets:
                block = serialize_kube_obj(
                    api_version="apps/v1", kind="ReplicaSet", obj=replicaset
                )
                files.append(
                    File(name=replicaset.metadata.name, contents=block.encode())
                )

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterSecretsDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            secrets = self.client.list_secrets_from_all_namespaces()
            for secret in secrets:
                block = serialize_kube_obj(api_version="v1", kind="Secret", obj=secret)
                files.append(File(name=secret.metadata.name, contents=block.encode()))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterServicesDir(Directory):
    @classmethod
    def create(cls, *, name: str, context: Context):
        self = cls(name=name)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            services = self.client.list_services_from_all_namespaces()
            for service in services:
                block = serialize_kube_obj(
                    api_version="v1", kind="Service", obj=service
                )
                files.append(File(name=service.metadata.name, contents=block.encode()))

            self._lazy_entries = files

        return self._lazy_entries
