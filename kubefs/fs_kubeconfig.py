from kubefs.fs_kubecluster import (
    KubeClusterConfigMapsDir,
    KubeClusterDaemonSetsDir,
    KubeClusterDeploymentsDir,
    KubeClusterEndpointsDir,
    KubeClusterNamespacesDir,
    KubeClusterNodesDir,
    KubeClusterPodsDir,
    KubeClusterReplicaSetsDir,
    KubeClusterSecretsDir,
    KubeClusterServicesDir,
)
from kubefs.fs_model import Directory, File, Payload
from kubefs.kubeconfig import Cluster, Context, KubeConfigLoader, User


class KubeConfigClusterDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, cluster: Cluster):
        self = cls(payload=payload)
        self.cluster = cluster
        return self

    def get_entries(self):
        if not self.lazy_entries:
            dirs = []

            types = {
                "configmaps": KubeClusterConfigMapsDir,
                "daemonsets": KubeClusterDaemonSetsDir,
                "deployments": KubeClusterDeploymentsDir,
                "endpoints": KubeClusterEndpointsDir,
                "namespaces": KubeClusterNamespacesDir,
                "nodes": KubeClusterNodesDir,
                "pods": KubeClusterPodsDir,
                "replicasets": KubeClusterReplicaSetsDir,
                "secrets": KubeClusterSecretsDir,
                "services": KubeClusterServicesDir,
            }

            for name, cls in types.items():
                payload = Payload(name=name)
                dir = cls.create(payload=payload, context=self.cluster.get_context())
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeConfigClustersDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, loader: KubeConfigLoader):
        self = cls(payload=payload)
        self.loader = loader
        return self

    def get_entries(self):
        if not self.lazy_entries:
            clusters = self.loader.get_all_clusters()

            dirs = []
            for cluster in clusters:
                payload = Payload(
                    name=cluster.name,
                    ctime=cluster.ctime,
                    mtime=cluster.mtime,
                    atime=cluster.atime,
                )
                dir = KubeConfigClusterDir.create(payload=payload, cluster=cluster)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeConfigContextDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.context = context
        return self

    def get_entries(self):
        if not self.lazy_entries:
            dirs = []

            cluster = self.context.get_cluster()
            if cluster:
                payload = Payload(name="cluster")
                dir = KubeConfigClusterDir.create(payload=payload, cluster=cluster)
                dirs.append(dir)

            user = self.context.get_user()
            if user:
                payload = Payload(name="user")
                dir = KubeConfigUserDir.create(payload=payload, user=user)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeConfigContextsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, loader: KubeConfigLoader):
        self = cls(payload=payload)
        self.loader = loader
        return self

    def get_entries(self):
        if not self.lazy_entries:
            contexts = self.loader.get_all_contexts()

            dirs = []
            for context in contexts:
                payload = Payload(
                    name=context.name,
                    ctime=context.ctime,
                    mtime=context.mtime,
                    atime=context.atime,
                )
                dir = KubeConfigContextDir.create(payload=payload, context=context)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeConfigUserDir(Directory):
    """Represents a directory that contains files that belong to a single user.
    The files and their contents are the key/values of the user object in the
    kube config."""

    @classmethod
    def create(cls, *, payload: Payload, user: User):
        self = cls(payload=payload)
        self.user = user
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            for attname in self.user.get_attribute_names():
                value = self.user.get_attribute(attname)
                if value is not None:
                    payload = Payload(
                        name=attname,
                        data=value.encode(),
                        ctime=self.user.ctime,
                        mtime=self.user.mtime,
                        atime=self.user.atime,
                    )
                    file = File(payload=payload)
                    files.append(file)

            self.lazy_entries = files

        return self.lazy_entries


class KubeConfigUsersDir(Directory):
    """Represents a directory containing all the user names defined in the kube
    config. Each entry is itself a directory containing files."""

    @classmethod
    def create(cls, *, payload: Payload, loader: KubeConfigLoader):
        self = cls(payload=payload)
        self.loader = loader
        return self

    def get_entries(self):
        if not self.lazy_entries:
            users = self.loader.get_all_users()

            dirs = []
            for user in users:
                payload = Payload(
                    name=user.name,
                    ctime=user.ctime,
                    mtime=user.mtime,
                    atime=user.atime,
                )
                dir = KubeConfigUserDir.create(payload=payload, user=user)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries
