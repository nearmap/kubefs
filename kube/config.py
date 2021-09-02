import base64
import fnmatch
import logging
import os
import tempfile
from ssl import SSLContext, create_default_context
from typing import Dict, List, Optional, Sequence

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

        # host.company.com -> host
        self.short_name = name.split(".")[0]

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

    def get_attribute_names(self) -> List[str]:
        "Returns names of all attributes that are set"

        names = []
        attnames = dir(self)

        for attname in attnames:
            value = getattr(self, attname)

            if attname.startswith("_") or callable(value):
                continue

            if not value:
                continue

            names.append(attname)

        return names


class Cluster:
    def __init__(
        self,
        *,
        name: str,
        server: str,
        ca_cert_path: Optional[str],
        ca_cert_data: Optional[str],
    ) -> None:
        self.name = name
        self.server = server
        self.ca_cert_path = ca_cert_path
        self.ca_cert_data = ca_cert_data

        # host.company.com -> host
        self.short_name = name.split(".")[0]

    def __repr__(self) -> str:
        return "<%s name=%r, server=%r, ca_cert_path=%r, ca_cert_data=%r>" % (
            self.__class__.__name__,
            self.name,
            self.server,
            self.ca_cert_path,
            disp_secret_blob(self.ca_cert_data),
        )


class Context:
    def __init__(
        self,
        *,
        name: str,
        user: User,
        cluster: Cluster,
        namespace: Optional[str],
    ) -> None:
        self.name = name
        self.user = user
        self.cluster = cluster
        self.namespace = namespace
        self.file: "KubeConfigFile" = None  # type: ignore

        # host.company.com -> host
        self.short_name = name.split(".")[0]

    def __repr__(self) -> str:
        return "<%s name=%r, short_name=%r, user=%r, cluster=%r, namespace=%r>" % (
            self.__class__.__name__,
            self.name,
            self.short_name,
            self.user,
            self.cluster,
            self.namespace,
        )

    def set_file(self, file: "KubeConfigFile") -> None:
        self.file = file

    def create_ssl_context(self) -> SSLContext:
        kwargs = {}

        if self.cluster.ca_cert_path:
            kwargs["cafile"] = self.cluster.ca_cert_path

        elif self.cluster.ca_cert_data:
            value = base64.b64decode(self.cluster.ca_cert_data)
            cert_data = value.decode()
            kwargs["cadata"] = cert_data

        ssl_context = create_default_context(**kwargs)

        # If the cert and key are in the form of blobs then we need to create
        # temporary files for them because the ssl lib only accepts file paths.
        # We first create a tempdir which is rwx only for the current user, so
        # no other users can even list its contents. We then create the two temp
        # files inside it. The tempdir and its contents get removed when the
        # context manager exits.
        if self.user.client_cert_data and self.user.client_key_data:
            with tempfile.TemporaryDirectory(prefix="kube-client.") as tempdir_name:
                cert_content = base64.b64decode(self.user.client_cert_data)
                cert_file_fd, cert_file_name = tempfile.mkstemp(dir=tempdir_name)
                os.write(cert_file_fd, cert_content)

                cert_content = base64.b64decode(self.user.client_key_data)
                key_file_fd, key_file_name = tempfile.mkstemp(dir=tempdir_name)
                os.write(key_file_fd, cert_content)

                ssl_context.load_cert_chain(
                    certfile=cert_file_name,
                    keyfile=key_file_name,
                )

        elif self.user.client_cert_path and self.user.client_key_path:
            ssl_context.load_cert_chain(
                certfile=self.user.client_cert_path,
                keyfile=self.user.client_key_path,
            )

        return ssl_context


class KubeConfigFile:
    def __init__(
        self,
        *,
        filepath: str,
        contexts: Sequence[Context],
        users: Sequence[User],
        clusters: Sequence[Cluster],
        ctime: float,
        mtime: float,
        atime: float,
    ) -> None:
        self.filepath = filepath
        self.contexts = contexts or []
        self.users = users or []
        self.clusters = clusters or []
        self.ctime = ctime
        self.mtime = mtime
        self.atime = atime

    def __repr__(self) -> str:
        return "<%s filepath=%r, contexts=%r, users=%r, clusters=%r>" % (
            self.__class__.__name__,
            self.filepath,
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
        # NOTE: does not enforce uniqueness of context/user/cluster names

        for cluster in config_file.clusters:
            self.clusters[cluster.name] = cluster

        for context in config_file.contexts:
            self.contexts[context.name] = context

        for user in config_file.users:
            self.users[user.name] = user

    def get_context_names(self) -> Sequence[str]:
        names = list(self.contexts.keys())
        names.sort()
        return names

    def get_context(self, name) -> Optional[Context]:
        return self.contexts.get(name)


class KubeConfigSelector:
    def __init__(self, *, collection: KubeConfigCollection) -> None:
        self.collection = collection

    def fnmatch_context(self, pattern: str) -> List[Context]:
        names = self.collection.get_context_names()
        names = fnmatch.filter(names, pattern)
        objs = [self.collection.get_context(name) for name in names]
        contexts = [ctx for ctx in objs if ctx]
        return contexts


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

    def take_after_last_slash(self, name: str) -> str:
        # arn:aws:iam::123:role/myrole -> myrole
        if "/" in name:
            name = name.rsplit("/")[1]

        return name

    def parse_context(
        self, clusters: Sequence[Cluster], users: Sequence[User], dct
    ) -> Optional[Context]:
        name = dct.get("name")
        name = self.take_after_last_slash(name)

        obj = dct.get("context")
        cluster_id = obj.get("cluster")
        namespace = obj.get("namespace")
        user_id = obj.get("user")

        cluster_id = self.take_after_last_slash(cluster_id)
        user_id = self.take_after_last_slash(user_id)

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
        name = self.take_after_last_slash(name)

        obj = dct.get("cluster")
        server = obj.get("server")
        ca_cert_path = obj.get("certificate-authority")
        ca_cert_data = obj.get("certificate-authority-data")

        # 'name' and 'server' are required attributes
        if name and server:
            return Cluster(
                name=name,
                server=server,
                ca_cert_path=ca_cert_path,
                ca_cert_data=ca_cert_data,
            )

        return None

    def parse_user(self, dct) -> Optional[User]:
        name = dct.get("name")
        name = self.take_after_last_slash(name)

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

        clust_list = [self.parse_cluster(clus) for clus in dct.get("clusters") or []]
        clusters = [cluster for cluster in clust_list if cluster]

        user_list = [self.parse_user(user) for user in dct.get("users") or []]
        users = [user for user in user_list if user]

        ctx_list = [
            self.parse_context(clusters, users, ctx)
            for ctx in dct.get("contexts") or []
        ]
        contexts = [ctx for ctx in ctx_list if ctx]

        st = os.stat(filepath)

        # The context is the organizing principle of a kube config so if we
        # didn't find any we failed to parse the file
        if contexts:
            config_file = KubeConfigFile(
                filepath=filepath,
                contexts=contexts,
                users=users,
                clusters=clusters,
                ctime=st.st_ctime,
                mtime=st.st_mtime,
                atime=st.st_atime,
            )

            for context in contexts:
                context.set_file(config_file)

            return config_file

        return None

    def create_collection(self) -> KubeConfigCollection:
        collection = KubeConfigCollection()

        for filepath in self.get_candidate_files():
            config_file = self.load_file(filepath)
            if config_file:
                collection.add_file(config_file)

        return collection


def get_selector() -> KubeConfigSelector:
    loader = KubeConfigLoader()
    collection = loader.create_collection()
    selector = KubeConfigSelector(collection=collection)
    return selector
