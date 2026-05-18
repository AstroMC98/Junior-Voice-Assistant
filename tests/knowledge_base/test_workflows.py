import pytest
from unittest.mock import AsyncMock, MagicMock

from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.query.agents.identifier import Candidate
from knowledge_base.query.workflows.base import WorkflowResult


# ── Helpers ────────────────────────────────────────────────────────────────

def _make_query(text: str, entities: dict | None = None) -> ProcessedQuery:
    return ProcessedQuery(
        cleaned_text=text,
        extracted_entities=entities or {},
        uncertainty_flags=[], corrections_detected=[],
        references_to_resolve=[], raw_text=text,
    )


def _make_session(active_module: str | None = None, steps: list | None = None) -> Session:
    session = Session(
        session_id="s1", document_id="d1", document_type="game_manual",
        active_module=active_module,
        step_state={"current_step": 0} if steps else {},
        known_facts={}, resolved_modules=[],
        turn_history=[], user_vocabulary={},
        urgency="normal", expertise_level="intermediate",
    )
    return session


def _make_entry(eid: str, steps: list | None = None) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=eid, source_document="doc.pdf", entry_type="procedure",
        title="Wires Module", summary="Cut the correct wire.",
        tags=["wire"], raw_text="raw",
        vernacular_terms=["wire puzzle"],
        structured_data={"steps": steps or []},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.9, requires_review=False,
    )


# ── WorkflowResult base tests ──────────────────────────────────────────────

def test_workflow_result_success():
    r = WorkflowResult(success=True, response="Cut red.", failure_type=None)
    assert r.success is True
    assert r.failure_context == {}


def test_workflow_result_failure():
    r = WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context={"q": "x"})
    assert r.failure_type == "ZERO_MATCHES"


# ── IdentificationWorkflow tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_identification_zero_matches():
    from knowledge_base.query.workflows.identification import IdentificationWorkflow
    identifier = MagicMock()
    identifier.identify = AsyncMock(return_value=[])
    gatherer = MagicMock()
    responder = MagicMock()
    wf = IdentificationWorkflow(identifier, gatherer, responder)
    result = await wf.run(_make_query("red wire"), _make_session())
    assert result.success is False
    assert result.failure_type == "ZERO_MATCHES"


@pytest.mark.asyncio
async def test_identification_ambiguous_match():
    from knowledge_base.query.workflows.identification import IdentificationWorkflow
    identifier = MagicMock()
    identifier.identify = AsyncMock(return_value=[
        Candidate("e1", 0.6, "tag"), Candidate("e2", 0.55, "tag"),
    ])
    gatherer = MagicMock()
    responder = MagicMock()
    wf = IdentificationWorkflow(identifier, gatherer, responder)
    result = await wf.run(_make_query("something"), _make_session())
    assert result.failure_type == "AMBIGUOUS_MATCH"


@pytest.mark.asyncio
async def test_identification_success_high_confidence():
    from knowledge_base.query.workflows.identification import IdentificationWorkflow
    entry = _make_entry("e1")
    identifier = MagicMock()
    identifier.identify = AsyncMock(return_value=[Candidate("e1", 0.9, "vernacular")])
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    responder = MagicMock()
    responder.respond_identification = AsyncMock(return_value="Found wires module.")
    session = _make_session()
    wf = IdentificationWorkflow(identifier, gatherer, responder)
    result = await wf.run(_make_query("wire puzzle"), session)
    assert result.success is True
    assert result.response == "Found wires module."
    assert session.active_module == "e1"


# ── InstructionWorkflow tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_instruction_missing_active_module():
    from knowledge_base.query.workflows.instruction import InstructionWorkflow
    wf = InstructionWorkflow(MagicMock(), MagicMock())
    result = await wf.run(_make_query("how do I do this"), _make_session())
    assert result.failure_type == "MISSING_PREREQUISITE"


@pytest.mark.asyncio
async def test_instruction_success():
    from knowledge_base.query.workflows.instruction import InstructionWorkflow
    entry = _make_entry("e1", steps=[{"order": 1, "action": "Note wire colors"}])
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    responder = MagicMock()
    responder.respond_instruction = AsyncMock(return_value="Step 1: Note wire colors")
    wf = InstructionWorkflow(gatherer, responder)
    result = await wf.run(_make_query("how"), _make_session(active_module="e1"))
    assert result.success is True


