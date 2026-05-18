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
                    entry_references TEXT NOT NULL,
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
                json.dumps(entry.references),       # stored as entry_references
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
            references=json.loads(row["entry_references"]),
            referenced_by=json.loads(row["referenced_by"]),
            ingestion_trace_id=row["ingestion_trace_id"],
            confidence_score=row["confidence_score"],
            requires_review=bool(row["requires_review"])
        )
