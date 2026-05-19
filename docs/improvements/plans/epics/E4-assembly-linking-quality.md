# E4 — Assembly, Linking & Quality + Full Pipeline

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 5.2 Phases 4–6, 5.3 Parallelization) before starting.

**Goal:** Implement `VernacularGenerator`, `ModuleAssembler`, `ReferenceLinker`, `QualityChecker`, and the full `IngestionPipeline` that wires all 6 phases together end-to-end.

**Wave:** 3 — Requires E2 (segmentation/classification) and E3 (extraction agents) to be merged first.

**Tech Stack:** Python 3.11+, asyncio, anthropic SDK, pymupdf (fitz), pytest-asyncio

---

## Files to Create

- `knowledge_base/ingestion/agents/vernacular_generator.py`
- `knowledge_base/ingestion/agents/module_assembler.py`
- `knowledge_base/ingestion/agents/reference_linker.py`
- `knowledge_base/ingestion/agents/quality_checker.py`
- `knowledge_base/ingestion/pipeline.py`
- `tests/knowledge_base/test_pipeline.py`

---

## Task E4-1: VernacularGenerator

**File:** `knowledge_base/ingestion/agents/vernacular_generator.py`

- [ ] **Step 1: Write failing test**

```python
# tests/knowledge_base/test_pipeline.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from knowledge_base.ingestion.agents.vernacular_generator import VernacularGenerator

@pytest.mark.asyncio
async def test_vernacular_generator_returns_aliases():
    mock_json = '["the wire cutting module", "cut the wires", "wire instructions", "defuse wires"]'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.vernacular_generator.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        gen = VernacularGenerator()
        terms = await gen.generate(
            title="Simple Wires Module",
            summary="Cut wires based on serial number rules",
            tags=["wires", "decision_tree"]
        )
    assert len(terms) == 4
    assert "cut the wires" in terms

@pytest.mark.asyncio
async def test_vernacular_generator_strips_fences():
    mock_text = '```json\n["term1", "term2"]\n```'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_text)]
    with patch("knowledge_base.ingestion.agents.vernacular_generator.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        gen = VernacularGenerator()
        terms = await gen.generate("T", "S", [])
    assert "term1" in terms
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_pipeline.py -k "vernacular" -v
```

- [ ] **Step 3: Create `knowledge_base/ingestion/agents/vernacular_generator.py`**

```python
import json
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

class VernacularGenerator:
    async def generate(self, title: str, summary: str, tags: list[str]) -> list[str]:
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=(
                "Generate spoken-language aliases someone might use when asking about this item. "
                "Think about how a non-expert would describe it verbally. "
                "Return ONLY a JSON array of 4-8 short alias strings."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Title: {title}\n"
                    f"Summary: {summary}\n"
                    f"Tags: {', '.join(tags)}\n"
                    "Return JSON array: [\"alias1\", \"alias2\", ...]"
                )
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
```

- [ ] **Step 4: Run, commit**

```bash
git add knowledge_base/ingestion/agents/vernacular_generator.py tests/knowledge_base/test_pipeline.py
git commit -m "feat(E4): add VernacularGenerator for spoken-language alias creation"
```

---

## Task E4-2: ModuleAssembler

**File:** `knowledge_base/ingestion/agents/module_assembler.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.ingestion.agents.module_assembler import ModuleAssembler
from knowledge_base.models.entry import KnowledgeEntry

def test_module_assembler_creates_entry():
    assembler = ModuleAssembler()
    entry = assembler.assemble(
        source_document="manual.pdf",
        entry_type="decision_tree",
        raw_text="If serial ends in even, cut the wire.",
        structured_data={
            "conditions": ["serial ends in even"],
            "branches": [{"condition": "yes", "action": "cut"}],
            "outcomes": ["cut", "dont_cut"],
            "default": "dont_cut"
        },
        image_results=[],
        ingestion_trace_id="trace_001",
        confidence_score=0.88
    )
    assert isinstance(entry, KnowledgeEntry)
    assert entry.entry_type == "decision_tree"
    assert entry.source_document == "manual.pdf"
    assert entry.confidence_score == 0.88
    assert entry.requires_review is False  # 0.88 >= 0.7 threshold
    assert entry.id  # non-empty UUID

def test_module_assembler_flags_low_confidence_for_review():
    assembler = ModuleAssembler()
    entry = assembler.assemble(
        source_document="doc.pdf", entry_type="narrative",
        raw_text="some text", structured_data={},
        image_results=[], ingestion_trace_id="t1", confidence_score=0.55
    )
    assert entry.requires_review is True

def test_module_assembler_attaches_media_blobs():
    from knowledge_base.models.entry import MediaBlob
    assembler = ModuleAssembler()
    image_results = [{
        "blob_id": "b1",
        "role": "diagram",
        "data": b"png_data",
        "descriptions": {"technical": "A Venn diagram"},
        "source_page": 3,
        "bounding_box": (10, 20, 300, 200)
    }]
    entry = assembler.assemble(
        "doc.pdf", "venn_logic", "raw", {}, image_results, "t1", 0.85
    )
    assert len(entry.media) == 1
    assert entry.media[0].blob_id == "b1"
    assert entry.media[0].role == "diagram"
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/module_assembler.py`**

