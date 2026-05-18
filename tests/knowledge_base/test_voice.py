import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from knowledge_base.models.session import ProcessedQuery, Turn, Session


# ── Session model tests ────────────────────────────────────────────────────

def test_processed_query_fields():
    pq = ProcessedQuery(
        cleaned_text="cut the red wire",
        extracted_entities={"colors": ["red"], "positions": []},
        uncertainty_flags=[],
        corrections_detected=[],
        references_to_resolve=[],
        raw_text="um cut the red wire",
    )
    assert pq.cleaned_text == "cut the red wire"
    assert pq.extracted_entities["colors"] == ["red"]
    assert pq.raw_text == "um cut the red wire"


def test_session_fields():
    s = Session(
        session_id="s1",
        document_id="doc1",
        document_type="game_manual",
        active_module=None,
        step_state={},
        known_facts={},
        resolved_modules=[],
        turn_history=[],
        user_vocabulary={},
        urgency="normal",
        expertise_level="intermediate",
    )
    assert s.session_id == "s1"
    assert s.trace_ids == []


def test_session_trace_ids_default_empty():
    s = Session(
        session_id="s2", document_id="d", document_type="t",
        active_module=None, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[], user_vocabulary={},
        urgency="high", expertise_level="beginner",
    )
    assert isinstance(s.trace_ids, list)
    assert len(s.trace_ids) == 0


def test_turn_fields():
    pq = ProcessedQuery("text", {}, [], [], [], "raw")
    t = Turn(
        turn_number=1,
        raw_transcript="raw",
        processed_query=pq,
        response_speech="response",
        action="cut_wire",
        trace_id="t1",
    )
    assert t.turn_number == 1
    assert t.action == "cut_wire"


# ── Whisper client tests ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_transcribe_returns_text():
    from knowledge_base.voice.whisper_client import transcribe
    with patch("knowledge_base.voice.whisper_client.client") as mock_openai:
        mock_openai.audio.transcriptions.create = AsyncMock(return_value="cut the red wire")
        result = await transcribe(b"fake_audio", "wav")
    assert result == "cut the red wire"


@pytest.mark.asyncio
async def test_transcribe_passes_correct_model():
    from knowledge_base.voice.whisper_client import transcribe
    with patch("knowledge_base.voice.whisper_client.client") as mock_openai:
        mock_openai.audio.transcriptions.create = AsyncMock(return_value="hello")
        await transcribe(b"audio_bytes", "mp3")
        call_kwargs = mock_openai.audio.transcriptions.create.call_args.kwargs
    assert call_kwargs["model"] == "whisper-1"
    assert call_kwargs["response_format"] == "text"


# ── ResponseFormatter tests ────────────────────────────────────────────────

def _make_session(urgency: str) -> Session:
    return Session(
        session_id="s", document_id="d", document_type="t",
        active_module=None, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[], user_vocabulary={},
        urgency=urgency, expertise_level="intermediate",
    )


def test_formatter_high_urgency_truncates():
    from knowledge_base.voice.formatter import ResponseFormatter
    f = ResponseFormatter()
    result = f.format("Cut the red wire. Do it now.", _make_session("high"))
    assert result == "Cut the red wire."


def test_formatter_normal_urgency_full():
    from knowledge_base.voice.formatter import ResponseFormatter
    f = ResponseFormatter()
    result = f.format("Cut the red wire.", _make_session("normal"))
    assert "Cut the red wire." in result


def test_formatter_normal_with_confirm_inputs():
    from knowledge_base.voice.formatter import ResponseFormatter
    f = ResponseFormatter()
    result = f.format("Cut the wire.", _make_session("normal"), confirm_inputs={"color": "red"})
    assert "Got it" in result
    assert "color: red" in result
    assert "Cut the wire." in result


def test_formatter_low_urgency_unchanged():
    from knowledge_base.voice.formatter import ResponseFormatter
    f = ResponseFormatter()
    answer = "Step 1: note the wire colors.\nStep 2: cut blue."
    result = f.format(answer, _make_session("low"))
    assert result == answer


# ── TranscriptPreprocessor tests ──────────────────────────────────────────

def _mock_entity_response(entities: dict):
    import json
    mock_resp = MagicMock()
    mock_resp.content = [MagicMock(text=json.dumps(entities))]
    return mock_resp


@pytest.mark.asyncio
async def test_preprocessor_strips_disfluencies():
    from knowledge_base.query.preprocessor import TranscriptPreprocessor
    session = _make_session("normal")
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_mock_entity_response({"colors": [], "numbers": [], "positions": [], "labels": [], "uncertainty": []})
        )
        proc = TranscriptPreprocessor()
        result = await proc.process("um cut the uh red wire", session)
    assert "um" not in result.cleaned_text
    assert "uh" not in result.cleaned_text
    assert "red" in result.cleaned_text


@pytest.mark.asyncio
async def test_preprocessor_extracts_entities():
    from knowledge_base.query.preprocessor import TranscriptPreprocessor
    session = _make_session("normal")
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_mock_entity_response({
                "colors": ["red", "blue"], "numbers": ["3"],
                "positions": ["top"], "labels": [], "uncertainty": [],
            })
        )
        proc = TranscriptPreprocessor()
        result = await proc.process("cut the red wire on top", session)
    assert result.extracted_entities["colors"] == ["red", "blue"]
    assert result.extracted_entities["positions"] == ["top"]


@pytest.mark.asyncio
async def test_preprocessor_detects_correction():
    from knowledge_base.query.preprocessor import TranscriptPreprocessor
    session = _make_session("normal")
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_mock_entity_response({"colors": [], "numbers": [], "positions": [], "labels": [], "uncertainty": []})
        )
        proc = TranscriptPreprocessor()
        result = await proc.process("it's red, wait no, it's blue", session)
    assert "blue" in result.corrections_detected


@pytest.mark.asyncio
async def test_preprocessor_captures_uncertainty():
    from knowledge_base.query.preprocessor import TranscriptPreprocessor
    session = _make_session("normal")
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_mock_entity_response({
                "colors": ["yellow"], "numbers": [], "positions": [], "labels": [],
                "uncertainty": ["I think it's yellow"],
            })
        )
        proc = TranscriptPreprocessor()
        result = await proc.process("I think it's yellow", session)
    assert len(result.uncertainty_flags) == 1
    assert "yellow" in result.uncertainty_flags[0]


@pytest.mark.asyncio
async def test_preprocessor_preserves_raw_text():
    from knowledge_base.query.preprocessor import TranscriptPreprocessor
    session = _make_session("normal")
    raw = "um so like cut the wire"
    with patch("knowledge_base.query.preprocessor.anthropic_client") as mock_client:
        mock_client.messages.create = AsyncMock(
            return_value=_mock_entity_response({"colors": [], "numbers": [], "positions": [], "labels": [], "uncertainty": []})
        )
        proc = TranscriptPreprocessor()
        result = await proc.process(raw, session)
    assert result.raw_text == raw
