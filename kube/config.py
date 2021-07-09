import logging
import os
from typing import Dict, Optional, Sequence

import yaml

from kube.tools.repr import disp_secret_blob, disp_secret_string


class User:
    def __init__(
        self,
        *,
        name: str,
        username: Optional[str],
        password: Optional[str],
        client_cert_path: Optional[str],
        client_key_path: Optional[str],
        client_cert_data: Optional[str],
        client_key_data: Optional[str],
    ) -> None:
        self.name = name
        self.username = username
        self.password = password
        self.client_cert_path = client_cert_path
        self.client_key_path = client_key_path
        self.client_cert_data = client_cert_data
        self.client_key_data = client_key_data

    def __repr__(self) -> str:
        return (
            "<%s name=%r, username=%r, password=%s, "
            "client_cert_path=%r, client_key_path=%r, "
            "client_cert_data=%s, client_key_data=%s>"
        ) % (
            self.__class__.__name__,
            self.name,
            self.username,
            disp_secret_string(self.password),
            self.client_cert_path,
            self.client_key_path,
            disp_secret_blob(self.client_cert_data),
            disp_secret_blob(self.client_key_data),
        )


class Cluster:
    def __init__(self, *, name: str, server: str, ca_cert_path: Optional[str]) -> None:
        self.name = name
        self.server = server
        self.ca_cert_path = ca_cert_path

    def __repr__(self) -> str:
        return "<%s name=%r, server=%r, ca_cert_path=%r>" % (
            self.__class__.__name__,
            self.name,
            self.server,
            self.ca_cert_path,
        )


class Context:
    def __init__(
        self, *, name: str, user: User, cluster: Cluster, namespace: Optional[str]
    ) -> None:
        self.name = name
        self.user = user
        self.cluster = cluster
        self.namespace = namespace

    def __repr__(self) -> str:
        return "<%s name=%r, user=%r, cluster=%r, namespace=%r>" % (
            self.__class__.__name__,
            self.name,
            self.user,
            self.cluster,
            self.namespace,
        )


class KubeConfigFile:
    def __init__(
        self,
        *,
        contexts: Sequence[Context],
        users: Sequence[User],
        clusters: Sequence[Cluster],
    ) -> None:
        self.contexts = contexts or []
        self.users = users or []
        self.clusters = clusters or []

    def __repr__(self) -> str:
        return "<%s contexts=%r, users=%r, clusters=%r>" % (
            self.__class__.__name__,
            self.contexts,
            self.users,
            self.clusters,
        )


class KubeConfigCollection:
    def __init__(self) -> None:
        self.clusters: Dict[str, Cluster] = {}
        self.contexts: Dict[str, Context] = {}
        self.users: Dict[str, User] = {}

    def add_file(self, config_file: KubeConfigFile) -> None:
        for cluster in config_file.clusters:
            self.clusters[cluster.name] = cluster

        for context in config_file.contexts:
            self.contexts[context.name] = context

        for user in config_file.users:
            self.users[user.name] = user

    def get_contexts(self) -> Sequence[Context]:
        names = list(self.contexts.keys())
        names.sort()
        objs = [self.contexts[name] for name in names]
        return objs


class KubeConfigLoader:
    def __init__(
        self, *, config_dir="$HOME/.kube", config_var="KUBECONFIG", logger=None
    ) -> None:
        self.config_dir = config_dir
        self.config_var = config_var
        self.logger = logger or logging.getLogger("config-loader")

    def get_candidate_files(self) -> Sequence[str]:
        # use config_var if set
        env_var = os.getenv(self.config_var)
        if env_var:
            filepaths = env_var.split(":")
            filepaths = [fp.strip() for fp in filepaths if fp.strip()]
            return filepaths

        # fall back on config_dir
        path = os.path.expandvars(self.config_dir)
        filenames = os.listdir(path)
        filepaths = []

        for fn in filenames:
            fp = os.path.join(path, fn)
            if not os.path.isfile(fp):
                continue

            filepaths.append(fp)

        return filepaths

    def parse_context(
        self, clusters: Sequence[Cluster], users: Sequence[User], dct
    ) -> Optional[Context]:
        name = dct.get("name")

        obj = dct.get("context")
        cluster_id = obj.get("cluster")
        namespace = obj.get("namespace")
        user_id = obj.get("user")

        # 'name', 'cluster' and 'user' are required attributes
        if all((name, cluster_id, user_id)):
            users = [user for user in users if user.name == user_id]
            if not users:
                self.logger.warn(
                    "When parsing context %r could not find matching user %r",
                    name,
                    user_id,
                )

            clusters = [cluster for cluster in clusters if cluster.name == cluster_id]
            if not clusters:
                self.logger.warn(
                    "When parsing context %r could not find matching cluster %r",
                    name,
                    cluster_id,
                )

            if users and clusters:
                return Context(
                    name=name,
                    user=users[0],
                    cluster=clusters[0],
                    namespace=namespace,
                )

        return None

    def parse_cluster(self, dct) -> Optional[Cluster]:
        name = dct.get("name")

        obj = dct.get("cluster")
        server = obj.get("server")
        ca_cert_path = obj.get("certificate-authority")

        # 'name' and 'server' are required attributes
        if name and server:
            return Cluster(name=name, server=server, ca_cert_path=ca_cert_path)

        return None

    def parse_user(self, dct) -> Optional[User]:
        name = dct.get("name")

        obj = dct.get("user")
        password = obj.get("password")
        username = obj.get("username")
        client_cert_path = obj.get("client-certificate")
        client_key_path = obj.get("client-key")
        client_cert_data = obj.get("client-certificate-data")
        client_key_data = obj.get("client-key-data")

        # 'name' is the only required attribute
        if name:
            return User(
                name=name,
                username=username,
                password=password,
                client_cert_path=client_cert_path,
                client_key_path=client_key_path,
                client_cert_data=client_cert_data,
                client_key_data=client_key_data,
            )

        return None

    def load_file(self, filepath: str) -> Optional[KubeConfigFile]:
        with open(filepath, "rb") as fl:
            try:
                dct = yaml.load(fl, Loader=yaml.SafeLoader)
            except Exception:
                self.logger.warn("Failed to parse kube config as yaml: %s", filepath)
                return None

        kind = dct.get("kind")
        if not kind == "Config":
            self.logger.warn("Kube config does not have kind: Config: %s", filepath)
            return None

        clust_list = [self.parse_cluster(cluster) for cluster in dct["clusters"]]
        clusters = [cluster for cluster in clust_list if cluster]

        user_list = [self.parse_user(user) for user in dct["users"]]
        users = [user for user in user_list if user]

        ctx_list = [self.parse_context(clusters, users, ctx) for ctx in dct["contexts"]]
        contexts = [ctx for ctx in ctx_list if ctx]

        # The context is the organizing principle of a kube config so if we
        # didn't find any we failed to parse the file
        if contexts:
            return KubeConfigFile(contexts=contexts, users=users, clusters=clusters)

        return None

    def create_collection(self) -> KubeConfigCollection:
        collection = KubeConfigCollection()

        for filepath in self.get_candidate_files():
            config_file = self.load_file(filepath)
            if config_file:
                collection.add_file(config_file)

        return collection


ld = KubeConfigLoader()
coll = ld.create_collection()
for c in coll.get_contexts():
    print(c)
