from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session


class InstructionWorkflow(BaseWorkflow):
    def __init__(self, gatherer: ContextGatherer, responder: Responder):
        self.gatherer = gatherer
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        module_id = session.active_module
        if not module_id:
            return WorkflowResult(
                success=False, response=None,
                failure_type="MISSING_PREREQUISITE",
                failure_context={"missing": "active_module"},
            )

        entry = await self.gatherer.gather(module_id)
        if entry is None:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"module_id": module_id},
            )

        if not entry.structured_data.get("steps"):
            return WorkflowResult(
                success=False, response=None,
                failure_type="ENTRY_TYPE_UNSUPPORTED",
                failure_context={"entry_type": entry.entry_type},
            )

        response = await self.responder.respond_instruction(entry, session)
        return WorkflowResult(success=True, response=response, failure_type=None)
