from knowledge_base.llm_clients import ingestion_client
from knowledge_base.utils.async_llm import run_llm
from knowledge_base.prompts.ingestion.chunk_classifier import (
    MODEL, MAX_TOKENS, VALID_ENTRY_TYPES, SYSTEM_TEMPLATE, USER_TEMPLATE,
    ChunkClassifierOutput,
)


class ChunkClassifier:
    async def classify(self, text: str, document_type_bias: str) -> dict:
        response = await run_llm(
            ingestion_client.generate,
            USER_TEMPLATE.format(valid_types=VALID_ENTRY_TYPES, text=text[:3000]),
            system_instruction=SYSTEM_TEMPLATE.format(doc_type=document_type_bias),
            response_schema=ChunkClassifierOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        return response.parsed.model_dump()
