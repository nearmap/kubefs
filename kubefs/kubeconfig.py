from typing import Iterator
import os
import logging
import yaml


class User:
    def __init__(self, user_dct) -> None:
        self.user_dct = user_dct

    def __repr__(self):
        return (
            "<%s name=%r, username=%r, password=%r, client_cert=%r, client_key=%r>"
            % (
                self.__class__.__name__,
                self.name,
                self.username,
                self.password,
                self.client_cert_data and ("<%d bytes>" % len(self.client_cert_data)),
                self.client_key_data and ("<%d bytes>" % len(self.client_key_data)),
            )
        )

    @property
    def name(self):
        return self.user_dct.get("name")

    @property
    def client_cert_data(self):
        return self.user_dct["user"].get("client-certificate-data")

    @property
    def client_key_data(self):
        return self.user_dct["user"].get("client-key-data")

    @property
    def password(self):
        return self.user_dct["user"].get("password")

    @property
    def username(self):
        return self.user_dct["user"].get("username")


class Cluster:
    def __init__(self, factory, ctx_dct) -> None:
        self.factory = factory
        self.ctx_dct = ctx_dct

    def __repr__(self):
        return "<%s context=%r, cluster=%r, user=%r>" % (
            self.__class__.__name__,
            self.name,
            self.cluster,
            self.user,
        )

    @property
    def name(self):
        return self.ctx_dct.get("name")

    @property
    def user(self):
        return self.ctx_dct["context"].get("user")

    @property
    def cluster(self):
        return self.ctx_dct["context"].get("cluster")


class KubeConfigExplorer:
    def __init__(self, kubecfg_loc="~/.kube") -> None:
        self.kubecfg_loc = os.path.expanduser(kubecfg_loc)

    def get_all_clusters(self) -> Iterator[Cluster]:
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
                    logging.debug("Failed to parse kube config: %s", fp)
                    continue

            kind = doc.get("kind")
            if not kind:
                logging.debug(
                    "Candidate kube config does not have kind: Config: %s", fp
                )
                continue

            for user_dct in doc.get("users"):
                yield User(user_dct)
