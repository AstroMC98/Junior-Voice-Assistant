import asyncio
from knowledge_base.llm_clients import query_client_sonnet
from knowledge_base.utils.async_llm import run_llm
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.prompts.query.tier3_orchestrator import (
    MODEL, MAX_TOKENS, FALLBACK_RESPONSE, INITIAL_USER_TEMPLATE,
)


class Tier3Orchestrator:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def resolve(
        self,
        query: ProcessedQuery,
        session: Session,
        failure_trace: list[dict],
    ) -> str:
        loop = asyncio.get_event_loop()

        def search_knowledge_base(keyword: str) -> str:
            """Search the knowledge base for entries matching the keyword."""
            future = asyncio.run_coroutine_threadsafe(
                self.store.search_by_tag(keyword), loop
            )
            results = future.result(timeout=30)
            return str([e.title for e in results[:5]])

        response = await run_llm(
            query_client_sonnet.generate,
            INITIAL_USER_TEMPLATE.format(
                query=query.cleaned_text,
                failure_trace=failure_trace,
            ),
            tools=[search_knowledge_base],
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return response.text or FALLBACK_RESPONSE
