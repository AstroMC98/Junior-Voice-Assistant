import json
import base64
from dataclasses import dataclass
import anthropic
from knowledge_base.prompts.ingestion.page_segmenter import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_TEMPLATE,
)

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
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": USER_TEMPLATE.format(page_number=page_number)},
                ],
            }],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        data = json.loads(raw)
        return SegmentationResult(
            page_number=page_number,
            text_regions=data.get("text_regions", []),
            image_regions=data.get("image_regions", []),
        )
