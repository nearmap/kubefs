import time
from typing import Optional

import dateutil.parser

from kube.async_loop import get_loop
from kube.cluster_facade import SyncClusterFacade
from kube.config import Context
from kube.model.api_resource import ApiResource, NamespaceKind
from kube.model.selector import ObjectSelector
from kubefs.fs_model import ONE_DAY, Directory, File, Payload
from kubefs.text import to_json


def mkpayload(*, obj):
    block = to_json(obj)

    timestamp = None

    creationTimestamp = obj["metadata"].get("creationTimestamp")
    if creationTimestamp:
        timestamp = dateutil.parser.parse(creationTimestamp).timestamp()

    if timestamp is None:
        timestamp = time.time()

    fn = obj["metadata"]["name"]
    if fn.endswith("."):
        fn = f"{fn}json"
    else:
        fn = f"{fn}.json"

    payload = Payload(
        name=fn,
        data=block.encode(),
        ctime=timestamp,
        mtime=timestamp,
    )

    return payload


class KubeClusterGenericResourceDir(Directory):
    @classmethod
    def create(
        cls,
        *,
        payload: Payload,
        context: Context,
        api_resource: ApiResource,
        namespace: Optional[str] = None,
    ):
        self = cls(payload=payload)
        self.context = context
        self.api_resource = api_resource
        self.namespace = namespace
        self.facade = SyncClusterFacade(async_loop=get_loop(), context=self.context)
        self.selector = ObjectSelector(res=self.api_resource, namespace=self.namespace)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            items = self.facade.list_objects(selector=self.selector)

            files = []
            for item in items:
                payload = mkpayload(obj=item)
                files.append(File(payload=payload))

            self.set_lazy_entries(files)

        return self.lazy_entries


class KubeClusterNamespaceDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, namespace: str):
        self = cls(payload=payload)
        self.context = context
        self.namespace = namespace
        self.facade = SyncClusterFacade(async_loop=get_loop(), context=self.context)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            api_resources = self.facade.list_api_resources()

            dirs = []
            for api_resource in api_resources:
                if not api_resource.namespaced:
                    continue

                payload = Payload(name=api_resource.name)
                dir = KubeClusterGenericResourceDir.create(
                    payload=payload,
                    context=self.context,
                    api_resource=api_resource,
                    namespace=self.namespace,
                )
                dirs.append(dir)

            # api resources almost never change
            self.set_lazy_entries(dirs, lifetime=ONE_DAY)

        return self.lazy_entries


class KubeClusterNamespacesDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.context = context
        self.facade = SyncClusterFacade(async_loop=get_loop(), context=self.context)
        self.selector = ObjectSelector(res=NamespaceKind)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            items = self.facade.list_objects(selector=self.selector)

            dirs = []
            for item in items:
                name = item["metadata"]["name"]
                payload = Payload(name=name)

                dir = KubeClusterNamespaceDir.create(
                    payload=payload,
                    context=self.context,
                    namespace=name,
                )
                dirs.append(dir)

            # namespaces rarely change
            self.set_lazy_entries(dirs, lifetime=ONE_DAY)

        return self.lazy_entries
