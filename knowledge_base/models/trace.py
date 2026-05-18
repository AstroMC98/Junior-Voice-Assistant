from dataclasses import dataclass
from datetime import datetime


@dataclass
class TraceEvent:
    # Identity
    trace_id: str
    parent_trace_id: str | None
    span_id: str

    # What
    event_type: str  # "agent_call", "handoff", "failure", "recovery", "tier_escalation"
    agent_name: str
    workflow_id: str | None
    tier: int  # 1, 2, or 3

    # Timing
    timestamp_start: datetime
    timestamp_end: datetime
    duration_ms: int

    # Data
    input_data: dict
    output_data: dict

    # Outcome
    status: str  # "success", "failure", "timeout", "skipped"
    failure_type: str | None   # typed failure code: ZERO_MATCHES, AMBIGUOUS_MATCH, etc.
    failure_detail: str | None

    # Context
    session_id: str | None
    document_id: str | None

    # Performance
    token_count_in: int | None
    token_count_out: int | None
    model_id: str | None
