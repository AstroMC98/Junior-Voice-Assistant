import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from knowledge_base.models.trace import TraceEvent
from knowledge_base.store.trace_store import TraceStore

_store: TraceStore | None = None


def init_tracing(store: TraceStore) -> None:
    global _store
    _store = store


@asynccontextmanager
async def trace_agent(
    agent_name: str,
    tier: int,
    input_data: dict,
    parent_trace_id: str | None = None,
    workflow_id: str | None = None,
    session_id: str | None = None,
    document_id: str | None = None,
):
    """
    Async context manager that records a TraceEvent on exit.
    Yields a dict with 'trace_id' and 'output' keys.
    Caller writes results into ctx['output'].
    """
    trace_id = str(uuid.uuid4())
    span_id = str(uuid.uuid4())
    start = datetime.utcnow()
    output_holder: dict = {}
    status = "success"
    failure_type = None
    failure_detail = None

    try:
        yield {"trace_id": trace_id, "output": output_holder}
    except Exception as exc:
        status = "failure"
        failure_type = type(exc).__name__
        failure_detail = str(exc)
        raise
    finally:
        end = datetime.utcnow()
        event = TraceEvent(
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            span_id=span_id,
            event_type="agent_call",
            agent_name=agent_name,
            workflow_id=workflow_id,
            tier=tier,
            timestamp_start=start,
            timestamp_end=end,
            duration_ms=int((end - start).total_seconds() * 1000),
            input_data=input_data,
            output_data=output_holder,
            status=status,
            failure_type=failure_type,
            failure_detail=failure_detail,
            session_id=session_id,
            document_id=document_id,
            token_count_in=None,
            token_count_out=None,
            model_id=None,
        )
        if _store is not None:
            await _store.save(event)
