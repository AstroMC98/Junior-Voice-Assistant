from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.store.knowledge_store import KnowledgeStore


class ContextGatherer:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def gather(self, entry_id: str) -> KnowledgeEntry | None:
        return await self.store.get(entry_id)
