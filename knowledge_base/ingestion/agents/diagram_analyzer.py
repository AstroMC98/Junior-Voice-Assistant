from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import generate_with_image
from knowledge_base.prompts.ingestion.diagram_analyzer import (
    MODEL, MAX_TOKENS, CONFIDENCE_THRESHOLD, SYSTEM_PROMPT, USER_PROMPT,
    DiagramAnalyzerOutput,
)


class DiagramAnalyzer:
    CONFIDENCE_THRESHOLD = CONFIDENCE_THRESHOLD

    async def analyze(self, image: bytes) -> dict:
        response = await generate_with_image(
            ingestion_client,
            image,
            USER_PROMPT,
            system_instruction=SYSTEM_PROMPT,
            response_schema=DiagramAnalyzerOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return response.parsed.model_dump()

    def is_high_confidence(self, result: dict) -> bool:
        return result.get("extraction_confidence", 0) >= self.CONFIDENCE_THRESHOLD
