from dataclasses import dataclass


@dataclass
class MediaBlob:
    blob_id: str
    media_type: str
    role: str  # "diagram", "reference", "state_repr", "positional_layout", "decorative"
    data: bytes
    descriptions: dict  # keys: "technical", "layperson", "distinguishing_features", etc.
    source_page: int
    bounding_box: tuple  # (x, y, w, h) in source page coordinates


@dataclass
class KnowledgeEntry:
    # Identity
    id: str
    source_document: str
    entry_type: str  # "decision_tree", "procedure", "reference_table", etc.

    # Universal fields
    title: str
    summary: str
    tags: list[str]
    raw_text: str
    vernacular_terms: list[str]  # spoken-language aliases

    # Type-specific payload
    structured_data: dict  # schema varies by entry_type

    # Visual context
    media: list[MediaBlob]

    # Graph edges
    references: list[str]   # IDs of entries this depends on
    referenced_by: list[str]  # reverse links

    # Metadata
    ingestion_trace_id: str
    confidence_score: float
    requires_review: bool
