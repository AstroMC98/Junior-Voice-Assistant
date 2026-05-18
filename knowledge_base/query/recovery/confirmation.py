from knowledge_base.query.recovery.registry import BaseRecovery
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore


class ConfirmationRecovery(BaseRecovery):
    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store

    async def attempt(
        self,
        failure_context: dict,
        query: ProcessedQuery,
        session: Session,
    ) -> WorkflowResult:
        candidates = failure_context.get("candidates", [])
        if not candidates or self.store is None:
            return WorkflowResult(success=False, response=None, failure_type="NO_CANDIDATES")

        best_id = candidates[0].get("id") if isinstance(candidates[0], dict) else getattr(candidates[0], "entry_id", None)
        if best_id is None:
            return WorkflowResult(success=False, response=None, failure_type="NO_CANDIDATES")

        entry = await self.store.get(best_id)
        name = entry.title if entry else best_id
        return WorkflowResult(
            success=True,
            response=f"I think this might be the {name}. Is that right?",
            failure_type=None,
            failure_context={"recovery": "confirmation_asked", "guessed_id": best_id},
        )
