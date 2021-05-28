from kubefs.fs_model import Directory, File
from kubefs.kubeconfig import Cluster
from kubefs.kubeclient import KubeClientCache
from kubefs.text import to_json


class KubeClusterPodsDir(Directory):
    @classmethod
    def create(cls, *, name: str, cluster: Cluster):
        self = cls(name=name)
        self.cluster = cluster
        self.client = KubeClientCache.get_client(context=cluster.get_context().name)
        return self

    def get_entries(self):
        if not self._lazy_entries:
            files = []

            pods = self.client.list_pods_from_all_namespaces()
            for pod in pods:
                block = to_json(pod.to_dict())
                files.append(File(name=pod.metadata.name, contents=block.encode()))

            self._lazy_entries = files

        return self._lazy_entries
