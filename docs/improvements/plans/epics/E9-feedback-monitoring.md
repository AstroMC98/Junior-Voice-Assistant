# E9 — Feedback Loop & Monitoring

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 10 and 9.6) before starting.

**Goal:** Implement `FeedbackCollector` (aggregates query-time signals to drive ingestion improvement), compute monitoring metrics from the trace store, and expose a `/api/kb/metrics` endpoint.

**Wave:** 4 — Requires E7 (workflows) and E8 (recovery/Tier 3). Parallel with E8 after E7 is merged.

**Tech Stack:** Python 3.11+, FastAPI, aiosqlite, pytest-asyncio

---

## Files to Create

- `knowledge_base/feedback/__init__.py`
- `knowledge_base/feedback/collector.py`
- `knowledge_base/feedback/metrics.py`
- `tests/knowledge_base/test_feedback.py`

## Modify

- `api/index.py` — add `GET /api/kb/metrics` route

---

## Task E9-1: FeedbackCollector

**File:** `knowledge_base/feedback/collector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/knowledge_base/test_feedback.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from knowledge_base.feedback.collector import FeedbackCollector

def _make_store_with_entry(entry_id: str, vernacular_terms: list[str]):
    mock_store = MagicMock()
    mock_entry = MagicMock()
    mock_entry.id = entry_id
    mock_entry.vernacular_terms = list(vernacular_terms)
    mock_store.get = AsyncMock(return_value=mock_entry)
    mock_store.save = AsyncMock()
    return mock_store, mock_entry

@pytest.mark.asyncio
async def test_identification_failure_increments_miss_count():
    mock_ks = MagicMock()
    mock_ts = MagicMock()
    collector = FeedbackCollector(knowledge_store=mock_ks, trace_store=mock_ts)
    await collector.on_identification_failure(entry_ids_tried=["e1", "e2"])
    await collector.on_identification_failure(entry_ids_tried=["e1"])
    assert collector._miss_counts.get("e1") == 2
    assert collector._miss_counts.get("e2") == 1

@pytest.mark.asyncio
async def test_get_high_miss_entries_above_threshold():
    mock_ks = MagicMock()
    collector = FeedbackCollector(knowledge_store=mock_ks, trace_store=MagicMock())
    collector._miss_counts = {"e1": 6, "e2": 3, "e3": 5}
    high_miss = collector.get_high_miss_entries(threshold=5)
    assert "e1" in high_miss
    assert "e3" in high_miss
    assert "e2" not in high_miss

@pytest.mark.asyncio
async def test_new_user_vocabulary_adds_term_to_entry():
    mock_ks, mock_entry = _make_store_with_entry("e1", ["existing term"])
    collector = FeedbackCollector(knowledge_store=mock_ks, trace_store=MagicMock())
    await collector.on_new_user_vocabulary("the wide thing", "e1")
    assert "the wide thing" in mock_entry.vernacular_terms
    mock_ks.save.assert_called_once()

@pytest.mark.asyncio
async def test_new_user_vocabulary_skips_if_already_present():
    mock_ks, mock_entry = _make_store_with_entry("e1", ["the wide thing"])
    collector = FeedbackCollector(knowledge_store=mock_ks, trace_store=MagicMock())
    await collector.on_new_user_vocabulary("the wide thing", "e1")
    mock_ks.save.assert_not_called()

@pytest.mark.asyncio
async def test_tier3_resolution_logs_pattern():
    collector = FeedbackCollector(knowledge_store=MagicMock(), trace_store=MagicMock())
    await collector.on_tier3_resolution(
        resolution_path=["BroadenSearch", "Tier3Orchestrator"],
        query_text="the purple thing on the left"
    )
    assert len(collector._tier3_patterns) == 1
    assert collector._tier3_patterns[0]["query"] == "the purple thing on the left"

@pytest.mark.asyncio
async def test_tier3_cluster_detection_above_threshold():
    collector = FeedbackCollector(knowledge_store=MagicMock(), trace_store=MagicMock())
    # Simulate 6 queries with the same resolution path
    for _ in range(6):
        await collector.on_tier3_resolution(["BroadenSearch", "Tier3"], "some query")
    clusters = collector.get_tier3_clusters(min_size=5)
    assert len(clusters) >= 1
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_feedback.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/feedback/__init__.py`** (empty)

