import os
import base64
import re
import time
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, Depends, UploadFile
import json as _json
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from api.models import (
    CreateGuideRequest,
    Guide,
    SessionTurnRequest,
    SessionResponse,
    Step,
)
from api.kv import get_guide, save_guide
from api.blob import upload_image
from api.claude import process_guide, session_turn
from api.transcription import transcribe_audio
from api.env import load_env_file
from api.utils import generate_id, strip_html

# Load .env.local for local development (Vercel injects env vars directly in production)
load_env_file(".env.local")

# CORS — only active when CORS_ORIGINS is set (local dev only)
_cors_origins_env = os.environ.get("CORS_ORIGINS", "")
_cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app = FastAPI(title="Junior API", version="1.0.0")

if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

_BLOCKED_HOST_RE = re.compile(
    r"^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|::1$|0\.0\.0\.0)",
    re.IGNORECASE,
)


def require_api_key(request: Request) -> str:
    # NEVER log this value — it is a user-supplied secret used only for the duration of this request
    key = request.headers.get("X-Api-Key", "").strip()
    if not key:
        raise HTTPException(status_code=401, detail="API key required")
    return key


@app.post("/api/guides", response_model=Guide, status_code=201)
async def create_guide(body: CreateGuideRequest, api_key: str = Depends(require_api_key)):
    if not body.title.strip():
        raise HTTPException(status_code=400, detail="title is required")

    try:
        image_urls: list[str] = []
        if body.images:
            for img_b64 in body.images:
                img_bytes = base64.b64decode(img_b64)
                url = await upload_image(f"{generate_id()}.png", img_bytes)
                image_urls.append(url)

        raw_steps = await process_guide(
            source=body.source,
            text=body.text,
            images=body.images,
            api_key=api_key,
        )

        steps: list[Step] = []
        for step in raw_steps:
            if step.image_index is not None and step.image_index < len(image_urls):
                step.image_url = image_urls[step.image_index]
            steps.append(step)

        guide = Guide(
            id=generate_id(),
            title=body.title.strip(),
            source=body.source,
            steps=steps,
            created_at=int(time.time() * 1000),
        )

        await save_guide(guide)
        return guide

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/guides/{guide_id}", response_model=Guide)
async def get_guide_endpoint(guide_id: str):
    guide = await get_guide(guide_id)
    if guide is None:
        raise HTTPException(status_code=404, detail="Not found")
    return guide


@app.post("/api/guides/{guide_id}", response_model=Guide, status_code=201)
async def fork_guide(guide_id: str):
    original = await get_guide(guide_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Not found")

    fork = Guide(
        **{
            **original.model_dump(),
            "id": generate_id(),
            "fork_of": original.id,
            "created_at": int(time.time() * 1000),
        }
    )
    await save_guide(fork)
    return fork


@app.post("/api/session", response_model=SessionResponse)
async def session_endpoint(
    audio: UploadFile = File(...),
    guide: str = Form(...),
    currentStepIndex: int = Form(...),
    photo: str | None = Form(None),
    api_key: str = Depends(require_api_key),
):
    guide_obj = Guide(**_json.loads(guide))

    if not guide_obj.steps:
        raise HTTPException(status_code=400, detail="Missing required fields")
    if currentStepIndex < 0 or currentStepIndex >= len(guide_obj.steps):
        raise HTTPException(status_code=400, detail="Step index out of range")

    audio_bytes = await audio.read()
    transcript = await transcribe_audio(audio_bytes)

    return await session_turn(
        guide=guide_obj,
        current_step_index=currentStepIndex,
        transcript=transcript,
        photo=photo,
        api_key=api_key,
    )


@app.get("/api/fetch-url")
async def fetch_url(url: str = Query(...)):
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=403, detail="Only http/https allowed")
    if _BLOCKED_HOST_RE.match(parsed.hostname or ""):
        raise HTTPException(status_code=403, detail="Forbidden URL")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers={"User-Agent": "Junior-Bot/1.0"})
    except Exception:
        raise HTTPException(status_code=502, detail="Fetch failed")

    if not response.is_success:
        raise HTTPException(status_code=502, detail=f"Upstream {response.status_code}")

    return {"text": strip_html(response.text)}


_kb_trace_store = None


async def _get_trace_store():
    global _kb_trace_store
    if _kb_trace_store is None:
        from knowledge_base.store.trace_store import TraceStore
        db_path = os.environ.get("KB_TRACE_DB", "traces.db")
        _kb_trace_store = TraceStore(db_path=db_path)
        await _kb_trace_store.init()
    return _kb_trace_store


@app.get("/api/kb/metrics")
async def kb_metrics():
    from knowledge_base.feedback.metrics import compute_metrics
    store = await _get_trace_store()
    return await compute_metrics(store)


# Vercel / Lambda ASGI entry point — variable must be named "handler"
handler = Mangum(app, lifespan="off")
