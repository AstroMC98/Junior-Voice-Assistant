import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.ingestion.agents.module_assembler import ModuleAssembler
from knowledge_base.ingestion.agents.reference_linker import ReferenceLinker
from knowledge_base.ingestion.agents.quality_checker import QualityChecker


# ── VernacularGenerator tests ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_vernacular_generator_returns_list():
    from knowledge_base.ingestion.agents.vernacular_generator import VernacularGenerator
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text='["cut the wire", "wires module", "wire puzzle"]')]
    with patch("knowledge_base.ingestion.agents.vernacular_generator.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        gen = VernacularGenerator()
        result = await gen.generate("Wires Module", "Defuse by cutting correct wire", ["wire", "procedure"])
    assert isinstance(result, list)
    assert len(result) >= 1


@pytest.mark.asyncio
async def test_vernacular_generator_strips_fences():
    from knowledge_base.ingestion.agents.vernacular_generator import VernacularGenerator
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text='```json\n["alias one", "alias two"]\n```')]
    with patch("knowledge_base.ingestion.agents.vernacular_generator.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_resp)
        gen = VernacularGenerator()
        result = await gen.generate("T", "S", [])
    assert result == ["alias one", "alias two"]


# ── ModuleAssembler tests ──────────────────────────────────────────────────

def test_assembler_basic():
    assembler = ModuleAssembler()
    entry = assembler.assemble(
        source_document="doc.pdf",
        entry_type="procedure",
        raw_text="Step 1: cut wire",
        structured_data={"steps": [{"order": 1, "action": "cut wire"}]},
        image_results=[],
        ingestion_trace_id="trace-1",
        confidence_score=0.9,
    )
    assert entry.source_document == "doc.pdf"
    assert entry.entry_type == "procedure"
    assert entry.confidence_score == 0.9
    assert entry.requires_review is False
    assert len(entry.media) == 0


def test_assembler_low_confidence_flags_review():
    assembler = ModuleAssembler()
    entry = assembler.assemble(
        source_document="doc.pdf", entry_type="faq",
        raw_text="Q: what?", structured_data={},
        image_results=[], ingestion_trace_id="t", confidence_score=0.5,
    )
    assert entry.requires_review is True


def test_assembler_with_image_results():
    assembler = ModuleAssembler()
    entry = assembler.assemble(
        source_document="doc.pdf", entry_type="visual_guide",
        raw_text="See diagram", structured_data={},
        image_results=[
            {"role": "diagram", "data": b"bytes", "descriptions": {"technical": "a venn"}, "source_page": 1, "bounding_box": (0, 0, 100, 100)}
        ],
        ingestion_trace_id="t", confidence_score=0.8,
    )
    assert len(entry.media) == 1
    assert entry.media[0].role == "diagram"


def test_assembler_derives_title_from_structured_data():
    assembler = ModuleAssembler()
    entry = assembler.assemble(
        source_document="doc.pdf", entry_type="faq",
        raw_text="raw", structured_data={"title": "Custom Title", "summary": "A summary"},
        image_results=[], ingestion_trace_id="t", confidence_score=0.9,
    )
    assert entry.title == "Custom Title"
    assert entry.summary == "A summary"


# ── ReferenceLinker tests ──────────────────────────────────────────────────

def _make_entry(eid: str, tags: list[str]) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=eid, source_document="doc.pdf", entry_type="procedure",
        title="T", summary="S", tags=tags, raw_text="raw",
        vernacular_terms=[], structured_data={}, media=[],
        references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.9, requires_review=False,
    )


def test_linker_connects_shared_tags():
    linker = ReferenceLinker()
    e1 = _make_entry("e1", ["wire", "red"])
    e2 = _make_entry("e2", ["wire", "blue"])
    e3 = _make_entry("e3", ["bomb"])
    linked = linker.link([e1, e2, e3])
    assert "e2" in linked[0].references
    assert "e1" in linked[1].references
    assert linked[2].references == []


def test_linker_populates_referenced_by():
    linker = ReferenceLinker()
    e1 = _make_entry("e1", ["wire"])
    e2 = _make_entry("e2", ["wire"])
    linker.link([e1, e2])
    assert "e1" in e2.referenced_by or "e2" in e1.referenced_by


def test_linker_no_self_reference():
    linker = ReferenceLinker()
    e1 = _make_entry("e1", ["wire"])
    linker.link([e1])
    assert "e1" not in e1.references


# ── QualityChecker tests ───────────────────────────────────────────────────

def test_quality_checker_passes_good_entry():
    checker = QualityChecker()
    entry = _make_entry("e1", ["wire"])
    entry.title = "Wires Module"
    entry.summary = "Defuse the bomb"
    entry.structured_data = {"steps": []}
    report = checker.check(entry)
    assert report.passed is True
    assert report.issues == []
    assert report.requires_review is False


def test_quality_checker_flags_low_confidence():
    checker = QualityChecker()
    entry = _make_entry("e1", [])
    entry.title = "T"
    entry.summary = "S"
    entry.structured_data = {"steps": []}
    entry.confidence_score = 0.5
    report = checker.check(entry)
    assert report.passed is False
    assert any("low confidence" in i for i in report.issues)
    assert entry.requires_review is True


def test_quality_checker_flags_missing_title():
    checker = QualityChecker()
    entry = _make_entry("e1", [])
    entry.title = ""
    entry.summary = "S"
    entry.structured_data = {"k": "v"}
    entry.confidence_score = 0.9
    report = checker.check(entry)
    assert "missing title" in report.issues


def test_quality_checker_flags_empty_structured_data():
    checker = QualityChecker()
    entry = _make_entry("e1", [])
    entry.title = "T"
    entry.summary = "S"
    entry.structured_data = {}
    entry.confidence_score = 0.9
    report = checker.check(entry)
    assert "empty structured_data" in report.issues