- [ ] **Step 4: Create `knowledge_base/feedback/collector.py`**

```python
from collections import Counter
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.store.trace_store import TraceStore

class FeedbackCollector:
    def __init__(self, knowledge_store: KnowledgeStore, trace_store: TraceStore):
        self.ks = knowledge_store
        self.ts = trace_store
        self._miss_counts: dict[str, int] = {}
        self._tier3_patterns: list[dict] = []

    async def on_identification_failure(self, entry_ids_tried: list[str]) -> None:
        """Called when IdentifierAgent fails to find a confident match."""
        for eid in entry_ids_tried:
            self._miss_counts[eid] = self._miss_counts.get(eid, 0) + 1

    async def on_new_user_vocabulary(self, term: str, resolved_entry_id: str) -> None:
        """
        Called when a user uses a phrase that eventually resolves to an entry.
        Adds the term to the entry's vernacular_terms so future queries match directly.
        """
        entry = await self.ks.get(resolved_entry_id)
        if entry is None:
            return
        if term not in entry.vernacular_terms:
            entry.vernacular_terms.append(term)
            await self.ks.save(entry)

    async def on_tier3_resolution(self, resolution_path: list[str], query_text: str) -> None:
        """
        Called when Tier 3 resolves a query. Logs the resolution path for pattern analysis.
        If a path appears frequently, it should be promoted to a Tier 1 workflow.
        """
        self._tier3_patterns.append({
            "path": resolution_path,
            "query": query_text,
            "path_key": "->".join(resolution_path)
        })

    def get_high_miss_entries(self, threshold: int = 5) -> list[str]:
        """Returns entry IDs that have been missed threshold+ times — candidates for re-enrichment."""
        return [eid for eid, count in self._miss_counts.items() if count >= threshold]

    def get_tier3_clusters(self, min_size: int = 5) -> list[dict]:
        """
        Returns resolution path clusters that appear >= min_size times.
        These are candidates for promotion to new Tier 1 workflows.
        """
        path_counts = Counter(p["path_key"] for p in self._tier3_patterns)
        large_clusters = [(path, count) for path, count in path_counts.items() if count >= min_size]
        return [
            {
                "path": path,
                "count": count,
                "sample_queries": [
                    p["query"] for p in self._tier3_patterns
                    if p["path_key"] == path
                ][:3]
            }
            for path, count in large_clusters
        ]
```

- [ ] **Step 5: Run tests**

```
pytest tests/knowledge_base/test_feedback.py -v
```
Expected: 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add knowledge_base/feedback/ tests/knowledge_base/test_feedback.py
git commit -m "feat(E9): add FeedbackCollector with miss tracking and Tier 3 pattern clustering"
```

---

## Task E9-2: Monitoring metrics

**File:** `knowledge_base/feedback/metrics.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.feedback.metrics import compute_metrics
from knowledge_base.store.trace_store import TraceStore
from knowledge_base.models.trace import TraceEvent
from datetime import datetime

def _make_trace(trace_id: str, status: str, tier: int, duration_ms: int, failure_type: str | None = None) -> TraceEvent:
    now = datetime.utcnow()
    return TraceEvent(
        trace_id=trace_id, parent_trace_id=None, span_id=f"s-{trace_id}",
        event_type="agent_call", agent_name="TestAgent", workflow_id=None, tier=tier,
        timestamp_start=now, timestamp_end=now, duration_ms=duration_ms,
        input_data={}, output_data={},
        status=status, failure_type=failure_type, failure_detail=None,
        session_id=None, document_id="doc1",
        token_count_in=100, token_count_out=50, model_id="claude-sonnet-4-6"
    )

