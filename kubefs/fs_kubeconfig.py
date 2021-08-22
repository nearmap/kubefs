from kube.config import Context, KubeConfigCollection
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


class KubeConfigClusterDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.context = context
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
                dir = cls.create(payload=payload, context=self.context)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeConfigClustersDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, config: KubeConfigCollection):
        self = cls(payload=payload)
        self.config = config
        return self

    def get_entries(self):
        if not self.lazy_entries:
            dirs = []
            for context in self.config.contexts.values():
                payload = Payload(
                    name=context.cluster.short_name,
                    ctime=context.file.ctime,
                    mtime=context.file.mtime,
                    atime=context.file.atime,
                )
                dir = KubeConfigClusterDir.create(payload=payload, context=context)
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

            cluster = self.context.cluster
            if cluster:
                payload = Payload(name="cluster")
                dir = KubeConfigClusterDir.create(payload=payload, context=self.context)
                dirs.append(dir)

            user = self.context.user
            if user:
                payload = Payload(name="user")
                dir = KubeConfigUserDir.create(payload=payload, context=self.context)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries


class KubeConfigContextsDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, config: KubeConfigCollection):
        self = cls(payload=payload)
        self.config = config
        return self

    def get_entries(self):
        if not self.lazy_entries:
            dirs = []
            for context in self.config.contexts.values():
                payload = Payload(
                    name=context.short_name,
                    ctime=context.file.ctime,
                    mtime=context.file.mtime,
                    atime=context.file.atime,
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
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.context = context
        return self

    def get_entries(self):
        if not self.lazy_entries:
            files = []

            for attname in self.context.user.get_attribute_names():
                value = getattr(self.context.user, attname)
                assert type(value) is str  # we need to call .encode on this

                payload = Payload(
                    name=attname,
                    data=value.encode(),
                    ctime=self.context.file.ctime,
                    mtime=self.context.file.mtime,
                    atime=self.context.file.atime,
                )
                file = File(payload=payload)
                files.append(file)

            self.lazy_entries = files

        return self.lazy_entries


class KubeConfigUsersDir(Directory):
    """Represents a directory containing all the user names defined in the kube
    config. Each entry is itself a directory containing files."""

    @classmethod
    def create(cls, *, payload: Payload, config: KubeConfigCollection):
        self = cls(payload=payload)
        self.config = config
        return self

    def get_entries(self):
        if not self.lazy_entries:
            dirs = []
            for context in self.config.contexts.values():
                payload = Payload(
                    name=context.user.short_name,
                    ctime=context.file.ctime,
                    mtime=context.file.mtime,
                    atime=context.file.atime,
                )
                dir = KubeConfigUserDir.create(payload=payload, context=context)
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries
