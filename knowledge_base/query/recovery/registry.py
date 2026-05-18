from typing import Type
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session


class BaseRecovery:
    async def attempt(
        self,
        failure_context: dict,
        query: ProcessedQuery,
        session: Session,
    ) -> WorkflowResult:
        raise NotImplementedError


RECOVERY_REGISTRY: dict[str, list[Type[BaseRecovery]]] = {
    "ZERO_MATCHES": [],          # populated in _register_strategies()
    "AMBIGUOUS_MATCH": [],
    "MISSING_PREREQUISITE": [],
    "ENTRY_TYPE_UNSUPPORTED": [],
    "CONFIDENCE_TOO_LOW": [],
}


def _register_strategies() -> None:
    from knowledge_base.query.recovery.clarification import ClarificationRecovery
    from knowledge_base.query.recovery.confirmation import ConfirmationRecovery
    RECOVERY_REGISTRY["ZERO_MATCHES"] = [ClarificationRecovery]
    RECOVERY_REGISTRY["AMBIGUOUS_MATCH"] = [ConfirmationRecovery, ClarificationRecovery]
    RECOVERY_REGISTRY["MISSING_PREREQUISITE"] = [ClarificationRecovery]
    RECOVERY_REGISTRY["ENTRY_TYPE_UNSUPPORTED"] = [ClarificationRecovery]
    RECOVERY_REGISTRY["CONFIDENCE_TOO_LOW"] = [ClarificationRecovery]


_register_strategies()


async def attempt_recovery(
    failure_type: str,
    failure_context: dict,
    query: ProcessedQuery,
    session: Session,
) -> WorkflowResult | None:
    strategies = RECOVERY_REGISTRY.get(failure_type, [])
    for strategy_cls in strategies:
        strategy = strategy_cls()
        result = await strategy.attempt(failure_context, query, session)
        if result.success:
            return result
    return None
