import json
import uuid
import aiosqlite
from knowledge_base.models.session import Session


class SessionManager:
    def __init__(self, db_path: str = "sessions.db"):
        self.db_path = db_path

    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    document_type TEXT,
                    active_module TEXT,
                    step_state TEXT,
                    known_facts TEXT,
                    resolved_modules TEXT,
                    user_vocabulary TEXT,
                    urgency TEXT DEFAULT 'normal',
                    expertise_level TEXT DEFAULT 'intermediate'
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    turn_number INTEGER,
                    raw_transcript TEXT,
                    response_speech TEXT,
                    action TEXT,
                    trace_id TEXT
                )
            """)
            await db.commit()

    async def create(self, document_id: str, document_type: str) -> Session:
        session = Session(
            session_id=str(uuid.uuid4()),
            document_id=document_id,
            document_type=document_type,
            active_module=None,
            step_state={},
            known_facts={},
            resolved_modules=[],
            turn_history=[],
            user_vocabulary={},
            urgency="normal",
            expertise_level="intermediate",
        )
        await self.save(session)
        return session

    async def save(self, session: Session):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    session.session_id,
                    session.document_id,
                    session.document_type,
                    session.active_module,
                    json.dumps(session.step_state),
                    json.dumps(session.known_facts),
                    json.dumps(session.resolved_modules),
                    json.dumps(session.user_vocabulary),
                    session.urgency,
                    session.expertise_level,
                ),
            )
            await db.commit()

    async def get(self, session_id: str) -> Session | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE session_id=?", (session_id,)
            ) as cur:
                row = await cur.fetchone()
        if not row:
            return None
        return Session(
            session_id=row["session_id"],
            document_id=row["document_id"],
            document_type=row["document_type"],
            active_module=row["active_module"],
            step_state=json.loads(row["step_state"]),
            known_facts=json.loads(row["known_facts"]),
            resolved_modules=json.loads(row["resolved_modules"]),
            turn_history=[],
            user_vocabulary=json.loads(row["user_vocabulary"]),
            urgency=row["urgency"],
            expertise_level=row["expertise_level"],
        )

    async def update_module(self, session_id: str, module_id: str | None):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE sessions SET active_module=? WHERE session_id=?",
                (module_id, session_id),
            )
            await db.commit()
