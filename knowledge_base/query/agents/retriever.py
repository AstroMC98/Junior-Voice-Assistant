from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.store.knowledge_store import KnowledgeStore


class RetrieverAgent:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def get(self, entry_id: str) -> KnowledgeEntry | None:
        return await self.store.get(entry_id)

    async def get_many(self, entry_ids: list[str]) -> list[KnowledgeEntry]:
        results = []
        for eid in entry_ids:
            entry = await self.store.get(eid)
            if entry is not None:
                results.append(entry)
        return results

    async def search_related(self, entry: KnowledgeEntry) -> list[KnowledgeEntry]:
        related = []
        for ref_id in entry.references + entry.referenced_by:
            ref = await self.store.get(ref_id)
            if ref is not None:
                related.append(ref)
        return related