@pytest.mark.asyncio
async def test_compute_metrics(tmp_path):
    store = TraceStore(db_path=str(tmp_path / "t.db"))
    await store.init()
    await store.save(_make_trace("t1", "success", tier=1, duration_ms=500))
    await store.save(_make_trace("t2", "failure", tier=1, duration_ms=1200, failure_type="ZERO_MATCHES"))
    await store.save(_make_trace("t3", "success", tier=2, duration_ms=3000))
    await store.save(_make_trace("t4", "failure", tier=3, duration_ms=4500, failure_type="AMBIGUOUS_MATCH"))

    metrics = await compute_metrics(store)

    assert metrics["total_failures"] == 2
    assert metrics["slow_operations_over_2s"] == 2  # t3, t4
    assert metrics["failures_by_tier"][1] == 1
    assert metrics["failures_by_tier"][3] == 1
    assert "ZERO_MATCHES" in metrics["failure_types"]
    assert metrics["failure_types"]["ZERO_MATCHES"] == 1
```

- [ ] **Step 2: Create `knowledge_base/feedback/metrics.py`**

```python
from knowledge_base.store.trace_store import TraceStore

SLOW_THRESHOLD_MS = 2000

async def compute_metrics(store: TraceStore) -> dict:
    all_failures = await store.query_failures()
    slow = await store.query_slow(threshold_ms=SLOW_THRESHOLD_MS)

    tier_counts: dict[int, int] = {}
    for event in all_failures:
        tier_counts[event.tier] = tier_counts.get(event.tier, 0) + 1

    failure_types = _count_by_field(all_failures, "failure_type")

    return {
        "total_failures": len(all_failures),
        "slow_operations_over_2s": len(slow),
        "failures_by_tier": tier_counts,
        "failure_types": failure_types,
    }

def _count_by_field(events, field: str) -> dict:
    counts: dict[str, int] = {}
    for event in events:
        val = getattr(event, field, None) or "unknown"
        counts[val] = counts.get(val, 0) + 1
    return counts
```

- [ ] **Step 3: Run test**

```
pytest tests/knowledge_base/test_feedback.py -k "compute_metrics" -v
```
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add knowledge_base/feedback/metrics.py
git commit -m "feat(E9): add compute_metrics from TraceStore"
```

---

## Task E9-3: Expose `/api/kb/metrics` endpoint

**File:** `api/index.py` (existing file — add one route)

- [ ] **Step 1: Read `api/index.py`** to understand current FastAPI app structure

- [ ] **Step 2: Add metric endpoint**

Add to `api/index.py` after existing routes:

```python
from knowledge_base.feedback.metrics import compute_metrics
from knowledge_base.store.trace_store import TraceStore

# Initialize trace store (adjust db_path to match your deployment)
_trace_store = TraceStore(db_path="traces.db")

@app.on_event("startup")
async def _init_trace_store():
    await _trace_store.init()

@app.get("/api/kb/metrics")
async def get_kb_metrics():
    """Returns monitoring metrics from the trace store."""
    return await compute_metrics(_trace_store)
```

- [ ] **Step 3: Verify route works**

```bash
uvicorn api.index:app --reload
# In another terminal:
curl http://localhost:8000/api/kb/metrics
```
Expected: JSON response with `total_failures`, `slow_operations_over_2s`, etc.

- [ ] **Step 4: Run all E9 tests**

```
pytest tests/knowledge_base/test_feedback.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add api/index.py knowledge_base/feedback/metrics.py
git commit -m "feat(E9): add /api/kb/metrics endpoint backed by TraceStore"
```

---

## Verification

```
pytest tests/knowledge_base/test_feedback.py -v
```
Expected: 7+ tests PASS, 0 failures.

Full test suite:
```
pytest tests/knowledge_base/ -v
```
Expected: All epics passing, 50+ total tests.
