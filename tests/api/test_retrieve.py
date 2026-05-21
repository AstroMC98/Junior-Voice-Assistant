import pytest
from api.models import Guide, Step
from api.retrieve import build_guide_context

GUIDE = Guide(
    id="g1",
    title="Bake Bread",
    source="pdf",
    steps=[
        Step(index=0, title="Mix", content="Mix flour and water"),
        Step(index=1, title="Knead", content="Knead for 10 minutes"),
    ],
    fork_of=None,
    created_at=1000000,
)


def test_build_guide_context_includes_guide_title():
    result = build_guide_context(GUIDE, 0)
    assert "Bake Bread" in result


def test_build_guide_context_includes_current_step_position():
    result = build_guide_context(GUIDE, 0)
    assert "Step 1 of 2" in result


def test_build_guide_context_includes_current_step_content():
    result = build_guide_context(GUIDE, 0)
    assert "Mix flour and water" in result
    assert "Mix" in result


def test_build_guide_context_includes_all_steps_summary():
    result = build_guide_context(GUIDE, 0)
    assert "Step 1: Mix — Mix flour and water" in result
    assert "Step 2: Knead — Knead for 10 minutes" in result


def test_build_guide_context_second_step_is_current():
    result = build_guide_context(GUIDE, 1)
    assert "Step 2 of 2" in result
    assert "Knead for 10 minutes" in result