```python
import uuid
from knowledge_base.models.entry import KnowledgeEntry, MediaBlob

REVIEW_THRESHOLD = 0.70

class ModuleAssembler:
    def assemble(
        self,
        source_document: str,
        entry_type: str,
        raw_text: str,
        structured_data: dict,
        image_results: list[dict],
        ingestion_trace_id: str,
        confidence_score: float,
    ) -> KnowledgeEntry:
        # Derive title and summary from structured_data if available
        title = (
            structured_data.get("title")
            or structured_data.get("question")  # for FAQ type
            or raw_text[:80].strip().rstrip(".")
        )
        summary = (
            structured_data.get("summary")
            or structured_data.get("answer")  # for FAQ type
            or raw_text[:200].strip()
        )
        tags = structured_data.get("tags", [entry_type])

        media = [
            MediaBlob(
                blob_id=img.get("blob_id", str(uuid.uuid4())),
                media_type=img.get("media_type", "image/png"),
                role=img.get("role", "reference"),
                data=img.get("data", b""),
                descriptions=img.get("descriptions", {}),
                source_page=img.get("source_page", 0),
                bounding_box=tuple(img.get("bounding_box", (0, 0, 0, 0)))
            )
            for img in image_results
        ]

        return KnowledgeEntry(
            id=str(uuid.uuid4()),
            source_document=source_document,
            entry_type=entry_type,
            title=title,
            summary=summary,
            tags=tags,
            raw_text=raw_text,
            vernacular_terms=[],  # populated by VernacularGenerator after assembly
            structured_data=structured_data,
            media=media,
            references=[],
            referenced_by=[],
            ingestion_trace_id=ingestion_trace_id,
            confidence_score=confidence_score,
            requires_review=confidence_score < REVIEW_THRESHOLD
        )
```

- [ ] **Step 3: Run, commit**

```
pytest tests/knowledge_base/test_pipeline.py -k "assembler" -v
```

```bash
git add knowledge_base/ingestion/agents/module_assembler.py
git commit -m "feat(E4): add ModuleAssembler that combines text and image extractions into KnowledgeEntry"
```

---

## Task E4-3: ReferenceLinker

**File:** `knowledge_base/ingestion/agents/reference_linker.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.ingestion.agents.reference_linker import ReferenceLinker
from knowledge_base.models.entry import KnowledgeEntry

def _make_bare_entry(id: str, tags: list[str]) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=id, source_document="d.pdf", entry_type="procedure",
        title=f"T{id}", summary="S", tags=tags, raw_text="r",
        vernacular_terms=[], structured_data={}, media=[],
        references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.9, requires_review=False
    )

def test_reference_linker_builds_cross_references():
    entries = [
        _make_bare_entry("e1", ["wire", "red"]),
        _make_bare_entry("e2", ["wire", "blue"]),
        _make_bare_entry("e3", ["battery"]),
    ]
    linker = ReferenceLinker()
    linked = linker.link(entries)
    e1 = next(e for e in linked if e.id == "e1")
    e2 = next(e for e in linked if e.id == "e2")
    e3 = next(e for e in linked if e.id == "e3")
    # e1 and e2 share "wire" tag — should reference each other
    assert "e2" in e1.references
    assert "e1" in e2.references
    # e3 shares no tags — no references
    assert e3.references == []

def test_reference_linker_populates_referenced_by():
    entries = [
        _make_bare_entry("e1", ["bomb", "timer"]),
        _make_bare_entry("e2", ["bomb"]),
    ]
    linker = ReferenceLinker()
    linked = linker.link(entries)
    e1 = next(e for e in linked if e.id == "e1")
    e2 = next(e for e in linked if e.id == "e2")
    assert "e2" in e1.referenced_by or "e1" in e2.referenced_by

def test_reference_linker_no_self_reference():
    entries = [_make_bare_entry("e1", ["wire"])]
    linker = ReferenceLinker()
    linked = linker.link(entries)
    assert "e1" not in linked[0].references
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/reference_linker.py`**

