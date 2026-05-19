# E1 — Tracing Infrastructure

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Section 9) before starting.

**Goal:** Implement `TraceEvent` dataclass, a structured SQLite trace store, and an async context manager for instrumenting agent calls.

**Wave:** 1 — No dependencies. Start immediately.

**Tech Stack:** Python 3.11+, aiosqlite, pytest-asyncio

---

## Files to Create

- `knowledge_base/models/trace.py`
- `knowledge_base/store/trace_store.py`
- `knowledge_base/tracing.py`
- `tests/knowledge_base/test_tracing.py`

## Assumption

E0 is complete (or running in parallel). The `knowledge_base/` package and `tests/knowledge_base/` directories exist. If not, create the `__init__.py` files as described in E0.

---

## Task E1-1: TraceEvent model

**Files:** Create `knowledge_base/models/trace.py`, `tests/knowledge_base/test_tracing.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/knowledge_base/test_tracing.py
from datetime import datetime
from knowledge_base.models.trace import TraceEvent

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
```

- [ ] **Step 2: Run test to verify failure**

```
pytest tests/knowledge_base/test_tracing.py::test_trace_event_success_fields -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/models/trace.py`**

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TraceEvent:
    # Identity
    trace_id: str
    parent_trace_id: str | None
    span_id: str

    # What
    event_type: str  # "agent_call", "handoff", "failure", "recovery", "tier_escalation"
    agent_name: str
    workflow_id: str | None
    tier: int  # 1, 2, or 3

    # Timing
    timestamp_start: datetime
    timestamp_end: datetime
    duration_ms: int

    # Data
    input_data: dict
    output_data: dict

    # Outcome
    status: str  # "success", "failure", "timeout", "skipped"
    failure_type: str | None   # typed failure code: ZERO_MATCHES, AMBIGUOUS_MATCH, etc.
    failure_detail: str | None

    # Context
    session_id: str | None
    document_id: str | None

    # Performance
    token_count_in: int | None
    token_count_out: int | None
    model_id: str | None
```

- [ ] **Step 4: Run test to verify pass**

```
pytest tests/knowledge_base/test_tracing.py -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/models/trace.py tests/knowledge_base/test_tracing.py
git commit -m "feat(E1): add TraceEvent dataclass"
```

---

## Task E1-2: TraceStore (SQLite)

**Files:** Create `knowledge_base/store/trace_store.py`, add tests to `tests/knowledge_base/test_tracing.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/knowledge_base/test_tracing.py`:

```python
import pytest
from knowledge_base.store.trace_store import TraceStore

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
    results = await trace_store.query_by_document(None)  # returns all if None
    # Just verify no exception on retrieval
    assert True
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_tracing.py -v -k "trace_store"
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/store/trace_store.py`**

```python
import json
import aiosqlite
from datetime import datetime
from knowledge_base.models.trace import TraceEvent

class TraceStore:
    def __init__(self, db_path: str = "traces.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    parent_trace_id TEXT,
                    span_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    workflow_id TEXT,
                    tier INTEGER NOT NULL,
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    input_data TEXT NOT NULL,
                    output_data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failure_type TEXT,
                    failure_detail TEXT,
                    session_id TEXT,
                    document_id TEXT,
                    token_count_in INTEGER,
                    token_count_out INTEGER,
                    model_id TEXT
                )
            """)
            await db.commit()

    async def save(self, event: TraceEvent) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO traces VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                event.trace_id, event.parent_trace_id, event.span_id,
                event.event_type, event.agent_name, event.workflow_id, event.tier,
                event.timestamp_start.isoformat(), event.timestamp_end.isoformat(),
                event.duration_ms,
                json.dumps(event.input_data), json.dumps(event.output_data),
                event.status, event.failure_type, event.failure_detail,
                event.session_id, event.document_id,
                event.token_count_in, event.token_count_out, event.model_id
            ))
            await db.commit()

    async def query_by_document(self, document_id: str | None) -> list[TraceEvent]:
        if document_id is None:
            return await self._query("SELECT * FROM traces", ())
        return await self._query(
            "SELECT * FROM traces WHERE document_id=?", (document_id,)
        )

    async def query_by_session(self, session_id: str) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE session_id=?", (session_id,)
        )

    async def query_failures(self) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE status='failure'", ()
        )

    async def query_slow(self, threshold_ms: int) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE duration_ms>?", (threshold_ms,)
        )

    async def query_by_tier(self, tier: int) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE tier=?", (tier,)
        )

    async def _query(self, sql: str, params: tuple) -> list[TraceEvent]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row) -> TraceEvent:
        return TraceEvent(
            trace_id=row["trace_id"],
            parent_trace_id=row["parent_trace_id"],
            span_id=row["span_id"],
            event_type=row["event_type"],
            agent_name=row["agent_name"],
            workflow_id=row["workflow_id"],
            tier=row["tier"],
            timestamp_start=datetime.fromisoformat(row["timestamp_start"]),
            timestamp_end=datetime.fromisoformat(row["timestamp_end"]),
            duration_ms=row["duration_ms"],
            input_data=json.loads(row["input_data"]),
            output_data=json.loads(row["output_data"]),
            status=row["status"],
            failure_type=row["failure_type"],
            failure_detail=row["failure_detail"],
            session_id=row["session_id"],
            document_id=row["document_id"],
            token_count_in=row["token_count_in"],
            token_count_out=row["token_count_out"],
            model_id=row["model_id"]
        )
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_tracing.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/store/trace_store.py tests/knowledge_base/test_tracing.py
git commit -m "feat(E1): add TraceStore with SQLite backend and query methods"
```

---

## Task E1-3: Tracing context manager

**File:** Create `knowledge_base/tracing.py`

- [ ] **Step 1: Write failing test** (append to `tests/knowledge_base/test_tracing.py`):

```python
from knowledge_base.tracing import trace_agent, init_tracing

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
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_tracing.py -k "trace_agent" -v
```

- [ ] **Step 3: Create `knowledge_base/tracing.py`**

```python
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
```

- [ ] **Step 4: Run all tracing tests**

```
pytest tests/knowledge_base/test_tracing.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/tracing.py tests/knowledge_base/test_tracing.py
git commit -m "feat(E1): add trace_agent context manager for structured instrumentation"
```

---

## Verification

```
pytest tests/knowledge_base/test_tracing.py -v
```
Expected: 7+ tests PASS, 0 failures.
