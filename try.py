import aiohttp
import json
import asyncio
from aiohttp.client import ClientTimeout

from aiohttp.connector import TCPConnector
from aiohttp.resolver import AsyncResolver


class KubeCli:
    def __init__(self) -> None:
        # connector = TCPConnector(resolver=AsyncResolver())
        connector = TCPConnector()
        timeout = ClientTimeout()
        # timeout = ClientTimeout(total=1)
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)

    async def list_objects(self, prefix='/api/v1', kind='namespaces'):
        url = 'http://127.0.0.1:8001/%s/%s' % (prefix, kind)
        async with self.session.get(url, chunked=True) as response:
            body = await response.read()
            item = json.loads(body)

            return item['items']

    async def watch_objects(self, prefix='/api/v1', kind='namespaces'):
        url = 'http://127.0.0.1:8001/%s/%s?watch=1' % (prefix, kind)
        async with self.session.get(url, chunked=True) as response:
            print(response)
            assert response.status == 200

            while True:
                line = await response.content.readline()
                if not line:
                    break

                try:
                    item = json.loads(line)
                except json.decoder.JSONDecodeError:
                    print("Failed to decode json:\n%s" % line)
                    return

                print(item['object']['metadata']['name'])


    async def list_all(self):
        lists = [
            # self.list_objects(kind='configmaps'),
            # self.list_objects(kind='namespaces'),
            # self.list_objects(kind='nodes'),
            # self.list_objects(kind='pods'),
            # self.list_objects(kind='secrets'),
            # self.list_objects(prefix='/apis/argoproj.io/v1alpha1', kind='applications'),
            # self.list_objects(prefix='/apis/argoproj.io/v1alpha1', kind='rollouts'),
            # self.list_objects(prefix='/apis/networking.istio.io/v1beta1', kind='destinationrules'),
            # self.list_objects(prefix='/apis/networking.istio.io/v1beta1', kind='gateways'),
            # self.list_objects(prefix='/apis/networking.istio.io/v1beta1', kind='serviceentries'),
            # self.list_objects(prefix='/apis/networking.istio.io/v1beta1', kind='sidecars'),
            # self.list_objects(prefix='/apis/networking.istio.io/v1beta1', kind='virtualservices'),
        ]
        lists = await asyncio.gather(*lists)
        for lst in lists:
            for obj in lst:
                yield obj

    async def watch(self):
        await self.watch_objects(kind='namespaces')

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.session.__aexit__(*args, **kwargs)


async def main():
    async with KubeCli() as cli:
        # async for obj in cli.list_all():
        #     print(obj['metadata']['name'])

        await cli.watch()


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
