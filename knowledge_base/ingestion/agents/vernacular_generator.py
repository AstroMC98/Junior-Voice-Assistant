import json
import anthropic
from knowledge_base.prompts.ingestion.vernacular_generator import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_TEMPLATE,
)

anthropic_client = anthropic.AsyncAnthropic()


class VernacularGenerator:
    async def generate(self, title: str, summary: str, tags: list[str]) -> list[str]:
        response = await anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": USER_TEMPLATE.format(
                title=title, summary=summary, tags=", ".join(tags),
            )}],
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return json.loads(raw)
