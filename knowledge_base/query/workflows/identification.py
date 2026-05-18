from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.identifier import IdentifierAgent
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session


class IdentificationWorkflow(BaseWorkflow):
    HIGH_CONFIDENCE = 0.8
    LOW_THRESHOLD = 0.4

    def __init__(self, identifier: IdentifierAgent, gatherer: ContextGatherer, responder: Responder):
        self.identifier = identifier
        self.gatherer = gatherer
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        candidates = await self.identifier.identify(query)

        if not candidates or candidates[0].confidence < self.LOW_THRESHOLD:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"query": query.cleaned_text},
            )

        above_low = [c for c in candidates if c.confidence >= self.LOW_THRESHOLD]
        has_high = any(c.confidence >= self.HIGH_CONFIDENCE for c in above_low)

        if not has_high and len(above_low) > 1:
            return WorkflowResult(
                success=False, response=None,
                failure_type="AMBIGUOUS_MATCH",
                failure_context={
                    "candidates": [
                        {"id": c.entry_id, "confidence": c.confidence}
                        for c in above_low[:3]
                    ]
                },
            )

        best = max(above_low, key=lambda c: c.confidence)
        context = await self.gatherer.gather(best.entry_id)
        response = await self.responder.respond_identification(context, session)
        session.active_module = best.entry_id

        return WorkflowResult(success=True, response=response, failure_type=None)
