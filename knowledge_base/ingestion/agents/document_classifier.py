import json
import base64
import anthropic
from knowledge_base.prompts.ingestion.document_classifier import (
    MODEL, MAX_TOKENS, VALID_TYPES, USER_TEMPLATE, DocumentClassifierOutput,
)

anthropic_client = anthropic.AsyncAnthropic()


class DocumentClassifier:
    async def classify(self, first_pages: list[bytes]) -> dict:
        content = []
        for page in first_pages[:3]:
            b64 = base64.standard_b64encode(page).decode()
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": b64},
            })
        content.append({
            "type": "text",
            "text": USER_TEMPLATE.format(valid_types=VALID_TYPES),
        })
        response = await anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": content}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return DocumentClassifierOutput.model_validate(json.loads(raw)).model_dump()
