import time
from datetime import datetime
from typing import Dict

from kube.config import Context
from podview.value import Value


class ContainerModel:
    def __init__(self, name: str) -> None:
        self.name = name

        self.image_hash: Value[str] = Value()
        self.restart_count: Value[int] = Value()
        self.state: Value[str] = Value()
        # self.started_at: Value[datetime] = Value()
        # self.finished_at: Value[datetime] = Value()


class PodModel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.containers: Dict[str, ContainerModel] = {}

        self.phase: Value[str] = Value()
        self.start_time: Value[datetime] = Value()
        self.image_hash: Value[str] = Value()

    def get_container(self, name: str) -> ContainerModel:
        container = self.containers.get(name)

        if container is None:
            container = ContainerModel(name=name)
            self.containers[name] = container

        return container


class ClusterModel:
    def __init__(self, context: Context) -> None:
        self.context = context
        self.name = context.short_name
        self.pods: Dict[str, PodModel] = {}

    def get_pod(self, name: str) -> PodModel:
        pod = self.pods.get(name)

        if pod is None:
            pod = PodModel(name=name)
            self.pods[name] = pod

        return pod


class ScreenModel:
    def __init__(self) -> None:
        self.clusters: Dict[Context, ClusterModel] = {}

        self.elapsed: Value[str] = Value()
        self.elapsed.set(value="", ts=time.time())

    def get_cluster(self, context: Context) -> ClusterModel:
        cluster = self.clusters.get(context)

        if cluster is None:
            cluster = ClusterModel(context=context)
            self.clusters[context] = cluster

        return cluster
