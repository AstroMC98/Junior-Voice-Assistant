# E5 — Voice I/O & Transcript Preprocessing

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 6.1, 7) before starting.

**Goal:** Implement the `Session` and `ProcessedQuery` dataclasses, Whisper transcription client, `TranscriptPreprocessor`, and `ResponseFormatter`.

**Wave:** 2 — Requires E0 (models). Parallel with E2, E3, E6.

**Tech Stack:** Python 3.11+, openai SDK (Whisper), anthropic SDK, pytest-asyncio

---

## Files to Create

- `knowledge_base/models/session.py`
- `knowledge_base/voice/__init__.py`
- `knowledge_base/voice/whisper_client.py`
- `knowledge_base/voice/formatter.py`
- `knowledge_base/query/__init__.py`
- `knowledge_base/query/preprocessor.py`
- `tests/knowledge_base/test_voice.py`

## Modify

- `requirements.txt` — add `openai`

---

## Task E5-1: Session and ProcessedQuery models

**File:** `knowledge_base/models/session.py`

- [ ] **Step 1: Write failing test**

```python
# tests/knowledge_base/test_voice.py
from knowledge_base.models.session import ProcessedQuery, Turn, Session

def test_processed_query_fields():
    q = ProcessedQuery(
        cleaned_text="cut the red wire",
        extracted_entities={"colors": ["red"], "positions": []},
        uncertainty_flags=[],
        corrections_detected=[],
        references_to_resolve=[],
        raw_text="um cut the red wire"
    )
    assert q.cleaned_text == "cut the red wire"
    assert q.extracted_entities["colors"] == ["red"]

def test_session_defaults():
    s = Session(
        session_id="s1", document_id="doc1", document_type="game_manual",
        active_module=None, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[],
        user_vocabulary={}, urgency="normal", expertise_level="intermediate"
    )
    assert s.urgency == "normal"
    assert s.active_module is None
    assert s.trace_ids == []

def test_turn_fields():
    q = ProcessedQuery(
        cleaned_text="next", extracted_entities={}, uncertainty_flags=[],
        corrections_detected=[], references_to_resolve=[], raw_text="next"
    )
    t = Turn(
        turn_number=1, raw_transcript="next",
        processed_query=q, response_speech="Moving to step 2.",
        action="advance", trace_id="t1"
    )
    assert t.turn_number == 1
    assert t.action == "advance"
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_voice.py -k "query_fields or session_defaults or turn_fields" -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/models/session.py`**

```python
from dataclasses import dataclass, field

@dataclass
class ProcessedQuery:
    cleaned_text: str
    extracted_entities: dict      # {"colors": [...], "numbers": [...], "positions": [...], "labels": [...]}
    uncertainty_flags: list[str]  # phrases expressing doubt: ["I think it's yellow"]
    corrections_detected: list[str]  # self-corrections detected
    references_to_resolve: list[str] # "the other one", "same as before"
    raw_text: str                 # original Whisper output before cleaning

@dataclass
class Turn:
    turn_number: int
    raw_transcript: str
    processed_query: ProcessedQuery
    response_speech: str
    action: str | None  # "advance", "show_image", None
    trace_id: str

@dataclass
class Session:
    session_id: str
    document_id: str
    document_type: str

    # Active context
    active_module: str | None       # currently working entry_id
    step_state: dict                # progress within a stateful module
    known_facts: dict               # serial number, battery count, etc.

    # History
    resolved_modules: list[str]     # completed module entry_ids
    turn_history: list[Turn]

    # User adaptation
    user_vocabulary: dict[str, str] # "the wide one" -> "parallel_port"
    urgency: str                    # "high", "normal", "low"
    expertise_level: str            # "beginner", "intermediate", "expert"

    # Tracing
    trace_ids: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test**

```
pytest tests/knowledge_base/test_voice.py -k "query_fields or session_defaults or turn_fields" -v
```
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/models/session.py tests/knowledge_base/test_voice.py
git commit -m "feat(E5): add Session, ProcessedQuery, Turn dataclasses"
```

---

## Task E5-2: Whisper transcription client

**File:** `knowledge_base/voice/whisper_client.py`

- [ ] **Step 1: Add failing test**

Append to `tests/knowledge_base/test_voice.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_whisper_transcribe_returns_text():
    with patch("knowledge_base.voice.whisper_client.openai_client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value="cut the red wire")
        from knowledge_base.voice.whisper_client import transcribe
        result = await transcribe(audio_bytes=b"fake_wav_data", audio_format="wav")
    assert result == "cut the red wire"

@pytest.mark.asyncio
async def test_whisper_transcribe_uses_whisper1_model():
    with patch("knowledge_base.voice.whisper_client.openai_client") as mock_client:
        mock_client.audio.transcriptions.create = AsyncMock(return_value="hello")
        from knowledge_base.voice.whisper_client import transcribe
        await transcribe(b"data", "mp3")
    call_kwargs = mock_client.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["model"] == "whisper-1"
    assert call_kwargs["response_format"] == "text"
```

