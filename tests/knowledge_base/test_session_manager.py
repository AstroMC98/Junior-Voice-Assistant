import pytest
from knowledge_base.query.session_manager import SessionManager
from knowledge_base.query.agents.identifier import IdentifierAgent, Candidate
from knowledge_base.query.agents.retriever import RetrieverAgent
from knowledge_base.models.session import ProcessedQuery
from knowledge_base.models.entry import KnowledgeEntry
from unittest.mock import AsyncMock, MagicMock


# ── SessionManager tests ───────────────────────────────────────────────────

@pytest.fixture
async def session_mgr(tmp_path):
    mgr = SessionManager(db_path=str(tmp_path / "sessions.db"))
    await mgr.init()
    return mgr


@pytest.mark.asyncio
async def test_create_session(session_mgr):
    session = await session_mgr.create("doc1", "game_manual")
    assert session.document_id == "doc1"
    assert session.document_type == "game_manual"
    assert session.active_module is None
    assert session.urgency == "normal"


@pytest.mark.asyncio
async def test_save_and_get_session(session_mgr):
    session = await session_mgr.create("doc2", "recipe")
    retrieved = await session_mgr.get(session.session_id)
    assert retrieved is not None
    assert retrieved.session_id == session.session_id
    assert retrieved.document_type == "recipe"


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(session_mgr):
    result = await session_mgr.get("no-such-id")
    assert result is None


@pytest.mark.asyncio
async def test_update_module(session_mgr):
    session = await session_mgr.create("doc3", "game_manual")
    await session_mgr.update_module(session.session_id, "module-42")
    updated = await session_mgr.get(session.session_id)
    assert updated.active_module == "module-42"


@pytest.mark.asyncio
async def test_update_module_to_none(session_mgr):
    session = await session_mgr.create("doc4", "game_manual")
    await session_mgr.update_module(session.session_id, "module-1")
    await session_mgr.update_module(session.session_id, None)
    updated = await session_mgr.get(session.session_id)
    assert updated.active_module is None


# ── IdentifierAgent tests ──────────────────────────────────────────────────

def _make_query(text: str, entities: dict | None = None) -> ProcessedQuery:
    return ProcessedQuery(
        cleaned_text=text,
        extracted_entities=entities or {},
        uncertainty_flags=[], corrections_detected=[],
        references_to_resolve=[], raw_text=text,
    )


def _make_entry(eid: str, tags: list[str], vernacular: list[str]) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=eid, source_document="doc.pdf", entry_type="procedure",
        title="T", summary="S", tags=tags, raw_text="raw",
        vernacular_terms=vernacular, structured_data={}, media=[],
        references=[], referenced_by=[], ingestion_trace_id="t1",
        confidence_score=0.9, requires_review=False,
    )


@pytest.mark.asyncio
async def test_identifier_returns_candidates_from_tag_search():
    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[_make_entry("e1", ["red"], [])])
    mock_store.search_by_vernacular = AsyncMock(return_value=[])
    agent = IdentifierAgent(mock_store)
    query = _make_query("cut the red wire", {"colors": ["red"]})
    candidates = await agent.identify(query)
    assert any(c.entry_id == "e1" for c in candidates)


@pytest.mark.asyncio
async def test_identifier_merges_results_by_highest_confidence():
    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[_make_entry("e1", [], [])])
    mock_store.search_by_vernacular = AsyncMock(return_value=[_make_entry("e1", [], [])])
    agent = IdentifierAgent(mock_store)
    query = _make_query("wires module", {"labels": ["wires"]})
    candidates = await agent.identify(query)
    ids = [c.entry_id for c in candidates]
    assert ids.count("e1") == 1  # deduped


@pytest.mark.asyncio
async def test_identifier_empty_when_no_matches():
    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[])
    mock_store.search_by_vernacular = AsyncMock(return_value=[])
    agent = IdentifierAgent(mock_store)
    query = _make_query("unknown thing")
    candidates = await agent.identify(query)
    assert candidates == []


# ── RetrieverAgent tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_retriever_get_returns_entry():
    entry = _make_entry("e1", [], [])
    mock_store = MagicMock()
    mock_store.get = AsyncMock(return_value=entry)
    agent = RetrieverAgent(mock_store)
    result = await agent.get("e1")
    assert result.id == "e1"


@pytest.mark.asyncio
async def test_retriever_get_many():
    e1 = _make_entry("e1", [], [])
    e2 = _make_entry("e2", [], [])
    mock_store = MagicMock()
    mock_store.get = AsyncMock(side_effect=lambda eid: {"e1": e1, "e2": e2}.get(eid))
    agent = RetrieverAgent(mock_store)
    results = await agent.get_many(["e1", "e2", "missing"])
    assert len(results) == 2