@pytest.mark.asyncio
async def test_instruction_entry_type_unsupported():
    from knowledge_base.query.workflows.instruction import InstructionWorkflow
    entry = _make_entry("e1", steps=[])  # empty steps
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    wf = InstructionWorkflow(gatherer, MagicMock())
    result = await wf.run(_make_query("how"), _make_session(active_module="e1"))
    assert result.failure_type == "ENTRY_TYPE_UNSUPPORTED"


# ── LookupWorkflow tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_lookup_zero_matches():
    from knowledge_base.query.workflows.lookup import LookupWorkflow
    identifier = MagicMock()
    identifier.identify = AsyncMock(return_value=[])
    wf = LookupWorkflow(identifier, MagicMock(), MagicMock())
    result = await wf.run(_make_query("what is a serial port"), _make_session())
    assert result.failure_type == "ZERO_MATCHES"


@pytest.mark.asyncio
async def test_lookup_success():
    from knowledge_base.query.workflows.lookup import LookupWorkflow
    entry = _make_entry("e1")
    identifier = MagicMock()
    identifier.identify = AsyncMock(return_value=[Candidate("e1", 0.8, "tag")])
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    responder = MagicMock()
    responder.respond_lookup = AsyncMock(return_value="A serial port has 9 pins.")
    wf = LookupWorkflow(identifier, gatherer, responder)
    result = await wf.run(_make_query("what is a serial port"), _make_session())
    assert result.success is True
    assert "serial port" in result.response or "9 pins" in result.response


# ── DisambiguationWorkflow tests ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_disambiguation_no_candidate_ids():
    from knowledge_base.query.workflows.disambiguation import DisambiguationWorkflow
    wf = DisambiguationWorkflow(MagicMock(), MagicMock())
    result = await wf.run(_make_query("something", {}), _make_session())
    assert result.failure_type == "ZERO_MATCHES"


@pytest.mark.asyncio
async def test_disambiguation_returns_question():
    from knowledge_base.query.workflows.disambiguation import DisambiguationWorkflow
    entry = _make_entry("e1")
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    responder = MagicMock()
    responder.respond_disambiguation = AsyncMock(return_value="Did you mean: wires or keypad?")
    wf = DisambiguationWorkflow(gatherer, responder)
    result = await wf.run(
        _make_query("module", {"candidate_ids": ["e1", "e2"]}), _make_session()
    )
    assert result.success is True


# ── StatefulContinuationWorkflow tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_stateful_missing_active_module():
    from knowledge_base.query.workflows.stateful_continuation import StatefulContinuationWorkflow
    wf = StatefulContinuationWorkflow(MagicMock(), MagicMock())
    result = await wf.run(_make_query("next"), _make_session())
    assert result.failure_type == "MISSING_PREREQUISITE"


@pytest.mark.asyncio
async def test_stateful_advances_step():
    from knowledge_base.query.workflows.stateful_continuation import StatefulContinuationWorkflow
    from knowledge_base.query.agents.state_manager import StateManager
    entry = _make_entry("e1", steps=[
        {"order": 1, "action": "Note colors"},
        {"order": 2, "action": "Cut blue wire"},
    ])
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    session = _make_session(active_module="e1")
    session.step_state = {"current_step": 0}
    wf = StatefulContinuationWorkflow(gatherer, StateManager())
    result = await wf.run(_make_query("next"), session)
    assert result.success is True
    assert "Step 2" in result.response or "Cut blue wire" in result.response


@pytest.mark.asyncio
async def test_stateful_completes_when_all_steps_done():
    from knowledge_base.query.workflows.stateful_continuation import StatefulContinuationWorkflow
    from knowledge_base.query.agents.state_manager import StateManager
    entry = _make_entry("e1", steps=[{"order": 1, "action": "Cut wire"}])
    gatherer = MagicMock()
    gatherer.gather = AsyncMock(return_value=entry)
    session = _make_session(active_module="e1")
    session.step_state = {"current_step": 0}
    wf = StatefulContinuationWorkflow(gatherer, StateManager())
    result = await wf.run(_make_query("done"), session)
    assert result.success is True
    assert "complete" in result.response.lower()
