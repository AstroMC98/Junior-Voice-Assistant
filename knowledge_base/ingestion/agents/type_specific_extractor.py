import json
from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import run_llm
from knowledge_base.prompts.ingestion.type_specific_extractor import (
    MODEL, MAX_TOKENS, EXTRACTION_PROMPTS, GENERIC_PROMPT, SYSTEM_SUFFIX,
)


class TypeSpecificExtractor:
    # response_schema= is intentionally absent: output shape varies per entry_type at runtime,
    # so raw JSON parsing is required here rather than a fixed Pydantic schema.
    async def extract(self, text: str, entry_type: str) -> dict:
        prompt = EXTRACTION_PROMPTS.get(entry_type, GENERIC_PROMPT)
        response = await run_llm(
            ingestion_client.generate,
            text[:8000],
            system_instruction=f"{prompt}{SYSTEM_SUFFIX}",
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        raw = response.text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
