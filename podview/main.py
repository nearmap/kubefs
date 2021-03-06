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
from podview.model.model import ScreenModel
from podview.model.updater import ModelUpdater
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
        self.async_loop = launch_in_background_thread()

        selector = get_selector()
        contexts = selector.fnmatch_context(self.args.cluster_context)

        oev_receivers_lists = [self.launch_watcher(ctx) for ctx in contexts]
        oev_receivers = [recv for lst in oev_receivers_lists for recv in lst]

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
                if self.display.stop_interacting(buffer, timeout=0.5):
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
