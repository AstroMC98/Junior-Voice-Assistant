from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import run_llm, generate_with_image
from knowledge_base.prompts.ingestion.image_classifier import (
    MODEL, MAX_TOKENS, VALID_ROLES,
    USER_TEMPLATE_WITH_IMAGE, USER_TEMPLATE_HINT_ONLY,
    ImageClassifierOutput,
)


class ImageClassifier:
    async def classify_role(self, role_hint: str, image_bytes: bytes | None = None) -> dict:
        if image_bytes:
            response = await generate_with_image(
                ingestion_client,
                image_bytes,
                USER_TEMPLATE_WITH_IMAGE.format(role_hint=role_hint, valid_roles=VALID_ROLES),
                response_schema=ImageClassifierOutput,
                max_output_tokens=MAX_TOKENS,
                model=MODEL,
            )
        else:
            response = await run_llm(
                ingestion_client.generate,
                USER_TEMPLATE_HINT_ONLY.format(role_hint=role_hint, valid_roles=VALID_ROLES),
                response_schema=ImageClassifierOutput,
                max_output_tokens=MAX_TOKENS,
                model=MODEL,
            )
        return response.parsed.model_dump()
