from knowledge_base.models.session import ProcessedQuery, Session

WORKFLOWS = [
    "identification",
    "instruction",
    "lookup",
    "disambiguation",
    "stateful_continuation",
]


class Router:
    def classify(
        self,
        query: ProcessedQuery,
        session: Session,
        document_type: str,
    ) -> tuple[str | None, dict]:
        text = query.cleaned_text.lower()
        entities = query.extracted_entities

        # Stateful continuation: active module + "next" / "done" / similar
        if session.active_module and any(
            w in text for w in ["next", "continue", "what's next", "whats next", "done"]
        ):
            return "stateful_continuation", {"module_id": session.active_module}

        # Instruction: active module + how/what to do
        if session.active_module and any(
            w in text for w in ["how", "what do i do", "instructions", "steps"]
        ):
            return "instruction", {"module_id": session.active_module}

        # Lookup: explicit fact query with no visual entities
        if any(w in text for w in ["what is", "what's", "tell me", "show me the"]) and not entities.get("colors"):
            return "lookup", {}

        # Identification: no active module, visual entities present
        if not session.active_module and any(
            k in entities and entities[k]
            for k in ["colors", "positions", "labels"]
        ):
            return "identification", {}

        return None, {}
