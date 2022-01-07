import argparse
import fnmatch
import logging
from threading import current_thread
from typing import List, Optional

from kube.async_loop import AsyncLoop, launch_in_background_thread
from kube.channels.objects import OEvReceiver
from kube.cluster_facade import SyncClusterFacade
from kube.config import Context, get_selector
from kube.model.api_resource import NamespaceKind, PodKind
from kube.model.object_model.kinds import Namespace
from kube.model.selector import ObjectSelector
from kube.tools.logs import configure_logging
from logview.display import LogDisplay
from logview.selector import PodSelector, PodTarget
from podview.model.model import ScreenModel
from podview.model.updater import ModelUpdater


class FatalError(Exception):
    pass


class Program:
    def __init__(self, args: argparse.Namespace, logfile="var/log/logview.log") -> None:
        self.args = args
        self.logfile = logfile
        self.logger = logging.getLogger("program")

        self.display = LogDisplay()
        self.model = ScreenModel(args)
        self.pod_selector = PodSelector(args)

        self.async_loop: Optional[AsyncLoop] = None
        self.facade: Optional[SyncClusterFacade] = None

        self.updater = None
        self.targets: List[PodTarget] = []

    def find_matching_namespaces(
        self, namespace_pat: str, context: Context
    ) -> List[str]:
        assert self.async_loop is not None  # help mypy

        facade = SyncClusterFacade(async_loop=self.async_loop, context=context)
        selector = ObjectSelector(res=NamespaceKind)
        namespace_objs = facade.list_objects(selector=selector)
        namespaces = [Namespace(namespace).meta.name for namespace in namespace_objs]

        return fnmatch.filter(namespaces, namespace_pat)

    def launch_watcher(self, context: Context) -> List[OEvReceiver]:
        assert self.async_loop is not None  # help mypy

        facade = SyncClusterFacade(async_loop=self.async_loop, context=context)

        oev_receivers = []
        if self.args.namespace not in (None, "", "*"):
            namespaces = self.find_matching_namespaces(self.args.namespace, context)
            for namespace in namespaces:
                selector = ObjectSelector(res=PodKind, namespace=namespace)
                oev_receiver = facade.list_then_watch(selector=selector)
                oev_receivers.append(oev_receiver)

        else:
            selector = ObjectSelector(res=PodKind, namespace=None)
            oev_receiver = facade.list_then_watch(selector=selector)
            oev_receivers.append(oev_receiver)

        return oev_receivers

    def initialize(self):
        main_thread = current_thread()
        main_thread.setName("UiThread")

        configure_logging(filename=self.logfile)

        selector = get_selector()
        contexts = selector.fnmatch_context(self.args.cluster_context)

        if len(contexts) != 1:
            names = [ctx.name for ctx in contexts]
            raise FatalError(
                f"Need exactly 1 cluster context to run, matched: {names!r}"
            )

        self.async_loop = launch_in_background_thread()
        self.facade = SyncClusterFacade(async_loop=self.async_loop, context=contexts[0])

        oev_receivers_lists = [self.launch_watcher(ctx) for ctx in contexts]
        oev_receivers = [recv for lst in oev_receivers_lists for recv in lst]

        self.updater = ModelUpdater(
            contexts=contexts, receivers=oev_receivers, args=self.args
        )

    def safe_initialize(self) -> bool:
        try:
            self.initialize()

        except Exception as exc:
            print(f"Failed to initialize: {exc}")

            if self.async_loop:
                self.async_loop.shutdown()

            return False

        return True

    def run_ui_loop(self):
        count = 2

        timeout_short_s = 5
        timeout_standard_s = 120
        timeout_s = timeout_standard_s

        try:
            while True:
                # run the updater for a bit to sync the model with all pods in
                # the namespaces we are watching
                self.updater.run(model=self.model, timeout=0.1)

                # refresh the pod selector to pick just the pods and containers
                # that we want to stream logs from
                self.pod_selector.refresh_candidates(model=self.model)
                num_cands = len(self.pod_selector.candidates)
                print(f"{num_cands} matching pod/container targets")

                # we have no targets yet: select them
                if not self.targets:
                    self.targets = self.pod_selector.select_targets(count=count)

                # we have fewer targets than desired, re-select them to maybe get more
                elif len(self.targets) < count:
                    self.targets = self.pod_selector.select_targets(count=count)

                # if we have few targets the model may still be populating so use a short timeout
                timeout_s = timeout_standard_s
                if len(self.targets) < count:
                    timeout_s = timeout_short_s

                if self.targets:
                    names = "\n- ".join(
                        [
                            f"{target.pod.name}/{target.container.name}"
                            for target in self.targets
                        ]
                    )
                    print(f"Streaming logs for {timeout_s}s from:\n- {names}")

                    for target in self.targets:
                        target.start_streaming(self.facade)

                    self.display.display_loop(targets=self.targets, timeout_s=timeout_s)

                    for target in self.targets:
                        target.start_streaming(self.facade)

        except (KeyboardInterrupt,):
            pass

        except Exception:
            self.logger.exception("Uncaught exception in run_ui_loop()")

        for target in self.targets:
            target.start_streaming(self.facade)

        self.async_loop.shutdown()

    def run(self):
        if self.safe_initialize():
            self.run_ui_loop()
