import json
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from api.index import app
from api.models import Guide, SessionResponse, Step


GUIDE_DICT = {
    "id": "g1",
    "title": "Test Guide",
    "source": "pdf",
    "steps": [{"index": 0, "title": "Step 1", "content": "Do this", "image_url": None, "image_index": None, "crop": None}],
    "fork_of": None,
    "created_at": 1000000,
}

client = TestClient(app)


@patch("api.index.session_turn", new_callable=AsyncMock)
@patch("api.index.transcribe_audio", new_callable=AsyncMock)
def test_session_endpoint_transcribes_audio_and_calls_session_turn(
    mock_transcribe, mock_session_turn
):
    mock_transcribe.return_value = "cut the red wire"
    mock_session_turn.return_value = SessionResponse(
        speech="Got it!", action=None, step=None
    )

    response = client.post(
        "/api/session",
        headers={"X-Api-Key": "test-key"},
        data={
            "guide": json.dumps(GUIDE_DICT),
            "currentStepIndex": "0",
        },
        files={"audio": ("audio.webm", b"fake-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 200
    assert response.json() == {"speech": "Got it!", "action": None, "step": None}
    mock_transcribe.assert_called_once_with(b"fake-audio-bytes")
    mock_session_turn.assert_called_once_with(
        guide=Guide(**GUIDE_DICT),
        current_step_index=0,
        transcript="cut the red wire",
        photo=None,
        api_key="test-key",
    )


@patch("api.index.session_turn", new_callable=AsyncMock)
@patch("api.index.transcribe_audio", new_callable=AsyncMock)
def test_session_endpoint_returns_400_for_invalid_step_index(
    mock_transcribe, mock_session_turn
):
    mock_transcribe.return_value = "hello"

    response = client.post(
        "/api/session",
        headers={"X-Api-Key": "test-key"},
        data={
            "guide": json.dumps(GUIDE_DICT),
            "currentStepIndex": "99",
        },
        files={"audio": ("audio.webm", b"fake-audio-bytes", "audio/webm")},
    )

    assert response.status_code == 400
    assert "Step index out of range" in response.json()["detail"]
    mock_session_turn.assert_not_called()


def test_session_endpoint_returns_401_without_api_key():
    response = client.post(
        "/api/session",
        data={
            "guide": json.dumps(GUIDE_DICT),
            "currentStepIndex": "0",
        },
        files={"audio": ("audio.webm", b"fake-audio-bytes", "audio/webm")},
    )
    assert response.status_code == 401
