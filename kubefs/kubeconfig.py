from typing import Iterable, Dict, Any
import os
import logging
import yaml


class YamlDoc:
    def __init__(
        self,
        *,
        filepath: str,
        doc: Dict[Any, Any],
        ctime: float = None,
        mtime: float = None,
        atime: float = None,
    ) -> None:
        self.filepath = filepath
        self.doc = doc
        self.ctime = ctime
        self.mtime = mtime
        self.atime = atime


class Context:
    def __init__(self, yaml_doc: YamlDoc, context_dct, loader) -> None:
        self.yaml_doc = yaml_doc
        self.context_dct = context_dct
        self.loader = loader

    @property
    def filepath(self):
        return self.yaml_doc.filepath

    @property
    def name(self):
        return self.context_dct.get("name")

    @property
    def ctime(self):
        return self.yaml_doc.ctime

    @property
    def mtime(self):
        return self.yaml_doc.mtime

    @property
    def atime(self):
        return self.yaml_doc.atime

    @property
    def cluster_name(self):
        return self.context_dct["context"].get("cluster")

    def get_cluster(self):
        cluster_name = self.context_dct["context"].get("cluster")
        if cluster_name:
            return self.loader.get_cluster(cluster_name)

    def get_user(self):
        user_name = self.context_dct["context"].get("user")
        if user_name:
            return self.loader.get_user(user_name)


class Cluster:
    def __init__(self, yaml_doc, cluster_dct, loader) -> None:
        self.yaml_doc = yaml_doc
        self.cluster_dct = cluster_dct
        self.loader = loader

    @property
    def name(self):
        return self.cluster_dct.get("name")

    @property
    def ctime(self):
        return self.yaml_doc.ctime

    @property
    def mtime(self):
        return self.yaml_doc.mtime

    @property
    def atime(self):
        return self.yaml_doc.atime

    def get_context(self) -> Context:
        return self.loader.get_context_by_cluster(self.name)


class User:
    def __init__(self, yaml_doc, user_dct) -> None:
        self.yaml_doc = yaml_doc
        self.user_dct = user_dct

    @property
    def name(self):
        return self.user_dct.get("name")

    @property
    def ctime(self):
        return self.yaml_doc.ctime

    @property
    def mtime(self):
        return self.yaml_doc.mtime

    @property
    def atime(self):
        return self.yaml_doc.atime

    def get_attribute_names(self):
        return list(self.user_dct["user"].keys())

    def get_attribute(self, name):
        return self.user_dct["user"].get(name)


class KubeConfigLoader:
    _instance = None
    logger = logging.getLogger("kube-config-loader")

    def __init__(self, kubecfg_var="KUBECONFIG", kubecfg_dir="~/.kube") -> None:
        self.kubecfg_var = kubecfg_var
        self.kubecfg_dir = os.path.expanduser(kubecfg_dir)

    @classmethod
    def get_instance(cls):
        if not cls._instance:
            cls._instance = cls()

        return cls._instance

    def detect_kubeconfig_files(self) -> Iterable[str]:
        config_var = os.getenv(self.kubecfg_var)
        if config_var:
            fps = config_var.split(":")
            return fps

        fns = os.listdir(self.kubecfg_dir)
        fps = []
        for fn in fns:
            fp = os.path.join(self.kubecfg_dir, fn)

            if not os.path.isfile(fp):
                continue

            fps.append(fp)

        return fps

    def get_all_documents(self) -> Iterable[YamlDoc]:
        for fp in self.detect_kubeconfig_files():
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

            st = os.stat(fp)
            yield YamlDoc(
                filepath=fp,
                doc=doc,
                ctime=st.st_ctime,
                mtime=st.st_mtime,
                atime=st.st_atime,
            )

    def get_all_clusters(self) -> Iterable[Cluster]:
        for yaml_doc in self.get_all_documents():
            for cluster_dct in yaml_doc.doc.get("clusters"):
                yield Cluster(yaml_doc, cluster_dct, self)

    def get_all_contexts(self) -> Iterable[Context]:
        for yaml_doc in self.get_all_documents():
            for context_dct in yaml_doc.doc.get("contexts"):
                yield Context(yaml_doc, context_dct, self)

    def get_all_users(self) -> Iterable[User]:
        for yaml_doc in self.get_all_documents():
            for user_dct in yaml_doc.doc.get("users"):
                yield User(yaml_doc, user_dct)

    def get_cluster(self, cluster_name) -> Cluster:
        for cluster in self.get_all_clusters():
            if cluster.name == cluster_name:
                return cluster

    def get_context_by_cluster(self, cluster_name) -> Context:
        for context in self.get_all_contexts():
            if context.cluster_name == cluster_name:
                return context

    def get_user(self, user_name) -> User:
        for user in self.get_all_users():
            if user.name == user_name:
                return user
