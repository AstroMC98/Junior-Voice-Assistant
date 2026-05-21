import json
import pytest
from fastapi.testclient import TestClient
from api.index import app

GUIDE_DICT = {
    "id": "g1",
    "title": "Bake Bread",
    "source": "pdf",
    "steps": [
        {"index": 0, "title": "Mix", "content": "Mix flour and water",
         "image_url": None, "image_index": None, "crop": None},
        {"index": 1, "title": "Knead", "content": "Knead for 10 minutes",
         "image_url": None, "image_index": None, "crop": None},
    ],
    "fork_of": None,
    "created_at": 1000000,
}

client = TestClient(app)


def test_retrieve_context_returns_context_and_echoes_transcript():
    response = client.post(
        "/api/retrieve",
        data={
            "guide": json.dumps(GUIDE_DICT),
            "currentStepIndex": "0",
            "transcript": "how do I mix the flour?",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "context" in body
    assert "Bake Bread" in body["context"]
    assert "Mix flour and water" in body["context"]
    assert body["transcript"] == "how do I mix the flour?"


def test_retrieve_context_returns_400_for_step_out_of_range():
    response = client.post(
        "/api/retrieve",
        data={
            "guide": json.dumps(GUIDE_DICT),
            "currentStepIndex": "99",
            "transcript": "hello",
        },
    )
    assert response.status_code == 400
    assert "Step index out of range" in response.json()["detail"]


def test_retrieve_context_returns_400_for_invalid_guide_json():
    response = client.post(
        "/api/retrieve",
        data={
            "guide": "not-valid-json",
            "currentStepIndex": "0",
            "transcript": "hello",
        },
    )
    assert response.status_code == 400
