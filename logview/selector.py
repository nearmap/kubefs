import argparse
import fnmatch
import random
from typing import Dict, List, Tuple

from logview.target import PodTarget
from podview.model.model import ContainerModel, PodModel, ScreenModel


class PodSelector:
    def __init__(
        self,
        args: argparse.Namespace,
    ) -> None:
        self.args = args

        # the pod+container pairs that match our log streaming criteria
        self.candidates: List[PodTarget] = []

        # long lived PodTarget objects
        self.all_targets: Dict[Tuple[PodModel, ContainerModel], PodTarget] = {}

    def get_target(self, pod: PodModel, container: ContainerModel) -> PodTarget:
        key = (pod, container)
        target = self.all_targets.get(key)

        if target is None:
            target = PodTarget(pod, container)
            self.all_targets[key] = target

        return target

    def refresh_candidates(self, model: ScreenModel) -> None:
        candidates = []

        for cluster in model.iter_clusters():
            for pod in cluster.iter_pods():
                # print(pod.name, pod.phase.current_value)
                # if the pod isn't running it's also not producing logs so skip it
                if pod.phase.current_value not in ["running"]:
                    continue

                # the pod name does not match the filter
                if self.args.pod and not fnmatch.fnmatch(pod.name, self.args.pod):
                    continue

                for container in pod.iter_containers():
                    # if the container is not running it's also not producing logs
                    if container.state.current_value not in ["running"]:
                        continue

                    # the container name does not match the filter
                    if self.args.container and not fnmatch.fnmatch(
                        container.name, self.args.container
                    ):
                        continue

                    target = self.get_target(pod, container)
                    candidates.append(target)

        self.candidates = candidates

    def select_targets(self, count: int) -> List[PodTarget]:
        if not self.candidates:
            return []

        # TODO: try to make it cycle through the population more and not just
        # select randomly, in order to make it more likely that we iterate
        # through all targets

        chosen = []
        cands = self.candidates[:]

        while cands and len(chosen) < count:
            choice = random.choice(cands)
            cands.remove(choice)
            chosen.append(choice)

        return chosen
