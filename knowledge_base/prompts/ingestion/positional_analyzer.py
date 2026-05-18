from pydantic import BaseModel

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

SYSTEM_PROMPT = (
    "Analyze this positional layout image (grid, button panel, coordinate map).\n"
    "Extract the spatial relationships where position is meaningful data.\n"
    "Return ONLY valid JSON:\n"
    "{\n"
    '  "coordinate_system": "grid | absolute | relative | named_zones",\n'
    '  "positions": {\n'
    '    "position_label_or_coordinate": "content or value at that position"\n'
    "  },\n"
    '  "mappings": {\n'
    '    "descriptive_location": "position_label"\n'
    "  }\n"
    "}\n"
    "For grids use row-column notation (A1, A2, B1...).\n"
    "Enumerate ALL positions visible in the image."
)

USER_PROMPT = "Extract the complete positional layout. Return JSON only."


class PositionalAnalyzerOutput(BaseModel):
    coordinate_system: str
    positions: dict
    mappings: dict
