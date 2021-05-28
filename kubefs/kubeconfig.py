from typing import Iterator
import os
import logging
import yaml


class Cluster:
    def __init__(self, cluster_dct) -> None:
        self.cluster_dct = cluster_dct

    @property
    def name(self):
        return self.cluster_dct.get("name")


class Context:
    def __init__(self, context_dct, loader) -> None:
        self.context_dct = context_dct
        self.loader = loader

    @property
    def name(self):
        return self.context_dct.get("name")

    def get_cluster(self):
        cluster_name = self.context_dct["context"].get("cluster")
        if cluster_name:
            return self.loader.get_cluster(cluster_name)

    def get_user(self):
        user_name = self.context_dct["context"].get("user")
        if user_name:
            return self.loader.get_user(user_name)


class User:
    def __init__(self, user_dct) -> None:
        self.user_dct = user_dct

    @property
    def name(self):
        return self.user_dct.get("name")

    def get_attribute_names(self):
        return list(self.user_dct["user"].keys())

    def get_attribute(self, name):
        return self.user_dct["user"].get(name)


class KubeConfigLoader:
    _instance = None
    logger = logging.getLogger("kube-config-loader")

    def __init__(self, kubecfg_loc="~/.kube") -> None:
        self.kubecfg_loc = os.path.expanduser(kubecfg_loc)

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()

        return cls._instance

    def get_all_documents(self) -> Iterator[User]:
        path = self.kubecfg_loc
        files = os.listdir(path)

        for file in files:
            fp = os.path.join(path, file)

            if not os.path.isfile(fp):
                continue

            with open(fp, "rb") as fl:
                try:
                    doc = yaml.load(fl, Loader=yaml.SafeLoader)
                except Exception as exc:
                    self.logger.debug("Failed to parse kube config: %s", fp)
                    continue

            kind = doc.get("kind")
            if not kind:
                self.logger.debug(
                    "Candidate kube config does not have kind: Config: %s", fp
                )
                continue

            yield doc

    def get_all_clusters(self) -> Iterator[Cluster]:
        for doc in self.get_all_documents():
            for cluster_dct in doc.get("clusters"):
                yield Cluster(cluster_dct)

    def get_all_contexts(self) -> Iterator[Context]:
        for doc in self.get_all_documents():
            for context_dct in doc.get("contexts"):
                yield Context(context_dct, self)

    def get_all_users(self) -> Iterator[User]:
        for doc in self.get_all_documents():
            for user_dct in doc.get("users"):
                yield User(user_dct)

    def get_cluster(self, cluster_name):
        for cluster in self.get_all_clusters():
            if cluster.name == cluster_name:
                return cluster

    def get_user(self, user_name):
        for user in self.get_all_users():
            if user.name == user_name:
                return user
