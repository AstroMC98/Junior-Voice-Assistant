from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.store.trace_store import TraceStore


class FeedbackCollector:
    def __init__(self, knowledge_store: KnowledgeStore, trace_store: TraceStore):
        self.ks = knowledge_store
        self.ts = trace_store
        self._miss_counts: dict[str, int] = {}
        self._tier3_patterns: list[dict] = []

    async def on_identification_failure(self, entry_ids_tried: list[str]) -> None:
        for eid in entry_ids_tried:
            self._miss_counts[eid] = self._miss_counts.get(eid, 0) + 1

    async def on_new_user_vocabulary(self, term: str, resolved_entry_id: str) -> None:
        entry = await self.ks.get(resolved_entry_id)
        if entry and term not in entry.vernacular_terms:
            entry.vernacular_terms.append(term)
            await self.ks.save(entry)

    async def on_tier3_resolution(self, resolution_path: list[str], query_text: str) -> None:
        self._tier3_patterns.append({"path": resolution_path, "query": query_text})

    def get_high_miss_entries(self, threshold: int = 5) -> list[str]:
        return [eid for eid, count in self._miss_counts.items() if count >= threshold]

    def get_tier3_patterns(self) -> list[dict]:
        return list(self._tier3_patterns)
