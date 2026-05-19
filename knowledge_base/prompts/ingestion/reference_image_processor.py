from pydantic import BaseModel

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 2048

SYSTEM_PROMPT = (
    "Analyze this reference image (a component, connector, indicator, or object someone might need to identify).\n"
    "Generate multi-level descriptions to support voice queries.\n"
    "Return ONLY valid JSON:\n"
    "{\n"
    '  "technical": "precise technical description with specs",\n'
    '  "layperson": "how someone unfamiliar with the domain would describe it",\n'
    '  "distinguishing_features": ["feature that makes this unique", "another feature"],\n'
    '  "commonly_confused_with": ["other_item_id_or_name"],\n'
    '  "differentiators": {\n'
    '    "vs_[confused_item]": "how to tell them apart in plain language"\n'
    "  }\n"
    "}"
)

USER_PROMPT = "Generate multi-level descriptions for this reference item. Return JSON only."


class ReferenceImageOutput(BaseModel):
    technical: str
    layperson: str
    distinguishing_features: list[str]
    commonly_confused_with: list[str]
    differentiators: dict
