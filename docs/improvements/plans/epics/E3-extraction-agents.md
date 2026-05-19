# E3 — Extraction Agents

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 5.1, 5.4) before starting. Pay close attention to Section 5.4.2 (DiagramAnalyzer) and 5.4.3 (ReferenceImageProcessor).

**Goal:** Implement the four extraction agents: `TypeSpecificExtractor`, `DiagramAnalyzer`, `ReferenceImageProcessor`, and `PositionalAnalyzer`. These are Phase 3 of the ingestion pipeline.

**Wave:** 2 — Requires E0 (models) and E1 (tracing). Parallel with E2, E5, E6.

**Tech Stack:** Python 3.11+, anthropic SDK (vision + text), pytest-asyncio

---

## Files to Create

- `knowledge_base/ingestion/agents/type_specific_extractor.py`
- `knowledge_base/ingestion/agents/diagram_analyzer.py`
- `knowledge_base/ingestion/agents/reference_image_processor.py`
- `knowledge_base/ingestion/agents/positional_analyzer.py`
- `tests/knowledge_base/test_extraction.py`

---

## Task E3-1: TypeSpecificExtractor

**File:** `knowledge_base/ingestion/agents/type_specific_extractor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/knowledge_base/test_extraction.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_base.ingestion.agents.type_specific_extractor import TypeSpecificExtractor

@pytest.mark.asyncio
async def test_extract_decision_tree():
    mock_json = '{"conditions": ["serial ends in even"], "branches": [{"condition": "yes", "action": "cut"}], "outcomes": ["cut", "dont_cut"], "default": "dont_cut"}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        extractor = TypeSpecificExtractor()
        result = await extractor.extract(
            text="If the last digit of the serial number is even, cut the wire. Otherwise, don't.",
            entry_type="decision_tree"
        )
    assert "conditions" in result
    assert "branches" in result

@pytest.mark.asyncio
async def test_extract_procedure():
    mock_json = '{"steps": [{"order": 1, "action": "Note the wire colors", "note": null}], "prerequisites": [], "warnings": ["Order matters"]}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("Step 1: note colors", "procedure")
    assert "steps" in result
    assert len(result["steps"]) == 1

@pytest.mark.asyncio
async def test_extract_strips_markdown_fences():
    mock_text = '```json\n{"steps": [], "prerequisites": [], "warnings": []}\n```'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_text)]
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("some text", "procedure")
    assert "steps" in result

@pytest.mark.asyncio
async def test_extract_reference_table():
    mock_json = '{"columns": ["Letter", "Morse"], "rows": [["A", ".-"], ["B", "-..."]], "lookup_keys": ["Letter"]}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("A = .-, B = -...", "reference_table")
    assert result["columns"] == ["Letter", "Morse"]

@pytest.mark.asyncio
async def test_extract_unknown_type_uses_generic_prompt():
    mock_json = '{"key": "value"}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.type_specific_extractor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        extractor = TypeSpecificExtractor()
        result = await extractor.extract("some text", "unknown_type")
    assert isinstance(result, dict)
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_extraction.py -k "extract" -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/ingestion/agents/type_specific_extractor.py`**

