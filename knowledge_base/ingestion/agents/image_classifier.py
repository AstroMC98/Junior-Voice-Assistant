import json
import base64
import anthropic
from knowledge_base.prompts.ingestion.image_classifier import (
    MODEL, MAX_TOKENS, VALID_ROLES,
    USER_TEMPLATE_WITH_IMAGE, USER_TEMPLATE_HINT_ONLY,
    ImageClassifierOutput,
)

anthropic_client = anthropic.AsyncAnthropic()


class ImageClassifier:
    async def classify_role(self, role_hint: str, image_bytes: bytes | None = None) -> dict:
        if image_bytes:
            b64 = base64.standard_b64encode(image_bytes).decode()
            content = [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                {"type": "text", "text": USER_TEMPLATE_WITH_IMAGE.format(
                    role_hint=role_hint, valid_roles=VALID_ROLES,
                )},
            ]
        else:
            content = USER_TEMPLATE_HINT_ONLY.format(
                role_hint=role_hint, valid_roles=VALID_ROLES,
            )

        response = await anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": content}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1].lstrip("json").strip()
        return ImageClassifierOutput.model_validate(json.loads(raw)).model_dump()
