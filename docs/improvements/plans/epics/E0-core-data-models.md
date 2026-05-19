# E0 — Core Data Models & Knowledge Store

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 4.1–4.3) before starting.

**Goal:** Define all shared dataclasses and implement the SQLite-backed KnowledgeStore.

**Wave:** 1 — No dependencies. Start immediately.

**Tech Stack:** Python 3.11+, aiosqlite, pytest-asyncio

---

## Files to Create

- `knowledge_base/__init__.py`
- `knowledge_base/models/__init__.py`
- `knowledge_base/models/entry.py`
- `knowledge_base/store/__init__.py`
- `knowledge_base/store/knowledge_store.py`
- `tests/__init__.py`
- `tests/knowledge_base/__init__.py`
- `tests/knowledge_base/test_models.py`
- `tests/knowledge_base/test_store.py`

## Modify

- `requirements.txt` — add `aiosqlite`

---

## Task E0-1: KnowledgeEntry and MediaBlob models

**Files:** Create `knowledge_base/models/entry.py`, `tests/knowledge_base/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/knowledge_base/test_models.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```
pytest tests/knowledge_base/test_models.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create package init files**

```python
# knowledge_base/__init__.py
# knowledge_base/models/__init__.py
# tests/__init__.py
# tests/knowledge_base/__init__.py
```
(all empty)

- [ ] **Step 4: Create `knowledge_base/models/entry.py`**

```python
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
```

- [ ] **Step 5: Run test to verify it passes**

```
pytest tests/knowledge_base/test_models.py -v
```
Expected: 3 tests PASS

- [ ] **Step 6: Commit**

```bash
git add knowledge_base/ tests/knowledge_base/test_models.py
git commit -m "feat(E0): add KnowledgeEntry and MediaBlob dataclasses"
```

---

## Task E0-2: Add aiosqlite dependency

- [ ] **Step 1: Add to requirements.txt**

Open `requirements.txt` and add:
```
aiosqlite==0.20.0
```

- [ ] **Step 2: Install**

```
pip install aiosqlite==0.20.0
```

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "chore(E0): add aiosqlite dependency"
```

---

## Task E0-3: SQLite KnowledgeStore

**Files:** Create `knowledge_base/store/knowledge_store.py`, `tests/knowledge_base/test_store.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/knowledge_base/test_store.py
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
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_store.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/store/__init__.py`** (empty)

- [ ] **Step 4: Create `knowledge_base/store/knowledge_store.py`**

```python
import json
import aiosqlite
from knowledge_base.models.entry import KnowledgeEntry, MediaBlob