```python
from knowledge_base.models.entry import KnowledgeEntry

class ReferenceLinker:
    def link(self, entries: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        """
        Builds bidirectional reference graph based on shared tags.
        No LLM calls — pure graph operation on metadata.
        """
        # Build tag -> list of entry_ids index
        tag_index: dict[str, list[str]] = {}
        for entry in entries:
            for tag in entry.tags:
                tag_index.setdefault(tag, []).append(entry.id)

        id_to_entry = {e.id: e for e in entries}

        # Populate forward references
        for entry in entries:
            refs: set[str] = set()
            for tag in entry.tags:
                for eid in tag_index.get(tag, []):
                    if eid != entry.id:
                        refs.add(eid)
            entry.references = list(refs)

        # Populate reverse references (referenced_by)
        for entry in entries:
            entry.referenced_by = []
        for entry in entries:
            for ref_id in entry.references:
                if ref_id in id_to_entry:
                    target = id_to_entry[ref_id]
                    if entry.id not in target.referenced_by:
                        target.referenced_by.append(entry.id)

        return entries
```

- [ ] **Step 3: Run, commit**

```bash
git add knowledge_base/ingestion/agents/reference_linker.py
git commit -m "feat(E4): add ReferenceLinker for tag-based bidirectional graph"
```

---

## Task E4-4: QualityChecker

**File:** `knowledge_base/ingestion/agents/quality_checker.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.ingestion.agents.quality_checker import QualityChecker, ValidationReport

def _make_entry_for_qc(confidence: float, title: str = "T", structured_data: dict | None = None) -> "KnowledgeEntry":
    return _make_bare_entry("e1", ["tag"]) if False else KnowledgeEntry(
        id="e1", source_document="d.pdf", entry_type="procedure",
        title=title, summary="S", tags=["t"], raw_text="r",
        vernacular_terms=[], structured_data=structured_data or {"steps": []},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=confidence, requires_review=False
    )

def test_quality_checker_passes_good_entry():
    from knowledge_base.models.entry import KnowledgeEntry
    entry = KnowledgeEntry(
        id="e1", source_document="d.pdf", entry_type="procedure",
        title="Wire Cutting", summary="Cut based on serial", tags=["wire"],
        raw_text="If serial ends in even...", vernacular_terms=["wire step"],
        structured_data={"steps": [{"order": 1, "action": "Check serial"}]},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.90, requires_review=False
    )
    checker = QualityChecker()
    report = checker.check(entry)
    assert report.passed is True
    assert report.requires_review is False
    assert len(report.issues) == 0

def test_quality_checker_flags_low_confidence():
    from knowledge_base.models.entry import KnowledgeEntry
    entry = KnowledgeEntry(
        id="e1", source_document="d.pdf", entry_type="procedure",
        title="T", summary="S", tags=["t"], raw_text="r",
        vernacular_terms=[], structured_data={"steps": []},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.55, requires_review=False
    )
    checker = QualityChecker()
    report = checker.check(entry)
    assert report.requires_review is True
    assert entry.requires_review is True  # mutated in place
    assert any("confidence" in issue for issue in report.issues)

def test_quality_checker_flags_missing_title():
    from knowledge_base.models.entry import KnowledgeEntry
    entry = KnowledgeEntry(
        id="e1", source_document="d.pdf", entry_type="procedure",
        title="", summary="S", tags=["t"], raw_text="r",
        vernacular_terms=[], structured_data={},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t", confidence_score=0.9, requires_review=False
    )
    checker = QualityChecker()
    report = checker.check(entry)
    assert report.requires_review is True
    assert any("title" in issue for issue in report.issues)
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/quality_checker.py`**

