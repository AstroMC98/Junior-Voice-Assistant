import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_transcribe_audio_passes_bytes_and_webm_format():
    fake_bytes = b"fake-audio-data"
    with patch(
        "api.transcription.whisper_client.transcribe", new_callable=AsyncMock
    ) as mock_transcribe:
        mock_transcribe.return_value = "cut the red wire"
        from api.transcription import transcribe_audio
        result = await transcribe_audio(fake_bytes)
    mock_transcribe.assert_called_once_with(fake_bytes, "webm")
    assert result == "cut the red wire"


@pytest.mark.asyncio
async def test_transcribe_audio_returns_empty_string_when_whisper_returns_empty():
    with patch(
        "api.transcription.whisper_client.transcribe", new_callable=AsyncMock
    ) as mock_transcribe:
        mock_transcribe.return_value = ""
        from api.transcription import transcribe_audio
        result = await transcribe_audio(b"silent-audio")
    assert result == ""
