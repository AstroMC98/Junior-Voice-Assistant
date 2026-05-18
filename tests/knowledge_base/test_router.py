import pytest
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.query.router import Router


def _make_query(text: str, entities: dict | None = None) -> ProcessedQuery:
    return ProcessedQuery(
        cleaned_text=text,
        extracted_entities=entities or {},
        uncertainty_flags=[],
        corrections_detected=[],
        references_to_resolve=[],
        raw_text=text,
    )


def _make_session(active_module: str | None = None) -> Session:
    return Session(
        session_id="s1", document_id="d1", document_type="game_manual",
        active_module=active_module,
        step_state={}, known_facts={}, resolved_modules=[],
        turn_history=[], user_vocabulary={},
        urgency="normal", expertise_level="intermediate",
    )


def test_router_identification_with_color_entities():
    router = Router()
    query = _make_query("cut the red wire", {"colors": ["red"], "positions": []})
    workflow, ctx = router.classify(query, _make_session(), "game_manual")
    assert workflow == "identification"


def test_router_stateful_continuation_next():
    router = Router()
    query = _make_query("what's next")
    workflow, ctx = router.classify(query, _make_session("module-1"), "game_manual")
    assert workflow == "stateful_continuation"
    assert ctx["module_id"] == "module-1"


def test_router_stateful_continuation_done():
    router = Router()
    query = _make_query("done")
    workflow, ctx = router.classify(query, _make_session("module-1"), "game_manual")
    assert workflow == "stateful_continuation"


def test_router_instruction_with_active_module():
    router = Router()
    query = _make_query("how do I defuse this")
    workflow, ctx = router.classify(query, _make_session("module-1"), "game_manual")
    assert workflow == "instruction"
    assert ctx["module_id"] == "module-1"


def test_router_lookup_what_is():
    router = Router()
    query = _make_query("what is a parallel port")
    workflow, ctx = router.classify(query, _make_session(), "game_manual")
    assert workflow == "lookup"


def test_router_returns_none_for_ambiguous():
    router = Router()
    query = _make_query("help")
    workflow, ctx = router.classify(query, _make_session(), "game_manual")
    assert workflow is None


def test_router_no_identification_without_entities():
    router = Router()
    query = _make_query("cut something", {"colors": [], "positions": []})
    workflow, ctx = router.classify(query, _make_session(), "game_manual")
    assert workflow is None
