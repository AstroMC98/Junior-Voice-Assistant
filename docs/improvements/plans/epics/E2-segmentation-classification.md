# E2 — Document Segmentation & Classification

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 5.1–5.3, Phases 1–2) before starting.

**Goal:** Implement `PageSegmenter`, `DocumentClassifier`, `ChunkClassifier`, `ImageClassifier`, and the asyncio semaphore-bounded `phase_runner`. These are the first two phases of the ingestion pipeline.

**Wave:** 2 — Requires E0 (models) and E1 (tracing) to be merged first.

**Tech Stack:** Python 3.11+, asyncio, anthropic SDK, pymupdf (fitz), pytest-asyncio

---

## Files to Create

- `knowledge_base/ingestion/__init__.py`
- `knowledge_base/ingestion/phase_runner.py`
- `knowledge_base/ingestion/agents/__init__.py`
- `knowledge_base/ingestion/agents/page_segmenter.py`
- `knowledge_base/ingestion/agents/document_classifier.py`
- `knowledge_base/ingestion/agents/chunk_classifier.py`
- `knowledge_base/ingestion/agents/image_classifier.py`
- `tests/knowledge_base/test_segmentation.py`

## Modify

- `requirements.txt` — add `pymupdf` and `anthropic`

---

## Task E2-1: Phase runner

**File:** `knowledge_base/ingestion/phase_runner.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/knowledge_base/test_segmentation.py
import asyncio
import pytest
from knowledge_base.ingestion.phase_runner import run_phase

@pytest.mark.asyncio
async def test_run_phase_executes_all():
    results = []
    async def work(i):
        await asyncio.sleep(0)
        results.append(i)
        return i * 2
    output = await run_phase([work(i) for i in range(5)], max_concurrency=3)
    assert sorted(output) == [0, 2, 4, 6, 8]
    assert sorted(results) == [0, 1, 2, 3, 4]

@pytest.mark.asyncio
async def test_run_phase_respects_concurrency():
    active = []
    peak = []
    async def work(i):
        active.append(i)
        peak.append(len(active))
        await asyncio.sleep(0.01)
        active.remove(i)
        return i
    await run_phase([work(i) for i in range(10)], max_concurrency=3)
    assert max(peak) <= 3

@pytest.mark.asyncio
async def test_run_phase_propagates_exceptions():
    async def failing():
        raise ValueError("boom")
    with pytest.raises(ValueError, match="boom"):
        await run_phase([failing()])

@pytest.mark.asyncio
async def test_run_phase_empty_list():
    result = await run_phase([])
    assert result == []
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_segmentation.py -k "run_phase" -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create init files and `knowledge_base/ingestion/phase_runner.py`**

```python
# knowledge_base/ingestion/__init__.py  (empty)
# knowledge_base/ingestion/agents/__init__.py  (empty)
```

```python
# knowledge_base/ingestion/phase_runner.py
import asyncio
from typing import Any, Coroutine

async def run_phase(
    coros: list[Coroutine],
    max_concurrency: int = 10
) -> list[Any]:
    """
    Runs all coroutines concurrently, bounded to max_concurrency at a time.
    Preserves result order matching input order.
    Raises on first exception (fails fast).
    """
    if not coros:
        return []
    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded(coro: Coroutine) -> Any:
        async with semaphore:
            return await coro

    return await asyncio.gather(*[bounded(c) for c in coros])
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_segmentation.py -k "run_phase" -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/ingestion/ tests/knowledge_base/test_segmentation.py
git commit -m "feat(E2): add semaphore-bounded phase_runner"
```

---

## Task E2-2: PageSegmenter

**File:** `knowledge_base/ingestion/agents/page_segmenter.py`

- [ ] **Step 1: Add failing test**

Append to `tests/knowledge_base/test_segmentation.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_base.ingestion.agents.page_segmenter import PageSegmenter, SegmentationResult

