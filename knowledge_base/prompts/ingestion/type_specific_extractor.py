MODEL = "gemini-2.5-flash"
MAX_TOKENS = 2048

EXTRACTION_PROMPTS: dict[str, str] = {
    "decision_tree": (
        'Extract as JSON: {"conditions": ["condition text"], '
        '"branches": [{"condition": "...", "action": "..."}], '
        '"outcomes": ["outcome1", "outcome2"], "default": "default action"}'
    ),
    "procedure": (
        'Extract as JSON: {"steps": [{"order": 1, "action": "...", "note": null}], '
        '"prerequisites": ["..."], "warnings": ["..."]}'
    ),
    "reference_table": (
        'Extract as JSON: {"columns": ["col1", "col2"], '
        '"rows": [["val1", "val2"]], "lookup_keys": ["primary_key_column"]}'
    ),
    "recipe": (
        'Extract as JSON: {"ingredients": [{"item": "...", "amount": "..."}], '
        '"steps": [{"order": 1, "action": "..."}], "timing": "...", "servings": null}'
    ),
    "narrative": (
        'Extract as JSON: {"key_points": ["point1"], '
        '"entities": [{"name": "...", "type": "..."}], "context": "brief context"}'
    ),
    "visual_guide": (
        'Extract as JSON: {"visual_description": "...", '
        '"identifying_features": ["feature1"], '
        '"commonly_confused_with": {"other_item": "how to distinguish"}}'
    ),
    "positional_layout": (
        'Extract as JSON: {"coordinate_system": "grid|absolute|relative", '
        '"positions": {"label": {"x": 0, "y": 0}}, "mappings": {"position": "meaning"}}'
    ),
    "state_machine": (
        'Extract as JSON: {"states": ["state1", "state2"], '
        '"transitions": [{"from": "s1", "to": "s2", "trigger": "..."}], '
        '"current_state_indicators": ["how to tell current state"]}'
    ),
    "venn_logic": (
        'Extract as JSON: {"dimensions": ["dim1", "dim2"], '
        '"regions": [{"conditions": {"dim1": true, "dim2": false}, "action": "..."}], '
        '"action_legend": {"symbol": "full meaning"}}'
    ),
    "faq": (
        'Extract as JSON: {"question": "...", "answer": "...", '
        '"related_questions": ["q1", "q2"]}'
    ),
}

GENERIC_PROMPT = "Extract all key information as structured JSON."

SYSTEM_SUFFIX = "\nReturn ONLY valid JSON. No explanation, no markdown."
