from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session


class DisambiguationWorkflow(BaseWorkflow):
    def __init__(self, gatherer: ContextGatherer, responder: Responder):
        self.gatherer = gatherer
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        candidate_ids = query.extracted_entities.get("candidate_ids", [])

        if not candidate_ids:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"query": query.cleaned_text},
            )

        entries = []
        for eid in candidate_ids[:3]:
            entry = await self.gatherer.gather(eid)
            if entry:
                entries.append(entry)

        response = await self.responder.respond_disambiguation(entries, session)
        return WorkflowResult(success=True, response=response, failure_type=None)
