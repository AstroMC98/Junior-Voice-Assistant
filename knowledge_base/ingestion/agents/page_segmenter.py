from dataclasses import dataclass
from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import generate_with_image
from knowledge_base.prompts.ingestion.page_segmenter import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_TEMPLATE, PageSegmenterOutput,
)


@dataclass
class SegmentationResult:
    page_number: int
    text_regions: list[dict]   # each: {"bbox": [x,y,w,h], "text": str, "confidence": float}
    image_regions: list[dict]  # each: {"bbox": [x,y,w,h], "role_hint": str}


class PageSegmenter:
    async def segment(self, page_image: bytes, page_number: int) -> SegmentationResult:
        response = await generate_with_image(
            ingestion_client,
            page_image,
            USER_TEMPLATE.format(page_number=page_number),
            system_instruction=SYSTEM_PROMPT,
            response_schema=PageSegmenterOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        parsed: PageSegmenterOutput = response.parsed
        return SegmentationResult(
            page_number=page_number,
            text_regions=[r.model_dump() for r in parsed.text_regions],
            image_regions=[r.model_dump() for r in parsed.image_regions],
        )
