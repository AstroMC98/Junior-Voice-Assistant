from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import generate_with_images
from knowledge_base.prompts.ingestion.document_classifier import (
    MODEL, MAX_TOKENS, VALID_TYPES, USER_TEMPLATE, DocumentClassifierOutput,
)


class DocumentClassifier:
    async def classify(self, first_pages: list[bytes]) -> dict:
        response = await generate_with_images(
            ingestion_client,
            first_pages[:3],
            USER_TEMPLATE.format(valid_types=VALID_TYPES),
            response_schema=DocumentClassifierOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return response.parsed.model_dump()