- [ ] **Step 2: Create `knowledge_base/voice/__init__.py`** (empty)

- [ ] **Step 3: Create `knowledge_base/voice/whisper_client.py`**

```python
import io
from openai import AsyncOpenAI

openai_client = AsyncOpenAI()

async def transcribe(audio_bytes: bytes, audio_format: str = "wav") -> str:
    """
    Transcribes audio bytes using OpenAI Whisper.
    audio_format: "wav", "mp3", "m4a", "webm", etc.
    Returns plain text transcript.
    """
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = f"audio.{audio_format}"
    transcript = await openai_client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text"
    )
    return transcript
```

- [ ] **Step 4: Add openai to requirements.txt**

```
openai>=1.0.0
```

- [ ] **Step 5: Run tests**

```
pytest tests/knowledge_base/test_voice.py -k "whisper" -v
```
Expected: 2 tests PASS

- [ ] **Step 6: Commit**

```bash
git add knowledge_base/voice/ requirements.txt
git commit -m "feat(E5): add Whisper transcription client"
```

---

## Task E5-3: TranscriptPreprocessor

**File:** `knowledge_base/query/preprocessor.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/knowledge_base/test_voice.py`:

```python
from knowledge_base.models.session import Session

def _make_session() -> Session:
    return Session(
        session_id="s1", document_id="doc1", document_type="game_manual",
        active_module=None, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[],
        user_vocabulary={}, urgency="normal", expertise_level="intermediate"
    )

@pytest.mark.asyncio
async def test_preprocessor_removes_disfluencies():
    mock_json = '{"colors": [], "numbers": [], "positions": [], "labels": [], "uncertainty": []}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        from knowledge_base.query.preprocessor import TranscriptPreprocessor
        preprocessor = TranscriptPreprocessor()
        result = await preprocessor.process("um so like I have these uh wires", _make_session())
    assert "um" not in result.cleaned_text
    assert "uh" not in result.cleaned_text
    assert "wires" in result.cleaned_text

@pytest.mark.asyncio
async def test_preprocessor_detects_self_correction():
    mock_json = '{"colors": ["blue"], "numbers": [], "positions": [], "labels": [], "uncertainty": []}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        from knowledge_base.query.preprocessor import TranscriptPreprocessor
        preprocessor = TranscriptPreprocessor()
        result = await preprocessor.process("it's red, wait no, it's blue", _make_session())
    assert "blue" in result.corrections_detected

@pytest.mark.asyncio
async def test_preprocessor_extracts_entities():
    mock_json = '{"colors": ["red", "white"], "numbers": [3], "positions": ["last"], "labels": [], "uncertainty": []}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        from knowledge_base.query.preprocessor import TranscriptPreprocessor
        preprocessor = TranscriptPreprocessor()
        result = await preprocessor.process("I have 3 wires, the last one is red and white", _make_session())
    assert "red" in result.extracted_entities.get("colors", [])
    assert 3 in result.extracted_entities.get("numbers", [])

@pytest.mark.asyncio
async def test_preprocessor_flags_uncertainty():
    mock_json = '{"colors": ["yellow"], "numbers": [], "positions": [], "labels": [], "uncertainty": ["I think it\'s yellow"]}'
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=mock_json)]
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(return_value=mock_response)
        from knowledge_base.query.preprocessor import TranscriptPreprocessor
        preprocessor = TranscriptPreprocessor()
        result = await preprocessor.process("I think it's yellow", _make_session())
    assert len(result.uncertainty_flags) > 0
```

- [ ] **Step 2: Create `knowledge_base/query/__init__.py`** (empty)

- [ ] **Step 3: Create `knowledge_base/query/preprocessor.py`**

