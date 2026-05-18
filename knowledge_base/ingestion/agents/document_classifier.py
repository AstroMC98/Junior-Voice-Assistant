import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

VALID_TYPES = [
    "game_manual", "recipe", "assembly_guide",
    "reference_manual", "troubleshooting_guide", "general"
]


class DocumentClassifier:
    async def classify(self, first_pages: list[bytes]) -> dict:
        content = []
        for page in first_pages[:3]:
            b64 = base64.standard_b64encode(page).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64}
            })
        content.append({
            "type": "text",
            "text": (
                f"Classify this document. Valid types: {VALID_TYPES}.\n"
                'Return JSON only: {"document_type": "...", "confidence": 0.0-1.0, "reasoning": "brief"}'
            )
        })
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": content}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
