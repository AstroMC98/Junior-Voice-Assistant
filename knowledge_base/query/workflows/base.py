from dataclasses import dataclass, field
from knowledge_base.models.session import ProcessedQuery, Session


@dataclass
class WorkflowResult:
    success: bool
    response: str | None
    failure_type: str | None  # "ZERO_MATCHES", "AMBIGUOUS_MATCH", "MISSING_PREREQUISITE", etc.
    failure_context: dict = field(default_factory=dict)


class BaseWorkflow:
    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        raise NotImplementedError
