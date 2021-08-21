import argparse
import time
from datetime import datetime
from typing import Dict, List

from kube.config import Context
from podview.model.value import Value


class ContainerModel:
    def __init__(self, name: str) -> None:
        self.name = name

        self.ready: Value[bool] = Value()
        self.started: Value[bool] = Value()
        self.image_hash: Value[str] = Value()
        self.restart_count: Value[int] = Value()

        self.state: Value[str] = Value()
        self.exit_code: Value[int] = Value()
        self.reason: Value[str] = Value()
        self.message: Value[str] = Value()

        # self.last_state: Value[str] = Value()


class PodModel:
    def __init__(self, name: str) -> None:
        self.name = name
        self.containers: Dict[str, ContainerModel] = {}

        self.creation_timestamp: Value[datetime] = Value()
        self.deletion_timestamp: Value[datetime] = Value()
        self.phase: Value[str] = Value()
        self.image_hash: Value[str] = Value()

    def get_container(self, name: str) -> ContainerModel:
        container = self.containers.get(name)

        if container is None:
            container = ContainerModel(name=name)
            self.containers[name] = container

        return container

    def iter_containers(self) -> List[ContainerModel]:
        containers = list(self.containers.values())
        containers.sort(key=lambda cont: cont.name)
        return containers


class ClusterModel:
    def __init__(self, context: Context) -> None:
        self.context = context

        self.name: Value[str] = Value()
        self.pods: Dict[str, PodModel] = {}

    def get_pod(self, name: str) -> PodModel:
        pod = self.pods.get(name)

        if pod is None:
            pod = PodModel(name=name)
            self.pods[name] = pod

        return pod

    def iter_pods(self) -> List[PodModel]:
        pods = list(self.pods.values())
        pods.sort(key=lambda pod: (pod.creation_timestamp.current_value, pod.name))
        return pods


class ScreenModel:
    def __init__(self, args: argparse.Namespace) -> None:
        self.clusters: Dict[Context, ClusterModel] = {}

        self.cluster: Value[str] = Value()
        self.namespace: Value[str] = Value()
        self.pod: Value[str] = Value()
        self.uptime: Value[str] = Value()

        ts = time.time()
        self.cluster.set(args.cluster_context, ts=ts)
        self.namespace.set(args.namespace, ts=ts)
        self.pod.set(args.pod, ts=ts)
        self.uptime.set(value="", ts=ts)

    def get_cluster(self, context: Context) -> ClusterModel:
        cluster = self.clusters.get(context)

        if cluster is None:
            cluster = ClusterModel(context=context)
            self.clusters[context] = cluster

        return cluster

    def iter_clusters(self) -> List[ClusterModel]:
        clusters = list(self.clusters.values())
        clusters.sort(key=lambda cluster: cluster.context.short_name)
        return clusters
