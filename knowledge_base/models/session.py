from dataclasses import dataclass, field


@dataclass
class ProcessedQuery:
    cleaned_text: str
    extracted_entities: dict       # {"colors": [...], "numbers": [...], "positions": [...]}
    uncertainty_flags: list[str]   # ["I think it's yellow"]
    corrections_detected: list[str]
    references_to_resolve: list[str]
    raw_text: str


@dataclass
class Turn:
    turn_number: int
    raw_transcript: str
    processed_query: ProcessedQuery
    response_speech: str
    action: str | None
    trace_id: str


@dataclass
class Session:
    session_id: str
    document_id: str
    document_type: str
    active_module: str | None
    step_state: dict
    known_facts: dict
    resolved_modules: list[str]
    turn_history: list[Turn]
    user_vocabulary: dict[str, str]
    urgency: str            # "high", "normal", "low"
    expertise_level: str    # "beginner", "intermediate", "expert"
    trace_ids: list[str] = field(default_factory=list)