```python
import json
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

EXTRACTION_PROMPTS: dict[str, str] = {
    "decision_tree": (
        'Extract as JSON: {"conditions": ["condition text"], '
        '"branches": [{"condition": "...", "action": "..."}], '
        '"outcomes": ["outcome1", "outcome2"], "default": "default action"}'
    ),
    "procedure": (
        'Extract as JSON: {"steps": [{"order": 1, "action": "...", "note": null}], '
        '"prerequisites": ["..."], "warnings": ["..."]}'
    ),
    "reference_table": (
        'Extract as JSON: {"columns": ["col1", "col2"], '
        '"rows": [["val1", "val2"]], "lookup_keys": ["primary_key_column"]}'
    ),
    "recipe": (
        'Extract as JSON: {"ingredients": [{"item": "...", "amount": "..."}], '
        '"steps": [{"order": 1, "action": "..."}], "timing": "...", "servings": null}'
    ),
    "narrative": (
        'Extract as JSON: {"key_points": ["point1"], '
        '"entities": [{"name": "...", "type": "..."}], "context": "brief context"}'
    ),
    "visual_guide": (
        'Extract as JSON: {"visual_description": "...", '
        '"identifying_features": ["feature1"], '
        '"commonly_confused_with": {"other_item": "how to distinguish"}}'
    ),
    "positional_layout": (
        'Extract as JSON: {"coordinate_system": "grid|absolute|relative", '
        '"positions": {"label": {"x": 0, "y": 0}}, "mappings": {"position": "meaning"}}'
    ),
    "state_machine": (
        'Extract as JSON: {"states": ["state1", "state2"], '
        '"transitions": [{"from": "s1", "to": "s2", "trigger": "..."}], '
        '"current_state_indicators": ["how to tell current state"]}'
    ),
    "venn_logic": (
        'Extract as JSON: {"dimensions": ["dim1", "dim2"], '
        '"regions": [{"conditions": {"dim1": true, "dim2": false}, "action": "..."}], '
        '"action_legend": {"symbol": "full meaning"}}'
    ),
    "faq": (
        'Extract as JSON: {"question": "...", "answer": "...", '
        '"related_questions": ["q1", "q2"]}'
    ),
}

_GENERIC_PROMPT = 'Extract all key information as structured JSON.'

class TypeSpecificExtractor:
    async def extract(self, text: str, entry_type: str) -> dict:
        prompt = EXTRACTION_PROMPTS.get(entry_type, _GENERIC_PROMPT)
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=f"{prompt}\nReturn ONLY valid JSON. No explanation, no markdown.",
            messages=[{"role": "user", "content": text[:8000]}]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_extraction.py -k "extract" -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/ingestion/agents/type_specific_extractor.py tests/knowledge_base/test_extraction.py
git commit -m "feat(E3): add TypeSpecificExtractor with prompts for all 10 entry types"
```

---

## Task E3-2: DiagramAnalyzer

**File:** `knowledge_base/ingestion/agents/diagram_analyzer.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/knowledge_base/test_extraction.py`:

```python
from knowledge_base.ingestion.agents.diagram_analyzer import DiagramAnalyzer

@pytest.mark.asyncio
async def test_diagram_analyzer_venn_extraction():
    mock_json = '''{
        "type": "venn_logic",
        "dimensions": ["has_red", "has_blue", "has_star", "led_on"],
        "regions": [
            {"conditions": {"has_red": false, "has_blue": false, "has_star": false, "led_on": false}, "action": "C"},
            {"conditions": {"has_red": true, "has_blue": false, "has_star": false, "led_on": false}, "action": "S"}
        ],
        "action_legend": {"C": "Cut the wire", "S": "Cut if serial even"},
        "extraction_confidence": 0.85,
        "raw_description": "Four-set Venn diagram..."
    }'''
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.diagram_analyzer.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        analyzer = DiagramAnalyzer()
        result = await analyzer.analyze(image=b"png_bytes")
    assert result["type"] == "venn_logic"
    assert len(result["dimensions"]) == 4
    assert len(result["regions"]) == 2
    assert result["extraction_confidence"] == 0.85

@pytest.mark.asyncio
async def test_diagram_analyzer_is_high_confidence():
    analyzer = DiagramAnalyzer()
    assert analyzer.is_high_confidence({"extraction_confidence": 0.85}) is True
    assert analyzer.is_high_confidence({"extraction_confidence": 0.65}) is False
    assert analyzer.is_high_confidence({"extraction_confidence": 0.70}) is True  # exactly at threshold
    assert analyzer.is_high_confidence({}) is False  # missing key

@pytest.mark.asyncio
async def test_diagram_analyzer_strips_fences():
    mock_text = '```json\n{"type": "flowchart", "dimensions": [], "regions": [], "action_legend": {}, "extraction_confidence": 0.9, "raw_description": "x"}\n```'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_text)]
    with patch("knowledge_base.ingestion.agents.diagram_analyzer.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        analyzer = DiagramAnalyzer()
        result = await analyzer.analyze(b"img")
    assert result["type"] == "flowchart"
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/diagram_analyzer.py`**

```python
import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

class DiagramAnalyzer:
    CONFIDENCE_THRESHOLD = 0.70

    async def analyze(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system="""Analyze this logic diagram image and extract the decision logic it encodes.
Return ONLY valid JSON:
{
  "type": "venn_logic | decision_tree | flowchart | state_machine",
  "dimensions": ["dimension_name"],
  "regions": [{"conditions": {"dim_name": true_or_false}, "action": "symbol_or_text"}],
  "action_legend": {"symbol": "full meaning of the symbol"},
  "extraction_confidence": 0.0-1.0,
  "raw_description": "plain text description of what the diagram shows"
}
For Venn diagrams, enumerate ALL regions (2^N for N dimensions).
For flowcharts, list all decision nodes and their branches.""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": "Extract the complete decision logic from this diagram. Return JSON only."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)

    def is_high_confidence(self, result: dict) -> bool:
        return result.get("extraction_confidence", 0) >= self.CONFIDENCE_THRESHOLD
```

