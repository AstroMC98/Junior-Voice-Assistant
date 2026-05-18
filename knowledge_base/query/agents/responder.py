import anthropic
from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.models.session import Session

anthropic_client = anthropic.AsyncAnthropic()


class Responder:
    async def respond_identification(self, entry: KnowledgeEntry | None, session: Session) -> str:
        if entry is None:
            return "I could not retrieve information about that module."
        summary = entry.vernacular_terms[0] if entry.vernacular_terms else entry.title
        return f"I found the {summary}. {entry.summary}"

    async def respond_instruction(self, entry: KnowledgeEntry | None, session: Session) -> str:
        if entry is None:
            return "I could not find instructions for that module."
        steps = entry.structured_data.get("steps", [])
        if not steps:
            return entry.summary or entry.raw_text[:200]
        first = steps[0]
        action = first.get("action", "") if isinstance(first, dict) else str(first)
        return f"Step 1: {action}"

    async def respond_lookup(self, entry: KnowledgeEntry | None, query_text: str, session: Session) -> str:
        if entry is None:
            return "I could not find an answer to that question."
        return entry.summary or entry.raw_text[:200]

    async def respond_disambiguation(self, candidates: list[KnowledgeEntry], session: Session) -> str:
        if not candidates:
            return "I could not find any matching modules."
        names = ", ".join(
            (e.vernacular_terms[0] if e.vernacular_terms else e.title)
            for e in candidates[:3]
        )
        return f"I found several possible matches: {names}. Could you be more specific?"
