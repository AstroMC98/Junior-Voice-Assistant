MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

SYSTEM_PROMPT = (
    "Analyze this document page image. Identify all text blocks and image regions.\n"
    "Return ONLY valid JSON with this exact structure:\n"
    "{\n"
    '  "text_regions": [\n'
    '    {"bbox": [x, y, w, h], "text": "extracted text content", "confidence": 0.95}\n'
    "  ],\n"
    '  "image_regions": [\n'
    '    {"bbox": [x, y, w, h], "role_hint": "diagram|reference|positional_layout|state_repr|decorative"}\n'
    "  ]\n"
    "}\n"
    "bbox values are pixels from top-left corner."
)

USER_TEMPLATE = "Segment page {page_number}. Return JSON only, no explanation."