```python
import re
import json
import anthropic
from knowledge_base.models.session import ProcessedQuery, Session

anthropic_client = anthropic.AsyncAnthropic()

# Common speech disfluencies to strip
_DISFLUENCY_PATTERN = re.compile(
    r'\b(um+|uh+|like|so|you know|er+|hmm+|ah+|oh)\b',
    re.IGNORECASE
)

# Self-correction pattern: "X, wait/no/actually, it's Y" -> Y is the correction
_CORRECTION_PATTERN = re.compile(
    r'(?:wait|no|actually|sorry),?\s+(?:it\'?s?|its|the answer is|I mean)\s+(\w+)',
    re.IGNORECASE
)

class TranscriptPreprocessor:
    async def process(self, raw: str, session: Session) -> ProcessedQuery:
        # Step 1: Remove disfluencies
        cleaned = _DISFLUENCY_PATTERN.sub("", raw).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)

        # Step 2: Detect self-corrections
        corrections = _CORRECTION_PATTERN.findall(cleaned)

        # Step 3: Apply user vocabulary substitutions from session
        for alias, canonical in session.user_vocabulary.items():
            cleaned = re.sub(re.escape(alias), canonical, cleaned, flags=re.IGNORECASE)

        # Step 4: Entity extraction via Claude Haiku (fast, cheap)
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system="Extract entities from a voice query about following instructions. Return JSON only.",
            messages=[{
                "role": "user",
                "content": (
                    f"Query: {cleaned}\n"
                    'Return: {"colors": [...], "numbers": [...], "positions": ["top","left","last",...], '
                    '"labels": ["text labels or names mentioned"], "uncertainty": ["exact phrases expressing doubt"]}'
                )
            }]
        )
        raw_json = response.content[0].text.strip()
        if "```" in raw_json:
            parts = raw_json.split("```")
            raw_json = parts[1].lstrip("json").strip() if len(parts) > 1 else raw_json
        entities = json.loads(raw_json)
        uncertainty = entities.pop("uncertainty", [])

        return ProcessedQuery(
            cleaned_text=cleaned,
            extracted_entities=entities,
            uncertainty_flags=uncertainty,
            corrections_detected=corrections,
            references_to_resolve=[],
            raw_text=raw
        )
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_voice.py -k "preprocessor" -v
```
Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/query/preprocessor.py
git commit -m "feat(E5): add TranscriptPreprocessor with disfluency removal and entity extraction"
```

---

## Task E5-4: ResponseFormatter

**File:** `knowledge_base/voice/formatter.py`

- [ ] **Step 1: Add failing tests**

```python
from knowledge_base.voice.formatter import ResponseFormatter

def test_formatter_high_urgency_truncates():
    session = _make_session()
    session.urgency = "high"
    formatter = ResponseFormatter()
    result = formatter.format(
        answer="You need to cut the last red wire. Make sure the serial number ends in an even digit first.",
        session=session
    )
    assert result == "You need to cut the last red wire."

def test_formatter_normal_urgency_includes_recap():
    session = _make_session()
    session.urgency = "normal"
    formatter = ResponseFormatter()
    result = formatter.format(
        answer="Cut the wire.",
        session=session,
        confirm_inputs={"wires": "3 red, 1 white", "serial_last": "7"}
    )
    assert "wires" in result or "3 red" in result
    assert "Cut the wire." in result

def test_formatter_low_urgency_returns_full():
    session = _make_session()
    session.urgency = "low"
    formatter = ResponseFormatter()
    result = formatter.format(
        answer="The parallel port is the widest connector on the bomb. It has 25 pins in two rows.",
        session=session
    )
    assert "25 pins" in result

def test_formatter_high_urgency_short_answer_unchanged():
    session = _make_session()
    session.urgency = "high"
    formatter = ResponseFormatter()
    result = formatter.format(answer="Cut it.", session=session)
    assert result == "Cut it."
```

- [ ] **Step 2: Create `knowledge_base/voice/formatter.py`**

```python
from knowledge_base.models.session import Session

class ResponseFormatter:
    def format(
        self,
        answer: str,
        session: Session,
        confirm_inputs: dict | None = None
    ) -> str:
        urgency = session.urgency

        if urgency == "high":
            # Take only the first sentence for minimal, direct delivery
            sentences = [s.strip() for s in answer.split(".") if s.strip()]
            return sentences[0] + "." if sentences else answer

        elif urgency == "normal":
            parts = []
            if confirm_inputs:
                recap_parts = [f"{k}: {v}" for k, v in confirm_inputs.items()]
                parts.append(f"Got it — {', '.join(recap_parts)}.")
            parts.append(answer)
            return " ".join(parts)

        else:  # "low" — exploratory, learning mode
            return answer
```

- [ ] **Step 3: Run all E5 tests**

```
pytest tests/knowledge_base/test_voice.py -v
```
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add knowledge_base/voice/formatter.py tests/knowledge_base/test_voice.py
git commit -m "feat(E5): add ResponseFormatter with urgency-aware voice delivery"
```

---

## Verification

```
pytest tests/knowledge_base/test_voice.py -v
```
Expected: 13+ tests PASS, 0 failures.
