from kubefs.fs_model import Directory, File, Payload
from kubefs.kubeconfig import Context
from kubefs.kubeclient import KubeClientCache
from kubefs.text import to_dict, to_json


def mkpayload(*, api_version, kind, obj):
    # set these on the object because they may not be set when the kube REST api
    # returns collections of objects
    obj.api_version = api_version
    obj.kind = kind

    block = to_json(to_dict(obj))

    timestamp = obj.metadata.creation_timestamp.timestamp()

    payload = Payload(
        name=obj.metadata.name,
        data=block.encode(),
        ctime=timestamp,
        mtime=timestamp,
    )

    return payload


class KubeClusterConfigMapsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            configmaps = self.client.list_configmaps_from_all_namespaces()
            for configmap in configmaps:
                payload = mkpayload(api_version="v1", kind="ConfigMap", obj=configmap)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterDeploymentsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            deployments = self.client.list_deployments_from_all_namespaces()
            for deployment in deployments:
                payload = mkpayload(
                    api_version="apps/v1", kind="Deployment", obj=deployment
                )
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterEndpointsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            endpoints = self.client.list_endpoints_from_all_namespaces()
            for endpoint in endpoints:
                payload = mkpayload(api_version="v1", kind="Endpoints", obj=endpoint)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterNodesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            nodes = self.client.list_nodes()
            for node in nodes:
                payload = mkpayload(api_version="v1", kind="Node", obj=node)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterNamespacesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            namespaces = self.client.list_namespaces()
            for namespace in namespaces:
                payload = mkpayload(api_version="v1", kind="Namespace", obj=namespace)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterPodsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            pods = self.client.list_pods_from_all_namespaces()
            for pod in pods:
                payload = mkpayload(api_version="v1", kind="Pod", obj=pod)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterReplicaSetsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            replicasets = self.client.list_replicasets_from_all_namespaces()
            for replicaset in replicasets:
                payload = mkpayload(
                    api_version="apps/v1", kind="ReplicaSet", obj=replicaset
                )
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterSecretsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            secrets = self.client.list_secrets_from_all_namespaces()
            for secret in secrets:
                payload = mkpayload(api_version="v1", kind="Secret", obj=secret)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries


class KubeClusterServicesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context.name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            services = self.client.list_services_from_all_namespaces()
            for service in services:
                payload = mkpayload(api_version="v1", kind="Service", obj=service)
                files.append(File(payload=payload))

            self._lazy_entries = files

        return self._lazy_entries
