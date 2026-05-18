import json
import base64
import anthropic
from knowledge_base.prompts.ingestion.positional_analyzer import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_PROMPT, PositionalAnalyzerOutput,
)

anthropic_client = anthropic.AsyncAnthropic()


class PositionalAnalyzer:
    async def analyze(self, image: bytes) -> dict:
        b64 = base64.standard_b64encode(image).decode()
        response = await anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": USER_PROMPT},
                ],
            }],
        )
        raw = response.content[0].text.strip()
        if "```" in raw:
            parts = raw.split("```")
            raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
        return PositionalAnalyzerOutput.model_validate(json.loads(raw)).model_dump()
