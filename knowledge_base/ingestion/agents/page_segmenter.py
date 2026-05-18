import json
import base64
from dataclasses import dataclass
import anthropic

anthropic_client = anthropic.AsyncAnthropic()


@dataclass
class SegmentationResult:
    page_number: int
    text_regions: list[dict]   # each: {"bbox": [x,y,w,h], "text": str, "confidence": float}
    image_regions: list[dict]  # each: {"bbox": [x,y,w,h], "role_hint": str}


class PageSegmenter:
    async def segment(self, page_image: bytes, page_number: int) -> SegmentationResult:
        b64 = base64.standard_b64encode(page_image).decode()
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system="""Analyze this document page image. Identify all text blocks and image regions.
Return ONLY valid JSON with this exact structure:
{
  "text_regions": [
    {"bbox": [x, y, w, h], "text": "extracted text content", "confidence": 0.95}
  ],
  "image_regions": [
    {"bbox": [x, y, w, h], "role_hint": "diagram|reference|positional_layout|state_repr|decorative"}
  ]
}
bbox values are pixels from top-left corner.""",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": "image/png", "data": b64}
                    },
                    {
                        "type": "text",
                        "text": f"Segment page {page_number}. Return JSON only, no explanation."
                    }
                ]
            }]
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        return SegmentationResult(
            page_number=page_number,
            text_regions=data.get("text_regions", []),
            image_regions=data.get("image_regions", [])
        )
