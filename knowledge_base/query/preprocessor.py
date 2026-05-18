import re
import json
import anthropic
from knowledge_base.models.session import ProcessedQuery, Session

anthropic_client = anthropic.AsyncAnthropic()

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

        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system="Extract entities from a voice query. Return JSON only.",
            messages=[{"role": "user", "content": (
                f"Query: {cleaned}\n"
                'Return: {"colors": [...], "numbers": [...], "positions": ["top","left",...], '
                '"labels": [...], "uncertainty": ["phrases expressing doubt"]}'
            )}],
        )
        raw_json = response.content[0].text.strip()
        if "```" in raw_json:
            parts = raw_json.split("```")
            raw_json = parts[1].lstrip("json").strip() if len(parts) > 1 else raw_json
        entities = json.loads(raw_json)
        uncertainty = entities.pop("uncertainty", [])

        return ProcessedQuery(
            cleaned_text=cleaned,
            extracted_entities=entities,
            uncertainty_flags=uncertainty,
            corrections_detected=corrections,
            references_to_resolve=[],
            raw_text=raw,
        )
