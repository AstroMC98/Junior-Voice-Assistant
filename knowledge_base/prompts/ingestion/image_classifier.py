from pydantic import BaseModel

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 64

VALID_ROLES = ["logic_diagram", "reference", "positional_layout", "state_repr", "decorative"]

USER_TEMPLATE_WITH_IMAGE = (
    "Hint from segmenter: {role_hint}. "
    "Classify this image role from {valid_roles}. "
    'Return JSON: {{"role": "...", "confidence": 0.0-1.0}}'
)

USER_TEMPLATE_HINT_ONLY = (
    "Role hint: {role_hint}. Map to one of {valid_roles}. "
    'Return JSON: {{"role": "...", "confidence": 0.85}}'
)


class ImageClassifierOutput(BaseModel):
    role: str
    confidence: float = 0.85
