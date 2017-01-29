import asyncio
import logging

from aioes import Elasticsearch


logger = logging.getLogger(__name__)


class XanmelDB:
    def __init__(self, cluster_urls):
        if cluster_urls:
            self.es = Elasticsearch(cluster_urls)
        else:
            self.es = None

    async def create_index_if_not_exist(self, index, mappings):
        # TODO: check if mapping is up-to-date
        res = await self.es.indices.exists(index=index)
        if not res:
            await self.es.indices.create(index=index, body={'mappings': mappings})

    async def create_module_indices(self, module):
        if self.es is None:
            return
        tasks = []
        for index, mappings in getattr(module, 'db_indices', {}).items():
            tasks.append(self.create_index_if_not_exist(index, mappings))
        if tasks:
            await asyncio.wait(tasks)
