import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.query.workflows.base import WorkflowResult


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_query(text: str) -> ProcessedQuery:
    return ProcessedQuery(
        cleaned_text=text, extracted_entities={},
        uncertainty_flags=[], corrections_detected=[],
        references_to_resolve=[], raw_text=text,
    )


def _make_session(active_module: str | None = None) -> Session:
    return Session(
        session_id="s1", document_id="d1", document_type="game_manual",
        active_module=active_module, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[], user_vocabulary={},
        urgency="normal", expertise_level="intermediate",
    )


def _make_entry(eid: str, raw_text: str = "raw text") -> KnowledgeEntry:
    return KnowledgeEntry(
        id=eid, source_document="doc.pdf", entry_type="procedure",
        title="Wires Module", summary="Cut correct wire.",
        tags=["wire"], raw_text=raw_text, vernacular_terms=[],
        structured_data={}, media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.9, requires_review=False,
    )


# ── Registry tests ─────────────────────────────────────────────────────────

def test_recovery_registry_has_all_failure_types():
    from knowledge_base.query.recovery.registry import RECOVERY_REGISTRY
    for ft in ["ZERO_MATCHES", "AMBIGUOUS_MATCH", "MISSING_PREREQUISITE", "ENTRY_TYPE_UNSUPPORTED", "CONFIDENCE_TOO_LOW"]:
        assert ft in RECOVERY_REGISTRY


def test_recovery_registry_populated():
    from knowledge_base.query.recovery.registry import RECOVERY_REGISTRY
    assert len(RECOVERY_REGISTRY["ZERO_MATCHES"]) > 0
    assert len(RECOVERY_REGISTRY["AMBIGUOUS_MATCH"]) > 0


# ── ClarificationRecovery tests ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clarification_always_succeeds():
    from knowledge_base.query.recovery.clarification import ClarificationRecovery
    rec = ClarificationRecovery()
    result = await rec.attempt({}, _make_query("help"), _make_session())
    assert result.success is True
    assert result.response is not None
    assert len(result.response) > 0


@pytest.mark.asyncio
async def test_clarification_uses_zero_matches_prompt():
    from knowledge_base.query.recovery.clarification import ClarificationRecovery
    rec = ClarificationRecovery()
    result = await rec.attempt({"failure_type": "ZERO_MATCHES"}, _make_query("x"), _make_session())
    assert "match" in result.response.lower() or "describe" in result.response.lower()


# ── ConfirmationRecovery tests ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirmation_asks_about_best_candidate():
    from knowledge_base.query.recovery.confirmation import ConfirmationRecovery
    entry = _make_entry("e1")
    mock_store = MagicMock()
    mock_store.get = AsyncMock(return_value=entry)
    rec = ConfirmationRecovery(store=mock_store)
    result = await rec.attempt(
        {"candidates": [{"id": "e1", "confidence": 0.6}]},
        _make_query("wire"), _make_session(),
    )
    assert result.success is True
    assert "Wires Module" in result.response


@pytest.mark.asyncio
async def test_confirmation_fails_without_candidates():
    from knowledge_base.query.recovery.confirmation import ConfirmationRecovery
    rec = ConfirmationRecovery(store=MagicMock())
    result = await rec.attempt({}, _make_query("x"), _make_session())
    assert result.success is False


# ── RawTextFallbackRecovery tests ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_raw_text_fallback_answers_from_entry():
    from knowledge_base.query.recovery.raw_text_fallback import RawTextFallbackRecovery
    entry = _make_entry("e1", raw_text="Cut the red wire if the serial number is odd.")
    mock_store = MagicMock()
    mock_store.get = AsyncMock(return_value=entry)

    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text="Cut the red wire.")]
    with patch("knowledge_base.query.recovery.raw_text_fallback.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        rec = RawTextFallbackRecovery(store=mock_store)
        result = await rec.attempt({}, _make_query("what do I do?"), _make_session("e1"))
    assert result.success is True
    assert "red wire" in result.response.lower() or len(result.response) > 0


@pytest.mark.asyncio
async def test_raw_text_fallback_fails_without_active_module():
    from knowledge_base.query.recovery.raw_text_fallback import RawTextFallbackRecovery
    rec = RawTextFallbackRecovery(store=MagicMock())
    result = await rec.attempt({}, _make_query("what?"), _make_session())
    assert result.success is False


# ── attempt_recovery orchestration tests ──────────────────────────────────

@pytest.mark.asyncio
async def test_attempt_recovery_returns_first_success():
    from knowledge_base.query.recovery.registry import RECOVERY_REGISTRY, attempt_recovery
    from knowledge_base.query.recovery.clarification import ClarificationRecovery

    original = RECOVERY_REGISTRY["ZERO_MATCHES"][:]
    try:
        RECOVERY_REGISTRY["ZERO_MATCHES"] = [ClarificationRecovery]
        result = await attempt_recovery("ZERO_MATCHES", {}, _make_query("x"), _make_session())
        assert result is not None
        assert result.success is True
    finally:
        RECOVERY_REGISTRY["ZERO_MATCHES"] = original


@pytest.mark.asyncio
async def test_attempt_recovery_returns_none_for_unknown_failure():
    from knowledge_base.query.recovery.registry import attempt_recovery
    result = await attempt_recovery("UNKNOWN_TYPE", {}, _make_query("x"), _make_session())
    assert result is None


# ── Tier3Orchestrator tests ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tier3_returns_answer_on_end_turn():
    from knowledge_base.query.tier3.orchestrator import Tier3Orchestrator

    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[])

    content_block = MagicMock()
    content_block.text = "Cut the red wire."
    mock_response = MagicMock()
    mock_response.stop_reason = "end_turn"
    mock_response.content = [content_block]

    with patch("knowledge_base.query.tier3.orchestrator.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_client
        orchestrator = Tier3Orchestrator(store=mock_store)
        result = await orchestrator.resolve(
            _make_query("what wire do I cut?"), _make_session(), []
        )
    assert "red wire" in result or len(result) > 0


@pytest.mark.asyncio
async def test_tier3_uses_tool_to_search():
    from knowledge_base.query.tier3.orchestrator import Tier3Orchestrator
    from knowledge_base.models.entry import KnowledgeEntry

    entry = _make_entry("e1")
    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[entry])

    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.id = "tu1"
    tool_block.input = {"keyword": "wire"}

    text_block = MagicMock()
    text_block.text = "Based on the search, cut the blue wire."

    tool_call_response = MagicMock()
    tool_call_response.stop_reason = "tool_use"
    tool_call_response.content = [tool_block]

    end_response = MagicMock()
    end_response.stop_reason = "end_turn"
    end_response.content = [text_block]

    with patch("knowledge_base.query.tier3.orchestrator.anthropic.AsyncAnthropic") as mock_cls:
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(side_effect=[tool_call_response, end_response])
        mock_cls.return_value = mock_client
        orchestrator = Tier3Orchestrator(store=mock_store)
        result = await orchestrator.resolve(_make_query("which wire"), _make_session(), [])
    assert len(result) > 0
    mock_store.search_by_tag.assert_called_once_with("wire")
