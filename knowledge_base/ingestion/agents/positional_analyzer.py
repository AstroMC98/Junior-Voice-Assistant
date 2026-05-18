import json
import base64
import anthropic

anthropic_client = anthropic.AsyncAnthropic()


class PositionalAnalyzer:
    async def analyze(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyze this positional layout image (grid, button panel, coordinate map).
Extract the spatial relationships where position is meaningful data.
Return ONLY valid JSON:
{
  "coordinate_system": "grid | absolute | relative | named_zones",
  "positions": {
    "position_label_or_coordinate": "content or value at that position"
  },
  "mappings": {
    "descriptive_location": "position_label"
  }
}
For grids use row-column notation (A1, A2, B1...).
Enumerate ALL positions visible in the image.""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": "Extract the complete positional layout. Return JSON only."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
