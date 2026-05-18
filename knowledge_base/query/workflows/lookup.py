from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.identifier import IdentifierAgent
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session


class LookupWorkflow(BaseWorkflow):
    def __init__(self, identifier: IdentifierAgent, gatherer: ContextGatherer, responder: Responder):
        self.identifier = identifier
        self.gatherer = gatherer
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        candidates = await self.identifier.identify(query)

        if not candidates:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"query": query.cleaned_text},
            )

        best = candidates[0]
        entry = await self.gatherer.gather(best.entry_id)
        response = await self.responder.respond_lookup(entry, query.cleaned_text, session)
        return WorkflowResult(success=True, response=response, failure_type=None)