- [ ] **Step 3: Run tests, commit**

```
pytest tests/knowledge_base/test_extraction.py -k "diagram" -v
```

```bash
git add knowledge_base/ingestion/agents/diagram_analyzer.py
git commit -m "feat(E3): add DiagramAnalyzer for structured logic extraction from images"
```

---

## Task E3-3: ReferenceImageProcessor

**File:** `knowledge_base/ingestion/agents/reference_image_processor.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.ingestion.agents.reference_image_processor import ReferenceImageProcessor

@pytest.mark.asyncio
async def test_reference_image_processor_multi_level():
    mock_json = '''{
        "technical": "DB-25 parallel port, 25 pins in two rows (13/12)",
        "layperson": "wide rectangular connector with two rows of small holes",
        "distinguishing_features": [
            "widest connector type on the bomb",
            "two rows: 13 top, 12 bottom"
        ],
        "commonly_confused_with": ["serial_port", "dvi_d"],
        "differentiators": {
            "vs_serial_port": "parallel is much wider with more holes",
            "vs_dvi_d": "parallel has round holes; DVI-D has a flat rectangular pin cluster"
        }
    }'''
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.reference_image_processor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        proc = ReferenceImageProcessor()
        result = await proc.process(image=b"png_data")
    assert "technical" in result
    assert "layperson" in result
    assert "distinguishing_features" in result
    assert len(result["distinguishing_features"]) == 2
    assert "differentiators" in result
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/reference_image_processor.py`**

```python
import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

class ReferenceImageProcessor:
    async def process(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyze this reference image (a component, connector, indicator, or object someone might need to identify).
Generate multi-level descriptions to support voice queries.
Return ONLY valid JSON:
{
  "technical": "precise technical description with specs",
  "layperson": "how someone unfamiliar with the domain would describe it",
  "distinguishing_features": ["feature that makes this unique", "another feature"],
  "commonly_confused_with": ["other_item_id_or_name"],
  "differentiators": {
    "vs_[confused_item]": "how to tell them apart in plain language"
  }
}""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": "Generate multi-level descriptions for this reference item. Return JSON only."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
```

- [ ] **Step 3: Run, commit**

```bash
git add knowledge_base/ingestion/agents/reference_image_processor.py
git commit -m "feat(E3): add ReferenceImageProcessor with multi-level descriptions"
```

---

## Task E3-4: PositionalAnalyzer

**File:** `knowledge_base/ingestion/agents/positional_analyzer.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.ingestion.agents.positional_analyzer import PositionalAnalyzer

@pytest.mark.asyncio
async def test_positional_analyzer_grid():
    mock_json = '''{
        "coordinate_system": "grid",
        "positions": {
            "A1": "YES", "A2": "NO", "A3": "THEY ARE",
            "B1": "UH HUH", "B2": "FIRST", "B3": "THIS"
        },
        "mappings": {
            "top-left": "A1", "top-center": "A2"
        }
    }'''
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.ingestion.agents.positional_analyzer.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        analyzer = PositionalAnalyzer()
        result = await analyzer.analyze(image=b"grid_png")
    assert result["coordinate_system"] == "grid"
    assert "A1" in result["positions"]
    assert result["positions"]["A1"] == "YES"
```

- [ ] **Step 2: Create `knowledge_base/ingestion/agents/positional_analyzer.py`**

```python
import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

class PositionalAnalyzer:
    async def analyze(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyze this positional layout image (grid, button panel, coordinate map).
Extract the spatial relationships where position is meaningful data.
Return ONLY valid JSON:
{
  "coordinate_system": "grid | absolute | relative | named_zones",
  "positions": {
    "position_label_or_coordinate": "content or value at that position"
  },
  "mappings": {
    "descriptive_location": "position_label"
  }
}
For grids use row-column notation (A1, A2, B1...).
Enumerate ALL positions visible in the image.""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": "Extract the complete positional layout. Return JSON only."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
```

- [ ] **Step 3: Run all E3 tests**

```
pytest tests/knowledge_base/test_extraction.py -v
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add knowledge_base/ingestion/agents/positional_analyzer.py
git commit -m "feat(E3): add PositionalAnalyzer for spatial layout extraction"
```

---

## Verification

```
pytest tests/knowledge_base/test_extraction.py -v
```
Expected: 12+ tests PASS, 0 failures.
