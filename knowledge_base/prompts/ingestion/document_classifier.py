from pydantic import BaseModel

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 256

VALID_TYPES = [
    "game_manual", "recipe", "assembly_guide",
    "reference_manual", "troubleshooting_guide", "general",
]

USER_TEMPLATE = (
    "Classify this document. Valid types: {valid_types}.\n"
    'Return JSON only: {{"document_type": "...", "confidence": 0.0-1.0, "reasoning": "brief"}}'
)


class DocumentClassifierOutput(BaseModel):
    document_type: str
    confidence: float
    reasoning: str = ""
