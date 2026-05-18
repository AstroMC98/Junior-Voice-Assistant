import json
import anthropic
from knowledge_base.prompts.ingestion.chunk_classifier import (
    MODEL, MAX_TOKENS, VALID_ENTRY_TYPES, SYSTEM_TEMPLATE, USER_TEMPLATE,
    ChunkClassifierOutput,
)

anthropic_client = anthropic.AsyncAnthropic()


class ChunkClassifier:
    async def classify(self, text: str, document_type_bias: str) -> dict:
        response = await anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_TEMPLATE.format(doc_type=document_type_bias),
            messages=[{"role": "user", "content": USER_TEMPLATE.format(
                valid_types=VALID_ENTRY_TYPES,
                text=text[:3000],
            )}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return ChunkClassifierOutput.model_validate(json.loads(raw)).model_dump()