```python
from dataclasses import dataclass
from knowledge_base.models.entry import KnowledgeEntry

CONFIDENCE_THRESHOLD = 0.70

@dataclass
class ValidationReport:
    entry_id: str
    passed: bool
    issues: list[str]
    requires_review: bool

class QualityChecker:
    def check(self, entry: KnowledgeEntry) -> ValidationReport:
        issues: list[str] = []

        if not entry.title or not entry.title.strip():
            issues.append("missing title")
        if not entry.summary or not entry.summary.strip():
            issues.append("missing summary")
        if not entry.structured_data:
            issues.append("empty structured_data")
        if not entry.tags:
            issues.append("no tags — entry will not be retrievable by tag search")
        if entry.confidence_score < CONFIDENCE_THRESHOLD:
            issues.append(f"low extraction confidence: {entry.confidence_score:.2f} (threshold: {CONFIDENCE_THRESHOLD})")

        requires_review = len(issues) > 0
        entry.requires_review = requires_review  # mutate in place

        return ValidationReport(
            entry_id=entry.id,
            passed=len(issues) == 0,
            issues=issues,
            requires_review=requires_review
        )
```

- [ ] **Step 3: Run all E4 unit tests**

```
pytest tests/knowledge_base/test_pipeline.py -v
```
Expected: All unit tests PASS

- [ ] **Step 4: Commit**

```bash
git add knowledge_base/ingestion/agents/quality_checker.py
git commit -m "feat(E4): add QualityChecker with validation and requires_review flagging"
```

---

## Task E4-5: Full IngestionPipeline

**File:** `knowledge_base/ingestion/pipeline.py`

- [ ] **Step 1: Add integration test** (uses mocked agents, not real Anthropic calls)

```python
@pytest.mark.asyncio
async def test_pipeline_end_to_end_mocked(tmp_path):
    from unittest.mock import AsyncMock, MagicMock, patch
    from knowledge_base.ingestion.pipeline import ingest_document
    from knowledge_base.store.knowledge_store import KnowledgeStore
    from knowledge_base.ingestion.agents.page_segmenter import SegmentationResult

    store = KnowledgeStore(db_path=str(tmp_path / "kb.db"))
    await store.init()

    mock_seg_result = SegmentationResult(
        page_number=0,
        text_regions=[{"bbox": [0,0,595,700], "text": "Cut the red wire if serial ends in even.", "confidence": 0.92}],
        image_regions=[]
    )

    with (
        patch("knowledge_base.ingestion.pipeline.PageSegmenter") as MockSeg,
        patch("knowledge_base.ingestion.pipeline.DocumentClassifier") as MockDocClf,
        patch("knowledge_base.ingestion.pipeline.ChunkClassifier") as MockChunkClf,
        patch("knowledge_base.ingestion.pipeline.TypeSpecificExtractor") as MockExtractor,
        patch("knowledge_base.ingestion.pipeline.VernacularGenerator") as MockVernacular,
        patch("knowledge_base.ingestion.pipeline.fitz") as MockFitz,
    ):
        # Configure mocks
        MockSeg.return_value.segment = AsyncMock(return_value=mock_seg_result)
        MockDocClf.return_value.classify = AsyncMock(return_value={"document_type": "game_manual", "confidence": 0.95})
        MockChunkClf.return_value.classify = AsyncMock(return_value={"entry_type": "decision_tree", "confidence": 0.88})
        MockExtractor.return_value.extract = AsyncMock(return_value={"conditions": ["serial even"], "branches": [], "outcomes": [], "default": "dont_cut"})
        MockVernacular.return_value.generate = AsyncMock(return_value=["cut the wire", "wire step"])

        # Mock pymupdf
        mock_page = MagicMock()
        mock_page.get_pixmap.return_value.tobytes.return_value = b"fake_png"
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)
        MockFitz.open.return_value = mock_doc

        result = await ingest_document("fake.pdf", store)

    assert result["entries_created"] >= 1
    assert result["document_type"] == "game_manual"
    entries = await store.list_by_document("fake.pdf")
    assert len(entries) >= 1
```

- [ ] **Step 2: Create `knowledge_base/ingestion/pipeline.py`**

