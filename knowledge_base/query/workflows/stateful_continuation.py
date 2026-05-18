from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.state_manager import StateManager
from knowledge_base.models.session import ProcessedQuery, Session


class StatefulContinuationWorkflow(BaseWorkflow):
    def __init__(self, gatherer: ContextGatherer, state_manager: StateManager):
        self.gatherer = gatherer
        self.state_manager = state_manager

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

        result = self.state_manager.advance_step(session, entry)

        if result["done"]:
            return WorkflowResult(
                success=True,
                response="All steps complete. The module should be solved.",
                failure_type=None,
            )

        return WorkflowResult(
            success=True,
            response=f"Step {result['step'] + 1}: {result['action']}",
            failure_type=None,
        )
