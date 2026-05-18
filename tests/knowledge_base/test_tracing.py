import pytest
from datetime import datetime
from knowledge_base.models.trace import TraceEvent
from knowledge_base.store.trace_store import TraceStore
from knowledge_base.tracing import trace_agent, init_tracing


def test_trace_event_success_fields():
    now = datetime.utcnow()
    t = TraceEvent(
        trace_id="t1", parent_trace_id=None, span_id="s1",
        event_type="agent_call", agent_name="PageSegmenter",
        workflow_id="identification", tier=1,
        timestamp_start=now, timestamp_end=now,
        duration_ms=42,
        input_data={"page": 1}, output_data={"regions": []},
        status="success", failure_type=None, failure_detail=None,
        session_id=None, document_id="doc1",
        token_count_in=100, token_count_out=50,
        model_id="claude-sonnet-4-6"
    )
    assert t.status == "success"
    assert t.tier == 1
    assert t.agent_name == "PageSegmenter"
    assert t.failure_type is None


def test_trace_event_failure_fields():
    now = datetime.utcnow()
    t = TraceEvent(
        trace_id="t2", parent_trace_id="t1", span_id="s2",
        event_type="failure", agent_name="DiagramAnalyzer",
        workflow_id=None, tier=2,
        timestamp_start=now, timestamp_end=now,
        duration_ms=1500,
        input_data={}, output_data={},
        status="failure", failure_type="CONFIDENCE_TOO_LOW",
        failure_detail="confidence=0.45 below threshold=0.7",
        session_id="sess1", document_id=None,
        token_count_in=None, token_count_out=None, model_id=None
    )
    assert t.failure_type == "CONFIDENCE_TOO_LOW"
    assert t.parent_trace_id == "t1"
    assert t.session_id == "sess1"


@pytest.fixture
async def trace_store(tmp_path):
    store = TraceStore(db_path=str(tmp_path / "traces.db"))
    await store.init()
    return store


def _make_event(trace_id: str, status: str = "success", tier: int = 1,
                session_id: str | None = None, document_id: str | None = None,
                duration_ms: int = 100, failure_type: str | None = None) -> TraceEvent:
    now = datetime.utcnow()
    return TraceEvent(
        trace_id=trace_id, parent_trace_id=None, span_id=f"s-{trace_id}",
        event_type="agent_call", agent_name="TestAgent",
        workflow_id=None, tier=tier,
        timestamp_start=now, timestamp_end=now,
        duration_ms=duration_ms,
        input_data={"x": 1}, output_data={"y": 2},
        status=status, failure_type=failure_type, failure_detail=None,
        session_id=session_id, document_id=document_id,
        token_count_in=50, token_count_out=25, model_id="claude-haiku-4-5-20251001"
    )


@pytest.mark.asyncio
async def test_save_and_query_by_document(trace_store):
    event = _make_event("t1", document_id="doc1")
    await trace_store.save(event)
    results = await trace_store.query_by_document("doc1")
    assert len(results) == 1
    assert results[0].agent_name == "TestAgent"
    assert results[0].token_count_in == 50


@pytest.mark.asyncio
async def test_query_by_session(trace_store):
    await trace_store.save(_make_event("t1", session_id="sess1"))
    await trace_store.save(_make_event("t2", session_id="sess2"))
    results = await trace_store.query_by_session("sess1")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_query_failures(trace_store):
    await trace_store.save(_make_event("t1", status="success"))
    await trace_store.save(_make_event("t2", status="failure", failure_type="ZERO_MATCHES"))
    results = await trace_store.query_failures()
    assert len(results) == 1
    assert results[0].failure_type == "ZERO_MATCHES"


@pytest.mark.asyncio
async def test_query_slow(trace_store):
    await trace_store.save(_make_event("t1", duration_ms=500))
    await trace_store.save(_make_event("t2", duration_ms=3000))
    results = await trace_store.query_slow(threshold_ms=2000)
    assert len(results) == 1
    assert results[0].trace_id == "t2"


@pytest.mark.asyncio
async def test_datetime_round_trip(trace_store):
    event = _make_event("t1")
    await trace_store.save(event)
    results = await trace_store.query_by_document(None)
    assert len(results) >= 1
    assert isinstance(results[0].timestamp_start, datetime)


@pytest.mark.asyncio
async def test_trace_agent_success(tmp_path):
    store = TraceStore(db_path=str(tmp_path / "t.db"))
    await store.init()
    init_tracing(store)

    async with trace_agent("TestAgent", tier=1, input_data={"x": 1}, document_id="doc1") as ctx:
        ctx["output"]["result"] = "ok"

    events = await store.query_by_document("doc1")
    assert len(events) == 1
    assert events[0].status == "success"
    assert events[0].output_data == {"result": "ok"}


@pytest.mark.asyncio
async def test_trace_agent_failure(tmp_path):
    store = TraceStore(db_path=str(tmp_path / "t2.db"))
    await store.init()
    init_tracing(store)

    with pytest.raises(ValueError):
        async with trace_agent("FailAgent", tier=1, input_data={}, document_id="doc2"):
            raise ValueError("boom")

    events = await store.query_failures()
    assert len(events) == 1
    assert events[0].failure_type == "ValueError"
    assert events[0].status == "failure"
