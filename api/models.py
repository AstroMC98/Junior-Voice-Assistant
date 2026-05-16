from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel


class Crop(BaseModel):
    x: float
    y: float
    w: float
    h: float


class Step(BaseModel):
    index: int
    title: str
    content: str
    image_url: Optional[str] = None
    image_index: Optional[int] = None
    crop: Optional[Crop] = None


class Guide(BaseModel):
    id: str
    title: str
    source: Literal["pdf", "url", "camera"]
    steps: list[Step]
    fork_of: Optional[str] = None
    created_at: int  # Unix ms timestamp


class SessionResponse(BaseModel):
    speech: str
    action: Optional[Literal["show_image", "advance"]] = None
    step: Optional[int] = None


class CreateGuideRequest(BaseModel):
    source: Literal["pdf", "url", "camera"]
    title: str
    text: Optional[str] = None
    images: Optional[list[str]] = None  # base64-encoded PNG strings


class SessionTurnRequest(BaseModel):
    guide: Guide
    currentStepIndex: int
    transcript: str
    photo: Optional[str] = None  # base64 JPEG
