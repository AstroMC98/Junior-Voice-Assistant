import json
import anthropic
from knowledge_base.prompts.ingestion.type_specific_extractor import (
    MODEL, MAX_TOKENS, EXTRACTION_PROMPTS, GENERIC_PROMPT, SYSTEM_SUFFIX,
)

anthropic_client = anthropic.AsyncAnthropic()


class TypeSpecificExtractor:
    async def extract(self, text: str, entry_type: str) -> dict:
        prompt = EXTRACTION_PROMPTS.get(entry_type, GENERIC_PROMPT)
        response = await anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=f"{prompt}{SYSTEM_SUFFIX}",
            messages=[{"role": "user", "content": text[:8000]}],
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
