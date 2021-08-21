import argparse
import fnmatch
import logging
from threading import current_thread
from typing import Optional

from akube.async_loop import AsyncLoop, launch_in_background_thread
from akube.cluster_facade import SyncClusterFacade
from akube.model.api_resource import NamespaceKind, PodKind
from akube.model.object_model.kinds import Namespace
from akube.model.selector import ObjectSelector
from kube.channels.objects import OEvReceiver
from kube.config import Context, get_selector
from kube.tools.logs import configure_logging
from podview.model.model import ScreenModel
from podview.model.updater import ModelUpdater
from podview.view.buffer import ScreenBuffer
from podview.view.display import CursesDisplay, CursesDisplayError
from podview.view.renderer import BufferRenderer


class Program:
    def __init__(self, args: argparse.Namespace, logfile="var/log/podview.log") -> None:
        self.args = args
        self.logfile = logfile
        self.logger = logging.getLogger("program")

        self.model = ScreenModel(args)
        self.display = CursesDisplay()

        self.async_loop: Optional[AsyncLoop] = None
        self.updater = None

    def find_matching_namespace(
        self, namespace_pat: str, context: Context
    ) -> Optional[str]:
        assert self.async_loop is not None  # help mypy

        facade = SyncClusterFacade(async_loop=self.async_loop, context=context)
        selector = ObjectSelector(res=NamespaceKind)
        namespace_objs = facade.list_objects(selector=selector)
        namespaces = [Namespace(namespace).meta.name for namespace in namespace_objs]

        namespaces = fnmatch.filter(namespaces, namespace_pat)
        assert len(namespaces) == 1

        return namespaces[0]

    def launch_watcher(self, context: Context) -> OEvReceiver:
        assert self.async_loop is not None  # help mypy

        facade = SyncClusterFacade(async_loop=self.async_loop, context=context)

        namespace = None
        if self.args.namespace not in (None, '', '*'):
            namespace = self.find_matching_namespace(self.args.namespace, context)

        selector = ObjectSelector(res=PodKind, namespace=namespace)

        return facade.list_then_watch(selector=selector)

    def initialize(self):
        main_thread = current_thread()
        main_thread.setName("UiThread")

        configure_logging(filename=self.logfile)
        self.async_loop = launch_in_background_thread()

        selector = get_selector()
        contexts = selector.fnmatch_context(self.args.cluster_context)

        oev_receivers = [self.launch_watcher(ctx) for ctx in contexts]

        self.updater = ModelUpdater(
            contexts=contexts, receivers=oev_receivers, args=self.args
        )

    def run_ui_loop(self):
        self.display.initialize()

        try:
            while True:
                # self.updater.run(model=self.model, timeout=0.5)
                self.updater.run(model=self.model, timeout=0.01)

                renderer = BufferRenderer(self.model)
                buffer = renderer.render()

                # print(buffer.assemble(dim=(120, 24), border_horiz="-", border_vert="|"))
                if self.display.interact(buffer, timeout=0.5):
                    break

        except (KeyboardInterrupt, CursesDisplayError):
            self.display.exit()

        except Exception:
            self.logger.exception("Uncaught exception in run_ui_loop()")
            self.display.exit()

        self.async_loop.shutdown()

    def run(self):
        self.initialize()
        self.run_ui_loop()
