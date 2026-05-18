import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()

VALID_ROLES = ["logic_diagram", "reference", "positional_layout", "state_repr", "decorative"]


class ImageClassifier:
    async def classify_role(self, role_hint: str, image_bytes: bytes | None = None) -> dict:
        if image_bytes:
            b64 = base64.standard_b64encode(image_bytes).decode()
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": (
                    f"Hint from segmenter: {role_hint}. "
                    f"Classify this image role from {VALID_ROLES}. "
                    'Return JSON: {"role": "...", "confidence": 0.0-1.0}'
                )}
            ]
        else:
            content = (
                f"Role hint: {role_hint}. Map to one of {VALID_ROLES}. "
                'Return JSON: {"role": "...", "confidence": 0.85}'
            )

        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            messages=[{"role": "user", "content": content}]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return json.loads(raw)
