from knowledge_base.llm_clients import query_client_haiku
from knowledge_base.utils.async_llm import run_llm
from knowledge_base.query.recovery.registry import BaseRecovery
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.prompts.query.raw_text_fallback import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_TEMPLATE,
)


class RawTextFallbackRecovery(BaseRecovery):
    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store

    async def attempt(
        self,
        failure_context: dict,
        query: ProcessedQuery,
        session: Session,
    ) -> WorkflowResult:
        if self.store is None or not session.active_module:
            return WorkflowResult(success=False, response=None, failure_type="NO_STORE")

        entry = await self.store.get(session.active_module)
        if entry is None or not entry.raw_text:
            return WorkflowResult(success=False, response=None, failure_type="NO_RAW_TEXT")

        response = await run_llm(
            query_client_haiku.generate,
            USER_TEMPLATE.format(raw_text=entry.raw_text[:3000], query=query.cleaned_text),
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return WorkflowResult(success=True, response=response.text.strip(), failure_type=None)
