import dateutil

from akube.async_loop import get_loop
from akube.cluster_facade import SyncClusterFacade
from akube.model.api_resource import NamespaceKind
from akube.model.selector import ObjectSelector
from kube.config import Context
from kubefs.fs_model import Directory, File, Payload
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


def mkpayload2(*, obj):
    block = to_json(obj)

    timestamp = dateutil.parser.parse(obj["metadata"]["creationTimestamp"]).timestamp()

    payload = Payload(
        name=obj["metadata"]["name"],
        data=block.encode(),
        ctime=timestamp,
        mtime=timestamp,
    )

    return payload


class KubeClusterConfigMapsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context)
        self.namespace = namespace
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            configmaps = self.client.get_configmaps(namespace=self.namespace)
            for configmap in configmaps:
                payload = mkpayload(api_version="v1", kind="ConfigMap", obj=configmap)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterDaemonSetsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            daemonsets = self.client.get_daemonsets(namespace=self.namespace)
            for daemonset in daemonsets:
                payload = mkpayload(
                    api_version="apps/v1", kind="DaemonSet", obj=daemonset
                )
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterDeploymentsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            deployments = self.client.get_deployments(namespace=self.namespace)
            for deployment in deployments:
                payload = mkpayload(
                    api_version="apps/v1", kind="Deployment", obj=deployment
                )
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterEndpointsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            endpoints = self.client.get_endpoints(namespace=self.namespace)
            for endpoint in endpoints:
                payload = mkpayload(api_version="v1", kind="Endpoints", obj=endpoint)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterNodesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            nodes = self.client.get_nodes()
            for node in nodes:
                payload = mkpayload(api_version="v1", kind="Node", obj=node)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterNamespaceDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.context = context
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):

        if not self.lazy_entries:
            dirs = []

            types = {
                "configmaps": KubeClusterConfigMapsDir,
                "daemonsets": KubeClusterDaemonSetsDir,
                "deployments": KubeClusterDeploymentsDir,
                "endpoints": KubeClusterEndpointsDir,
                "pods": KubeClusterPodsDir,
                "replicasets": KubeClusterReplicaSetsDir,
                "secrets": KubeClusterSecretsDir,
                "services": KubeClusterServicesDir,
            }

            for name, cls in types.items():
                payload = Payload(name=name)
                dir = cls.create(
                    payload=payload, context=self.context, namespace=self.namespace
                )
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeClusterNamespacesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.context = context
        self.facade = SyncClusterFacade(async_loop=get_loop(), context=self.context)
        self.selector = ObjectSelector(res=NamespaceKind)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            items = self.facade.list_objects(selector=self.selector)

            files = []
            for item in items:
                payload = mkpayload2(obj=item)
                files.append(File(payload=payload))

            self.lazy_entries = files

            # files = []

            # namespaces = self.client.get_namespaces()
            # for namespace in namespaces:
            #     name = namespace.metadata.name
            #     payload = Payload(name=name)
            #     files.append(
            #         KubeClusterNamespaceDir.create(
            #             payload=payload, context=self.context, namespace=name
            #         )
            #     )

            # self.lazy_entries = files

        return self.lazy_entries


class KubeClusterPodsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.client = KubeClientCache.get_client(context=context)
        self.namespace = namespace
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            pods = self.client.get_pods(namespace=self.namespace)
            for pod in pods:
                payload = mkpayload(api_version="v1", kind="Pod", obj=pod)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterReplicaSetsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            replicasets = self.client.get_replicasets(namespace=self.namespace)
            for replicaset in replicasets:
                payload = mkpayload(
                    api_version="apps/v1", kind="ReplicaSet", obj=replicaset
                )
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterSecretsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            secrets = self.client.get_secrets(namespace=self.namespace)
            for secret in secrets:
                payload = mkpayload(api_version="v1", kind="Secret", obj=secret)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterServicesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str = None):
        self = cls(payload=payload)
        self.namespace = namespace
        self.client = KubeClientCache.get_client(context=context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            services = self.client.get_services(namespace=self.namespace)
            for service in services:
                payload = mkpayload(api_version="v1", kind="Service", obj=service)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries
