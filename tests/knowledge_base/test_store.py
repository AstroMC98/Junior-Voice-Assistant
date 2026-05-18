import pytest
import pytest_asyncio
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.models.entry import KnowledgeEntry, MediaBlob


def _make_entry(id: str, tags: list[str] = None, vernacular: list[str] = None) -> KnowledgeEntry:
    return KnowledgeEntry(
        id=id, source_document="doc.pdf", entry_type="procedure",
        title=f"Title {id}", summary=f"Summary {id}",
        tags=tags or ["default"], raw_text="raw text here",
        vernacular_terms=vernacular or [],
        structured_data={"steps": [{"order": 1, "action": "do thing"}]},
        media=[], references=[], referenced_by=[],
        ingestion_trace_id="t1", confidence_score=0.9, requires_review=False
    )


@pytest.fixture
async def store(tmp_path):
    s = KnowledgeStore(db_path=str(tmp_path / "test.db"))
    await s.init()
    return s


@pytest.mark.asyncio
async def test_save_and_get(store):
    entry = _make_entry("e1", tags=["wire", "red"])
    await store.save(entry)
    result = await store.get("e1")
    assert result is not None
    assert result.title == "Title e1"
    assert result.tags == ["wire", "red"]
    assert result.confidence_score == 0.9


@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(store):
    result = await store.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_search_by_tag(store):
    await store.save(_make_entry("e1", tags=["wire"]))
    await store.save(_make_entry("e2", tags=["battery"]))
    results = await store.search_by_tag("wire")
    assert len(results) == 1
    assert results[0].id == "e1"


@pytest.mark.asyncio
async def test_search_by_vernacular(store):
    entry = _make_entry("e1", vernacular=["the red wire step", "cut the red one"])
    await store.save(entry)
    results = await store.search_by_vernacular("red wire")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_list_by_document(store):
    await store.save(_make_entry("e1"))
    await store.save(_make_entry("e2"))
    results = await store.list_by_document("doc.pdf")
    assert len(results) == 2


@pytest.mark.asyncio
async def test_save_updates_existing(store):
    entry = _make_entry("e1", tags=["old"])
    await store.save(entry)
    entry.tags = ["new"]
    await store.save(entry)
    result = await store.get("e1")
    assert result.tags == ["new"]


@pytest.mark.asyncio
async def test_save_and_get_with_media_blob(store):
    blob = MediaBlob(
        blob_id="b1", media_type="image/png", role="diagram",
        data=b"\x89PNG\r\n",
        descriptions={"technical": "A Venn diagram", "layperson": "A logic chart"},
        source_page=2, bounding_box=(10, 20, 300, 200)
    )
    entry = _make_entry("e1")
    entry.media = [blob]
    await store.save(entry)
    result = await store.get("e1")
    assert len(result.media) == 1
    assert result.media[0].blob_id == "b1"
    assert result.media[0].role == "diagram"
    assert result.media[0].data == b"\x89PNG\r\n"
