import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()


class ReferenceImageProcessor:
    async def process(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyze this reference image (a component, connector, indicator, or object someone might need to identify).
Generate multi-level descriptions to support voice queries.
Return ONLY valid JSON:
{
  "technical": "precise technical description with specs",
  "layperson": "how someone unfamiliar with the domain would describe it",
  "distinguishing_features": ["feature that makes this unique", "another feature"],
  "commonly_confused_with": ["other_item_id_or_name"],
  "differentiators": {
    "vs_[confused_item]": "how to tell them apart in plain language"
  }
}""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": "Generate multi-level descriptions for this reference item. Return JSON only."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
