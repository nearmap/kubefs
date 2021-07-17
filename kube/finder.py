import fnmatch
from typing import Any, List

from kubernetes import config
from kubernetes.client.api_client import ApiClient
from kubernetes.client.configuration import Configuration
from kubernetes.dynamic.client import DynamicClient

from kube.config import Context
from kube.listener import ObjectClass


class Finder:
    def __init__(self, context: Context) -> None:
        self.context = context

    def create_client(self):
        config.load_kube_config(
            config_file=self.context.file.filepath, context=self.context.name
        )
        configuration = Configuration.get_default_copy()
        api_client = ApiClient(configuration=configuration)
        client = DynamicClient(api_client)
        return client

    def list_all(self, object_class: ObjectClass) -> List[Any]:
        client = self.create_client()

        collection = client.resources.get(
            api_version=object_class.api_version,
            kind=object_class.kind,
        )

        lst = []
        result = collection.get()
        for item in result.items:
            dct = result._ResourceInstance__serialize(item)
            lst.append(dct)

        return lst

    def fnmatch_objects(self, name_pattern: str, lst: List[Any]) -> List[Any]:
        index = {obj["metadata"]["name"]: obj for obj in lst}
        names = sorted(index.keys())

        names = fnmatch.filter(names, name_pattern)
        matching = [index[name] for name in names]
        return matching