@pytest.mark.asyncio
async def test_page_segmenter_returns_text_and_image_regions():
    mock_json = '{"text_regions": [{"bbox": [0,0,595,100], "text": "Cut the red wire", "confidence": 0.95}], "image_regions": [{"bbox": [0,100,595,300], "role_hint": "diagram"}]}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]

    with patch("knowledge_base.ingestion.agents.page_segmenter.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        seg = PageSegmenter()
        result = await seg.segment(page_image=b"fake_png_bytes", page_number=3)

    assert isinstance(result, SegmentationResult)
    assert result.page_number == 3
    assert len(result.text_regions) == 1
    assert result.text_regions[0]["text"] == "Cut the red wire"
    assert len(result.image_regions) == 1
    assert result.image_regions[0]["role_hint"] == "diagram"

@pytest.mark.asyncio
async def test_page_segmenter_handles_empty_page():
    mock_json = '{"text_regions": [], "image_regions": []}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.page_segmenter.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        seg = PageSegmenter()
        result = await seg.segment(b"blank", 0)
    assert result.text_regions == []
    assert result.image_regions == []
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_segmentation.py -k "segmenter" -v
```

- [ ] **Step 3: Create `knowledge_base/ingestion/agents/page_segmenter.py`**

```python
import json
import base64
from dataclasses import dataclass
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

@dataclass
class SegmentationResult:
    page_number: int
    text_regions: list[dict]   # each: {"bbox": [x,y,w,h], "text": str, "confidence": float}
    image_regions: list[dict]  # each: {"bbox": [x,y,w,h], "role_hint": str}

class PageSegmenter:
    async def segment(self, page_image: bytes, page_number: int) -> SegmentationResult:
        b64 = base64.standard_b64encode(page_image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyze this document page image. Identify all text blocks and image regions.
Return ONLY valid JSON with this exact structure:
{
  "text_regions": [
    {"bbox": [x, y, w, h], "text": "extracted text content", "confidence": 0.95}
  ],
  "image_regions": [
    {"bbox": [x, y, w, h], "role_hint": "diagram|reference|positional_layout|state_repr|decorative"}
  ]
}
bbox values are pixels from top-left corner.""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": f"Segment page {page_number}. Return JSON only, no explanation."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        return SegmentationResult(
            page_number=page_number,
            text_regions=data.get("text_regions", []),
            image_regions=data.get("image_regions", [])
        )
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_segmentation.py -k "segmenter" -v
```
Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/ingestion/agents/page_segmenter.py
git commit -m "feat(E2): add PageSegmenter with vision-based region detection"
```

---

## Task E2-3: DocumentClassifier

**File:** `knowledge_base/ingestion/agents/document_classifier.py`

- [ ] **Step 1: Add failing test**

```python
from knowledge_base.ingestion.agents.document_classifier import DocumentClassifier

@pytest.mark.asyncio
async def test_document_classifier_returns_type():
    mock_json = '{"document_type": "game_manual", "confidence": 0.92, "reasoning": "Contains module defusal instructions"}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.document_classifier.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        clf = DocumentClassifier()
        result = await clf.classify(first_pages=[b"page1_png", b"page2_png"])
    assert result["document_type"] == "game_manual"
    assert result["confidence"] == 0.92

@pytest.mark.asyncio
async def test_document_classifier_limits_to_3_pages():
    mock_json = '{"document_type": "recipe", "confidence": 0.88, "reasoning": "Contains ingredients"}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.document_classifier.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        clf = DocumentClassifier()
        # Pass 10 pages — should only send 3
        result = await clf.classify(first_pages=[b"p"] * 10)
    call_args = mock_client.messages.create.call_args
    image_blocks = [c for c in call_args.kwargs["messages"][0]["content"] if c.get("type") == "image"]
    assert len(image_blocks) == 3
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/document_classifier.py`**

```python
import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

VALID_TYPES = [
    "game_manual", "recipe", "assembly_guide",
    "reference_manual", "troubleshooting_guide", "general"
]

class DocumentClassifier:
    async def classify(self, first_pages: list[bytes]) -> dict:
        content = []
        for page in first_pages[:3]:
            b64 = base64.standard_b64encode(page).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64}
            })
        content.append({
            "type": "text",
            "text": (
                f"Classify this document. Valid types: {VALID_TYPES}.\n"
                'Return JSON only: {"document_type": "...", "confidence": 0.0-1.0, "reasoning": "brief"}'
            )
        })
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": content}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
```

- [ ] **Step 3: Run tests, commit**

```
pytest tests/knowledge_base/test_segmentation.py -k "classifier" -v
```

```bash
git add knowledge_base/ingestion/agents/document_classifier.py
git commit -m "feat(E2): add DocumentClassifier"
```

---

## Task E2-4: ChunkClassifier and ImageClassifier

**Files:** `chunk_classifier.py`, `image_classifier.py`

- [ ] **Step 1: Add tests**

```python
from knowledge_base.ingestion.agents.chunk_classifier import ChunkClassifier
from knowledge_base.ingestion.agents.image_classifier import ImageClassifier

@pytest.mark.asyncio
async def test_chunk_classifier_returns_entry_type():
    mock_json = '{"entry_type": "decision_tree", "confidence": 0.88}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.chunk_classifier.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        clf = ChunkClassifier()
        result = await clf.classify(
            text="If the last digit of serial is even, cut the red wire.",
            document_type_bias="game_manual"
        )
    assert result["entry_type"] == "decision_tree"
    assert result["confidence"] == 0.88

@pytest.mark.asyncio
async def test_image_classifier_returns_role():
    mock_json = '{"role": "logic_diagram", "confidence": 0.91}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.image_classifier.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        clf = ImageClassifier()
        result = await clf.classify_role(role_hint="diagram", image_bytes=b"png_data")
    assert result["role"] == "logic_diagram"
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/chunk_classifier.py`**

```python
import json
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

VALID_ENTRY_TYPES = [
    "decision_tree", "procedure", "reference_table", "recipe",
    "narrative", "visual_guide", "positional_layout",
    "state_machine", "venn_logic", "faq"
]

class ChunkClassifier:
    async def classify(self, text: str, document_type_bias: str) -> dict:
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            system=f"Document context: {document_type_bias}. Classify this text chunk.",
            messages=[{
                "role": "user",
                "content": (
                    f"Classify into one of {VALID_ENTRY_TYPES}.\n"
                    'Return JSON: {"entry_type": "...", "confidence": 0.0-1.0}\n\n'
                    f"{text[:3000]}"
                )
            }]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
```

- [ ] **Step 3: Create `knowledge_base/ingestion/agents/image_classifier.py`**

```python
import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

VALID_ROLES = ["logic_diagram", "reference", "positional_layout", "state_repr", "decorative"]

class ImageClassifier:
    async def classify_role(self, role_hint: str, image_bytes: bytes | None = None) -> dict:
        if image_bytes:
            b64 = base64.standard_b64encode(image_bytes).decode()
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": f"Hint from segmenter: {role_hint}. Classify this image role from {VALID_ROLES}. Return JSON: {{\"role\": \"...\", \"confidence\": 0.0-1.0}}"}
            ]
        else:
            # Hint-only (no image bytes available)
            content = f"Role hint: {role_hint}. Map to one of {VALID_ROLES}. Return JSON: {{\"role\": \"...\", \"confidence\": 0.85}}"

        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": content}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
```

- [ ] **Step 4: Run all E2 tests**

```
pytest tests/knowledge_base/test_segmentation.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/ingestion/agents/
git commit -m "feat(E2): add ChunkClassifier and ImageClassifier"
```

---

## Verification

```
pytest tests/knowledge_base/test_segmentation.py -v
```
Expected: 10+ tests PASS, 0 failures.

`★ Insight ─────────────────────────────────────`
Using `claude-haiku-4-5-20251001` for ChunkClassifier and ImageClassifier (lightweight classification) vs `claude-sonnet-4-6` for PageSegmenter (complex vision layout analysis) cuts cost ~10x per ingestion run. The design routes each agent to the cheapest model that can reliably do the job.
`─────────────────────────────────────────────────`
