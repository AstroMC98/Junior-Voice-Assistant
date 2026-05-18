from pydantic import BaseModel

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 128

VALID_ENTRY_TYPES = [
    "decision_tree", "procedure", "reference_table", "recipe",
    "narrative", "visual_guide", "positional_layout",
    "state_machine", "venn_logic", "faq",
]

SYSTEM_TEMPLATE = "Document context: {doc_type}. Classify this text chunk."

USER_TEMPLATE = (
    "Classify into one of {valid_types}.\n"
    'Return JSON: {{"entry_type": "...", "confidence": 0.0-1.0}}\n\n'
    "{text}"
)


class ChunkClassifierOutput(BaseModel):
    entry_type: str
    confidence: float
