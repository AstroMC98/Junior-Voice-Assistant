from knowledge_base.models.entry import KnowledgeEntry, MediaBlob

def test_knowledge_entry_fields():
    e = KnowledgeEntry(
        id="e1", source_document="doc.pdf", entry_type="procedure",
        title="Step 1", summary="Do X", tags=["wire"], raw_text="raw text",
        vernacular_terms=["the wire step"], structured_data={"steps": []},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t1", confidence_score=0.9, requires_review=False
    )
    assert e.entry_type == "procedure"
    assert e.confidence_score == 0.9
    assert e.requires_review is False

def test_media_blob_fields():
    b = MediaBlob(
        blob_id="b1", media_type="image/png", role="diagram",
        data=b"bytes", descriptions={"technical": "A diagram", "layperson": "A picture"},
        source_page=0, bounding_box=(0, 0, 100, 100)
    )
    assert b.role == "diagram"
    assert b.bounding_box == (0, 0, 100, 100)

def test_knowledge_entry_defaults_empty_lists():
    e = KnowledgeEntry(
        id="e2", source_document="d.pdf", entry_type="narrative",
        title="T", summary="S", tags=[], raw_text="r",
        vernacular_terms=[], structured_data={},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t2", confidence_score=0.5, requires_review=True
    )
    assert e.references == []
    assert e.requires_review is True