```python
import asyncio
import uuid
import fitz  # pymupdf
from knowledge_base.ingestion.phase_runner import run_phase
from knowledge_base.ingestion.agents.page_segmenter import PageSegmenter
from knowledge_base.ingestion.agents.document_classifier import DocumentClassifier
from knowledge_base.ingestion.agents.chunk_classifier import ChunkClassifier
from knowledge_base.ingestion.agents.image_classifier import ImageClassifier
from knowledge_base.ingestion.agents.type_specific_extractor import TypeSpecificExtractor
from knowledge_base.ingestion.agents.diagram_analyzer import DiagramAnalyzer
from knowledge_base.ingestion.agents.reference_image_processor import ReferenceImageProcessor
from knowledge_base.ingestion.agents.positional_analyzer import PositionalAnalyzer
from knowledge_base.ingestion.agents.vernacular_generator import VernacularGenerator
from knowledge_base.ingestion.agents.module_assembler import ModuleAssembler
from knowledge_base.ingestion.agents.reference_linker import ReferenceLinker
from knowledge_base.ingestion.agents.quality_checker import QualityChecker
from knowledge_base.store.knowledge_store import KnowledgeStore

async def ingest_document(pdf_path: str, store: KnowledgeStore) -> dict:
    trace_id = str(uuid.uuid4())

    # Render PDF pages to PNG bytes
    doc = fitz.open(pdf_path)
    pages = [doc[i].get_pixmap().tobytes("png") for i in range(len(doc))]

    # Phase 1: Segmentation (parallel per page) + DocumentClassifier (concurrent)
    segmenter = PageSegmenter()
    classifier = DocumentClassifier()
    seg_coros = [segmenter.segment(p, i) for i, p in enumerate(pages)]
    seg_results, doc_class = await asyncio.gather(
        run_phase(seg_coros),
        classifier.classify(pages[:3])
    )
    doc_type = doc_class.get("document_type", "general")

    # Collect all text chunks and image regions with page context
    all_text_chunks = [
        (region["text"], doc_type, seg.page_number)
        for seg in seg_results
        for region in seg.text_regions
        if region.get("text", "").strip()
    ]
    all_image_regions = [
        (region.get("role_hint", "decorative"), seg.page_number)
        for seg in seg_results
        for region in seg.image_regions
    ]

    # Phase 2: Classification (parallel)
    chunk_clf = ChunkClassifier()
    img_clf = ImageClassifier()
    chunk_type_coros = [chunk_clf.classify(text, bias) for text, bias, _ in all_text_chunks]
    img_role_coros = [img_clf.classify_role(hint) for hint, _ in all_image_regions]
    chunk_types, img_roles = await asyncio.gather(
        run_phase(chunk_type_coros),
        run_phase(img_role_coros)
    )

    # Phase 3: Extraction (parallel)
    extractor = TypeSpecificExtractor()
    extraction_coros = [
        extractor.extract(text, ct["entry_type"])
        for (text, _, _), ct in zip(all_text_chunks, chunk_types)
    ]
    structured_results = await run_phase(extraction_coros)

    # Phase 4: Assembly + Vernacular (parallel per section)
    assembler = ModuleAssembler()
    vernacular = VernacularGenerator()
    entries = []
    for (text, _, page_num), ct, sd in zip(all_text_chunks, chunk_types, structured_results):
        entry = assembler.assemble(
            source_document=pdf_path,
            entry_type=ct.get("entry_type", "narrative"),
            raw_text=text,
            structured_data=sd,
            image_results=[],
            ingestion_trace_id=trace_id,
            confidence_score=ct.get("confidence", 0.8)
        )
        terms = await vernacular.generate(entry.title, entry.summary, entry.tags)
        entry.vernacular_terms = terms
        entries.append(entry)

    # Phase 5: Linking (sequential) + Quality (parallel)
    linker = ReferenceLinker()
    checker = QualityChecker()
    entries = linker.link(entries)
    reports = [checker.check(e) for e in entries]

    # Phase 6: Storage
    for entry in entries:
        await store.save(entry)

    return {
        "trace_id": trace_id,
        "document_type": doc_type,
        "entries_created": len(entries),
        "requires_review": sum(1 for r in reports if r.requires_review),
        "pages_processed": len(pages)
    }
```

- [ ] **Step 3: Run all E4 tests**

```
pytest tests/knowledge_base/test_pipeline.py -v
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add knowledge_base/ingestion/pipeline.py
git commit -m "feat(E4): add full 6-phase IngestionPipeline with asyncio parallelism"
```

---

## Verification

```
pytest tests/knowledge_base/test_pipeline.py -v
```
Expected: 10+ tests PASS, 0 failures.
