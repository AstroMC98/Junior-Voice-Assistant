from pydantic import BaseModel

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 2048


class TextRegion(BaseModel):
    bbox: list[int]
    text: str
    confidence: float


class ImageRegion(BaseModel):
    bbox: list[int]
    role_hint: str


class PageSegmenterOutput(BaseModel):
    text_regions: list[TextRegion]
    image_regions: list[ImageRegion]


SYSTEM_PROMPT = (
    "Analyze this document page image. Identify all text blocks and image regions. "
    "bbox values are pixel coordinates from the top-left corner."
)

USER_TEMPLATE = "Segment page {page_number}. Return JSON only, no explanation."
