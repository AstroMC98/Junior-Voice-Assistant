import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from knowledge_base.feedback.collector import FeedbackCollector
from knowledge_base.feedback.metrics import compute_metrics, _count_by
from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.models.trace import TraceEvent


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_entry(eid: str, vernacular: list[str] | None = None) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=eid, source_document="doc.pdf", entry_type="procedure",
        title="T", summary="S", tags=[], raw_text="raw",
        vernacular_terms=vernacular or [],
        structured_data={}, media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.9, requires_review=False,
    )


def _make_trace(status: str = "success", tier: int = 1, duration_ms: int = 100, failure_type: str | None = None) -> TraceEvent:
    now = datetime.utcnow()
    return TraceEvent(
        trace_id="t1", parent_trace_id=None, span_id="s1",
        event_type="agent_call", agent_name="TestAgent",
        workflow_id=None, tier=tier,
        timestamp_start=now, timestamp_end=now,
        duration_ms=duration_ms,
        input_data={}, output_data={},
        status=status, failure_type=failure_type, failure_detail=None,
        session_id=None, document_id="doc1",
        token_count_in=None, token_count_out=None, model_id=None,
    )


# ── FeedbackCollector tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_on_identification_failure_increments_count():
    mock_ks = MagicMock()
    mock_ts = MagicMock()
    collector = FeedbackCollector(mock_ks, mock_ts)
    await collector.on_identification_failure(["e1", "e2"])
    await collector.on_identification_failure(["e1"])
    assert collector._miss_counts["e1"] == 2
    assert collector._miss_counts["e2"] == 1


@pytest.mark.asyncio
async def test_get_high_miss_entries_threshold():
    mock_ks = MagicMock()
    mock_ts = MagicMock()
    collector = FeedbackCollector(mock_ks, mock_ts)
    collector._miss_counts = {"e1": 5, "e2": 3, "e3": 7}
    high = collector.get_high_miss_entries(threshold=5)
    assert "e1" in high
    assert "e3" in high
    assert "e2" not in high


@pytest.mark.asyncio
async def test_on_new_vocabulary_updates_entry():
    entry = _make_entry("e1", vernacular=["wire puzzle"])
    mock_ks = MagicMock()
    mock_ks.get = AsyncMock(return_value=entry)
    mock_ks.save = AsyncMock()
    collector = FeedbackCollector(mock_ks, MagicMock())
    await collector.on_new_user_vocabulary("bomb wire thing", "e1")
    mock_ks.save.assert_called_once()
    assert "bomb wire thing" in entry.vernacular_terms


@pytest.mark.asyncio
async def test_on_new_vocabulary_skips_duplicate():
    entry = _make_entry("e1", vernacular=["wire puzzle"])
    mock_ks = MagicMock()
    mock_ks.get = AsyncMock(return_value=entry)
    mock_ks.save = AsyncMock()
    collector = FeedbackCollector(mock_ks, MagicMock())
    await collector.on_new_user_vocabulary("wire puzzle", "e1")
    mock_ks.save.assert_not_called()


@pytest.mark.asyncio
async def test_on_tier3_resolution_records_pattern():
    collector = FeedbackCollector(MagicMock(), MagicMock())
    await collector.on_tier3_resolution(["ZERO_MATCHES", "AMBIGUOUS"], "cut wire")
    patterns = collector.get_tier3_patterns()
    assert len(patterns) == 1
    assert patterns[0]["query"] == "cut wire"


# ── Metrics tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_metrics_empty_store():
    mock_store = MagicMock()
    mock_store.query_failures = AsyncMock(return_value=[])
    mock_store.query_slow = AsyncMock(return_value=[])
    result = await compute_metrics(mock_store)
    assert result["total_failures"] == 0
    assert result["slow_operations_over_2s"] == 0
    assert result["failures_by_tier"] == {}
    assert result["failure_types"] == {}


@pytest.mark.asyncio
async def test_compute_metrics_counts_failures():
    t1 = _make_trace("failure", tier=1, failure_type="ZERO_MATCHES")
    t2 = _make_trace("failure", tier=2, failure_type="AMBIGUOUS_MATCH")
    t3 = _make_trace("failure", tier=1, failure_type="ZERO_MATCHES")
    mock_store = MagicMock()
    mock_store.query_failures = AsyncMock(return_value=[t1, t2, t3])
    mock_store.query_slow = AsyncMock(return_value=[])
    result = await compute_metrics(mock_store)
    assert result["total_failures"] == 3
    assert result["failures_by_tier"][1] == 2
    assert result["failures_by_tier"][2] == 1
    assert result["failure_types"]["ZERO_MATCHES"] == 2


@pytest.mark.asyncio
async def test_compute_metrics_counts_slow():
    slow = _make_trace("success", duration_ms=3000)
    mock_store = MagicMock()
    mock_store.query_failures = AsyncMock(return_value=[])
    mock_store.query_slow = AsyncMock(return_value=[slow])
    result = await compute_metrics(mock_store)
    assert result["slow_operations_over_2s"] == 1


def test_count_by_field():
    t1 = _make_trace("failure", failure_type="ZERO_MATCHES")
    t2 = _make_trace("failure", failure_type="ZERO_MATCHES")
    t3 = _make_trace("failure", failure_type="AMBIGUOUS_MATCH")
    result = _count_by([t1, t2, t3], "failure_type")
    assert result["ZERO_MATCHES"] == 2
    assert result["AMBIGUOUS_MATCH"] == 1