class KnowledgeStore:
    def __init__(self, db_path: str = "knowledge_base.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS entries (
                    id TEXT PRIMARY KEY,
                    source_document TEXT NOT NULL,
                    entry_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    vernacular_terms TEXT NOT NULL,
                    structured_data TEXT NOT NULL,
                    references TEXT NOT NULL,
                    referenced_by TEXT NOT NULL,
                    ingestion_trace_id TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    requires_review INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS media_blobs (
                    blob_id TEXT PRIMARY KEY,
                    entry_id TEXT NOT NULL,
                    media_type TEXT NOT NULL,
                    role TEXT NOT NULL,
                    data BLOB NOT NULL,
                    descriptions TEXT NOT NULL,
                    source_page INTEGER NOT NULL,
                    bounding_box TEXT NOT NULL,
                    FOREIGN KEY (entry_id) REFERENCES entries(id)
                )
            """)
            await db.commit()

    async def save(self, entry: KnowledgeEntry) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO entries
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                entry.id, entry.source_document, entry.entry_type,
                entry.title, entry.summary,
                json.dumps(entry.tags),
                entry.raw_text,
                json.dumps(entry.vernacular_terms),
                json.dumps(entry.structured_data),
                json.dumps(entry.references),
                json.dumps(entry.referenced_by),
                entry.ingestion_trace_id,
                entry.confidence_score,
                int(entry.requires_review)
            ))
            # Delete existing blobs for this entry, then re-insert
            await db.execute("DELETE FROM media_blobs WHERE entry_id=?", (entry.id,))
            for blob in entry.media:
                await db.execute("""
                    INSERT INTO media_blobs VALUES (?,?,?,?,?,?,?,?)
                """, (
                    blob.blob_id, entry.id, blob.media_type, blob.role,
                    blob.data,
                    json.dumps(blob.descriptions),
                    blob.source_page,
                    json.dumps(list(blob.bounding_box))
                ))
            await db.commit()

    async def get(self, entry_id: str) -> KnowledgeEntry | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM entries WHERE id=?", (entry_id,)
            ) as cur:
                row = await cur.fetchone()
            if row is None:
                return None
            blobs = await self._load_blobs(db, entry_id)
        return self._row_to_entry(row, blobs)

    async def search_by_tag(self, tag: str) -> list[KnowledgeEntry]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM entries WHERE tags LIKE ?',
                (f'%"{tag}"%',)
            ) as cur:
                rows = await cur.fetchall()
        return [self._row_to_entry(r, []) for r in rows]

    async def search_by_vernacular(self, term: str) -> list[KnowledgeEntry]:
        # Tokenize term and match any token against vernacular_terms
        tokens = term.lower().split()
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            results = []
            seen = set()
            for token in tokens:
                async with db.execute(
                    'SELECT * FROM entries WHERE LOWER(vernacular_terms) LIKE ?',
                    (f'%{token}%',)
                ) as cur:
                    rows = await cur.fetchall()
                for r in rows:
                    if r["id"] not in seen:
                        seen.add(r["id"])
                        results.append(self._row_to_entry(r, []))
        return results

    async def list_by_document(self, source_document: str) -> list[KnowledgeEntry]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM entries WHERE source_document=?", (source_document,)
            ) as cur:
                rows = await cur.fetchall()
        return [self._row_to_entry(r, []) for r in rows]

    async def _load_blobs(self, db: aiosqlite.Connection, entry_id: str) -> list[MediaBlob]:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM media_blobs WHERE entry_id=?", (entry_id,)
        ) as cur:
            rows = await cur.fetchall()
        return [
            MediaBlob(
                blob_id=r["blob_id"],
                media_type=r["media_type"],
                role=r["role"],
                data=bytes(r["data"]),
                descriptions=json.loads(r["descriptions"]),
                source_page=r["source_page"],
                bounding_box=tuple(json.loads(r["bounding_box"]))
            )
            for r in rows
        ]

    def _row_to_entry(self, row, blobs: list[MediaBlob]) -> KnowledgeEntry:
        return KnowledgeEntry(
            id=row["id"],
            source_document=row["source_document"],
            entry_type=row["entry_type"],
            title=row["title"],
            summary=row["summary"],
            tags=json.loads(row["tags"]),
            raw_text=row["raw_text"],
            vernacular_terms=json.loads(row["vernacular_terms"]),
            structured_data=json.loads(row["structured_data"]),
            media=blobs,
            references=json.loads(row["references"]),
            referenced_by=json.loads(row["referenced_by"]),
            ingestion_trace_id=row["ingestion_trace_id"],
            confidence_score=row["confidence_score"],
            requires_review=bool(row["requires_review"])
        )
```

- [ ] **Step 5: Add pytest-asyncio config to `pytest.ini` (or `pyproject.toml`)**

Create `pytest.ini` at project root if it doesn't exist:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 6: Run tests to verify they pass**

```
pytest tests/knowledge_base/test_store.py -v
```
Expected: 7 tests PASS

- [ ] **Step 7: Run full test suite to check for regressions**

```
pytest tests/ -v
```

- [ ] **Step 8: Commit**

```bash
git add knowledge_base/store/ tests/knowledge_base/test_store.py pytest.ini
git commit -m "feat(E0): add SQLite KnowledgeStore with CRUD, tag, and vernacular search"
```

---

## Verification

```
pytest tests/knowledge_base/ -v
```
Expected: 10+ tests PASS, 0 failures.
