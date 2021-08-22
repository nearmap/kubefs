import time

import dateutil.parser

from akube.async_loop import get_loop
from akube.cluster_facade import SyncClusterFacade
from akube.model.api_resource import ApiResource, NamespaceKind
from akube.model.selector import ObjectSelector
from kube.config import Context
from kubefs.fs_model import Directory, File, Payload
from kubefs.text import to_json


def mkpayload2(*, obj):
    block = to_json(obj)

    timestamp = None

    creationTimestamp = obj["metadata"].get("creationTimestamp")
    if creationTimestamp:
        timestamp = dateutil.parser.parse(creationTimestamp).timestamp()

    if timestamp is None:
        timestamp = time.time()

    payload = Payload(
        name=obj["metadata"]["name"],
        data=block.encode(),
        ctime=timestamp,
        mtime=timestamp,
    )

    return payload


class KubeClusterGenericResourceDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context, api_resource: ApiResource):
        self = cls(payload=payload)
        self.context = context
        self.facade = SyncClusterFacade(async_loop=get_loop(), context=self.context)
        self.api_resource = api_resource
        self.selector = ObjectSelector(res=self.api_resource)
        return self

    def get_entries(self):
        if not self.lazy_entries:
            items = self.facade.list_objects(selector=self.selector)

            files = []
            for item in items:
                payload = mkpayload2(obj=item)
                files.append(File(payload=payload))

            self.lazy_entries = files

        return self.lazy_entries


class KubeClusterNamespaceDir(Directory):
    @classmethod
    def create(cls, *, payload: Payload, context: Context):
        self = cls(payload=payload)
        self.context = context
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
                )
                dirs.append(dir)

            self.lazy_entries = dirs

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
                payload = Payload(name=item["metadata"]["name"])
                dir = KubeClusterNamespaceDir.create(
                    payload=payload,
                    context=self.context,
                )
                dirs.append(dir)

            self.lazy_entries = dirs

        return self.lazy_entries
