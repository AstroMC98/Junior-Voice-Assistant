from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import generate_with_image
from knowledge_base.prompts.ingestion.positional_analyzer import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_PROMPT, PositionalAnalyzerOutput,
)


class PositionalAnalyzer:
    async def analyze(self, image: bytes) -> dict:
        response = await generate_with_image(
            ingestion_client,
            image,
            USER_PROMPT,
            system_instruction=SYSTEM_PROMPT,
            response_schema=PositionalAnalyzerOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return response.parsed.model_dump()
