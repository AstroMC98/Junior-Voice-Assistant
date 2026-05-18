import json
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

VALID_ENTRY_TYPES = [
    "decision_tree", "procedure", "reference_table", "recipe",
    "narrative", "visual_guide", "positional_layout",
    "state_machine", "venn_logic", "faq"
]


class ChunkClassifier:
    async def classify(self, text: str, document_type_bias: str) -> dict:
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            system=f"Document context: {document_type_bias}. Classify this text chunk.",
            messages=[{
                "role": "user",
                "content": (
                    f"Classify into one of {VALID_ENTRY_TYPES}.\n"
                    'Return JSON: {"entry_type": "...", "confidence": 0.0-1.0}\n\n'
                    f"{text[:3000]}"
                )
            }]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
