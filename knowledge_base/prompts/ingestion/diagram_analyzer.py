from pydantic import BaseModel

MODEL = "gemini-2.5-flash"
MAX_TOKENS = 4096
CONFIDENCE_THRESHOLD = 0.70

SYSTEM_PROMPT = (
    "Analyze this logic diagram image and extract the decision logic it encodes.\n"
    "Return ONLY valid JSON:\n"
    "{\n"
    '  "type": "venn_logic | decision_tree | flowchart | state_machine",\n'
    '  "dimensions": ["dimension_name"],\n'
    '  "regions": [{"conditions": {"dim_name": true_or_false}, "action": "symbol_or_text"}],\n'
    '  "action_legend": {"symbol": "full meaning of the symbol"},\n'
    '  "extraction_confidence": 0.0-1.0,\n'
    '  "raw_description": "plain text description of what the diagram shows"\n'
    "}\n"
    "For Venn diagrams, enumerate ALL regions (2^N for N dimensions).\n"
    "For flowcharts, list all decision nodes and their branches."
)

USER_PROMPT = "Extract the complete decision logic from this diagram. Return JSON only."


class DiagramAnalyzerOutput(BaseModel):
    type: str
    dimensions: list[str]
    regions: list[dict]
    action_legend: dict
    extraction_confidence: float
    raw_description: str
