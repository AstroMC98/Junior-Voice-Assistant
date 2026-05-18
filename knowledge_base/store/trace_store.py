import json
import aiosqlite
from datetime import datetime
from knowledge_base.models.trace import TraceEvent


class TraceStore:
    def __init__(self, db_path: str = "traces.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS traces (
                    trace_id TEXT PRIMARY KEY,
                    parent_trace_id TEXT,
                    span_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
                    workflow_id TEXT,
                    tier INTEGER NOT NULL,
                    timestamp_start TEXT NOT NULL,
                    timestamp_end TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    input_data TEXT NOT NULL,
                    output_data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    failure_type TEXT,
                    failure_detail TEXT,
                    session_id TEXT,
                    document_id TEXT,
                    token_count_in INTEGER,
                    token_count_out INTEGER,
                    model_id TEXT
                )
            """)
            await db.commit()

    async def save(self, event: TraceEvent) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO traces VALUES
                (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                event.trace_id, event.parent_trace_id, event.span_id,
                event.event_type, event.agent_name, event.workflow_id, event.tier,
                event.timestamp_start.isoformat(), event.timestamp_end.isoformat(),
                event.duration_ms,
                json.dumps(event.input_data), json.dumps(event.output_data),
                event.status, event.failure_type, event.failure_detail,
                event.session_id, event.document_id,
                event.token_count_in, event.token_count_out, event.model_id
            ))
            await db.commit()

    async def query_by_document(self, document_id: str | None) -> list[TraceEvent]:
        if document_id is None:
            return await self._query("SELECT * FROM traces", ())
        return await self._query(
            "SELECT * FROM traces WHERE document_id=?", (document_id,)
        )

    async def query_by_session(self, session_id: str) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE session_id=?", (session_id,)
        )

    async def query_failures(self) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE status='failure'", ()
        )

    async def query_slow(self, threshold_ms: int) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE duration_ms>?", (threshold_ms,)
        )

    async def query_by_tier(self, tier: int) -> list[TraceEvent]:
        return await self._query(
            "SELECT * FROM traces WHERE tier=?", (tier,)
        )

    async def _query(self, sql: str, params: tuple) -> list[TraceEvent]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(sql, params) as cur:
                rows = await cur.fetchall()
        return [self._row_to_event(r) for r in rows]

    def _row_to_event(self, row) -> TraceEvent:
        return TraceEvent(
            trace_id=row["trace_id"],
            parent_trace_id=row["parent_trace_id"],
            span_id=row["span_id"],
            event_type=row["event_type"],
            agent_name=row["agent_name"],
            workflow_id=row["workflow_id"],
            tier=row["tier"],
            timestamp_start=datetime.fromisoformat(row["timestamp_start"]),
            timestamp_end=datetime.fromisoformat(row["timestamp_end"]),
            duration_ms=row["duration_ms"],
            input_data=json.loads(row["input_data"]),
            output_data=json.loads(row["output_data"]),
            status=row["status"],
            failure_type=row["failure_type"],
            failure_detail=row["failure_detail"],
            session_id=row["session_id"],
            document_id=row["document_id"],
            token_count_in=row["token_count_in"],
            token_count_out=row["token_count_out"],
            model_id=row["model_id"]
        )
