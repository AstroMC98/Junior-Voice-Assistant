from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import run_llm
from knowledge_base.prompts.ingestion.vernacular_generator import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_TEMPLATE, VernacularOutput,
)


class VernacularGenerator:
    async def generate(self, title: str, summary: str, tags: list[str]) -> list[str]:
        response = await run_llm(
            ingestion_client.generate,
            USER_TEMPLATE.format(title=title, summary=summary, tags=", ".join(tags)),
            system_instruction=SYSTEM_PROMPT,
            response_schema=VernacularOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return response.parsed.terms
