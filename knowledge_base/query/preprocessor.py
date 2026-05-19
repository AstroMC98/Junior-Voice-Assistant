import re
import json
from knowledge_base.llm_clients import query_client_haiku
from knowledge_base.utils.async_llm import run_llm
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.prompts.query.preprocessor import (
    MODEL, MAX_TOKENS, SYSTEM_PROMPT, USER_TEMPLATE, PreprocessorOutput,
)

_DISFLUENCIES = re.compile(r"\b(um|uh|like|so|you know|er|hmm)\b", re.IGNORECASE)
_CORRECTION = re.compile(
    r"(?:wait|no|actually),?\s+(?:it'?s|its|the answer is)\s+(\w+)",
    re.IGNORECASE,
)


class TranscriptPreprocessor:
    async def process(self, raw: str, session: Session) -> ProcessedQuery:
        cleaned = _DISFLUENCIES.sub("", raw).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)

        corrections = []
        m = _CORRECTION.search(cleaned)
        if m:
            corrections.append(m.group(1))

        response = await run_llm(
            query_client_haiku.generate,
            USER_TEMPLATE.format(query=cleaned),
            system_instruction=SYSTEM_PROMPT,
            response_schema=PreprocessorOutput,
            max_output_tokens=MAX_TOKENS,
            model=MODEL,
        )
        entities = response.parsed.model_dump()
        uncertainty = entities.pop("uncertainty", [])

        return ProcessedQuery(
            cleaned_text=cleaned,
            extracted_entities=entities,
            uncertainty_flags=uncertainty,
            corrections_detected=corrections,
            references_to_resolve=[],
            raw_text=raw,
        )
