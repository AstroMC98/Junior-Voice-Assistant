import asyncio
from dataclasses import dataclass
from knowledge_base.models.session import ProcessedQuery
from knowledge_base.store.knowledge_store import KnowledgeStore


@dataclass
class Candidate:
    entry_id: str
    confidence: float
    match_reason: str


class IdentifierAgent:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def identify(self, query: ProcessedQuery) -> list[Candidate]:
        tag_results, vernacular_results = await asyncio.gather(
            self._tag_search(query),
            self._vernacular_search(query),
        )
        return self._merge_and_rank(tag_results, vernacular_results)

    async def _tag_search(self, query: ProcessedQuery) -> list[Candidate]:
        all_entities = [
            str(v)
            for vals in query.extracted_entities.values()
            for v in (vals if isinstance(vals, list) else [vals])
        ]
        candidates = []
        for entity in all_entities:
            entries = await self.store.search_by_tag(entity)
            candidates.extend(
                Candidate(e.id, 0.6, f"tag:{entity}") for e in entries
            )
        return candidates

    async def _vernacular_search(self, query: ProcessedQuery) -> list[Candidate]:
        entries = await self.store.search_by_vernacular(query.cleaned_text[:100])
        return [Candidate(e.id, 0.7, "vernacular") for e in entries]

    def _merge_and_rank(self, *result_lists: list[Candidate]) -> list[Candidate]:
        seen: dict[str, Candidate] = {}
        for candidates in result_lists:
            for c in candidates:
                if c.entry_id not in seen or seen[c.entry_id].confidence < c.confidence:
                    seen[c.entry_id] = c
        return sorted(seen.values(), key=lambda c: c.confidence, reverse=True)
