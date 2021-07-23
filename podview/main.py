import argparse
import fnmatch
from typing import Optional

from akube.async_loop import launch_in_background_thread
from akube.cluster_facade import SyncClusterFacade
from akube.model.api_resource import NamespaceKind, PodKind
from akube.model.object_model import Namespace
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvReceiver
from kube.config import Context, get_selector
from kube.tools.logs import configure_logging
from podview.model.model import ScreenModel
from podview.model.updater import ModelUpdater
from podview.view.renderer import BufferRenderer


class Program:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args

        self.model = ScreenModel()
        self.renderer = BufferRenderer()

        self.async_loop = None
        self.updater = None

    def find_matching_namespace(
        self, namespace_pat: str, context: Context
    ) -> Optional[str]:
        facade = SyncClusterFacade(async_loop=self.async_loop, context=context)
        selector = ObjectSelector(res=NamespaceKind)
        namespace_objs = facade.list_objects(selector=selector)
        namespaces = [Namespace(namespace).meta.name for namespace in namespace_objs]

        namespaces = fnmatch.filter(namespaces, namespace_pat)
        assert len(namespaces) == 1

        return namespaces[0]

    def launch_watcher(self, context: Context) -> OEvReceiver:
        facade = SyncClusterFacade(async_loop=self.async_loop, context=context)

        namespace = None
        if self.args.namespace:
            namespace = self.find_matching_namespace(self.args.namespace, context)

        selector = ObjectSelector(res=PodKind, namespace=namespace)

        # list first to advance the resourceVersion in the client to the current
        # point in time - so we can skip events that are in the past
        facade.list_objects(selector=selector)

        return facade.start_watching(selector=selector)

    def initialize(self):
        configure_logging()
        self.async_loop = launch_in_background_thread()

        selector = get_selector()
        contexts = selector.fnmatch_context(self.args.context)

        oev_receivers = [self.launch_watcher(ctx) for ctx in contexts]

        self.updater = ModelUpdater(receivers=oev_receivers, args=self.args)

    def run_ui_loop(self):
        while True:
            self.updater.run(model=self.model, timeout=0.5)
            buffer = self.renderer.render(self.model)
            print(buffer.assemble())

    def run(self):
        self.initialize()
        self.run_ui_loop()
