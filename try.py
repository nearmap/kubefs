import aiohttp
import asyncio


class KubeCli:
    def __init__(self) -> None:
        pass

    async def list_objects(self, kind='namespaces'):
        url = 'http://127.0.0.1:8001/api/v1/%s' % kind
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                js = await response.json()
                # import ipdb as pdb; pdb.set_trace() # BREAKPOINT
                items = js['items']

                for item in items:
                    item['apiVersion'] = js['apiVersion']
                    item['kind'] = js['kind'].replace('List', '')

                return items

    async def list_all(self):
        nss = self.list_objects(kind='namespaces')
        pods = self.list_objects(kind='pods')
        lists = [pods, nss]
        lists = await asyncio.gather(*lists)
        for lst in lists:
            for obj in lst:
                yield obj


async def main():
    cli = KubeCli()
    # objs = await cli.list_all()
    async for obj in cli.list_all():
        print(obj['kind'], obj['metadata']['name'])


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
