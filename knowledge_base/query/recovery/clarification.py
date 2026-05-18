from knowledge_base.query.recovery.registry import BaseRecovery
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session


class ClarificationRecovery(BaseRecovery):
    PROMPTS = {
        "ZERO_MATCHES": "I couldn't find a match. Could you describe what you see differently?",
        "AMBIGUOUS_MATCH": "I found several possible matches. Can you give me more details?",
        "default": "I need a bit more information. Can you describe that again?",
    }

    async def attempt(
        self,
        failure_context: dict,
        query: ProcessedQuery,
        session: Session,
    ) -> WorkflowResult:
        failure_type = failure_context.get("failure_type", "default")
        message = self.PROMPTS.get(failure_type, self.PROMPTS["default"])
        return WorkflowResult(
            success=True,
            response=message,
            failure_type=None,
            failure_context={"recovery": "clarification_asked"},
        )
