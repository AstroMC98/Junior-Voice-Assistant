import uuid
from knowledge_base.models.entry import KnowledgeEntry, MediaBlob


class ModuleAssembler:
    def assemble(
        self,
        source_document: str,
        entry_type: str,
        raw_text: str,
        structured_data: dict,
        image_results: list[dict],
        ingestion_trace_id: str,
        confidence_score: float,
    ) -> KnowledgeEntry:
        title = structured_data.get("title", raw_text[:80].strip())
        summary = structured_data.get("summary", raw_text[:200].strip())
        tags = structured_data.get("tags", [entry_type])

        media = [
            MediaBlob(
                blob_id=str(uuid.uuid4()),
                media_type="image/png",
                role=img.get("role", "reference"),
                data=img.get("data", b""),
                descriptions=img.get("descriptions", {}),
                source_page=img.get("source_page", 0),
                bounding_box=tuple(img.get("bounding_box", (0, 0, 0, 0))),
            )
            for img in image_results
        ]

        return KnowledgeEntry(
            id=str(uuid.uuid4()),
            source_document=source_document,
            entry_type=entry_type,
            title=title,
            summary=summary,
            tags=tags,
            raw_text=raw_text,
            vernacular_terms=[],
            structured_data=structured_data,
            media=media,
            references=[],
            referenced_by=[],
            ingestion_trace_id=ingestion_trace_id,
            confidence_score=confidence_score,
            requires_review=confidence_score < 0.7,
        )
