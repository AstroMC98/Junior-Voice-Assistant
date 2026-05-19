# E6 — Router & Session Management

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 6.2, 8) before starting.

**Goal:** Implement the query `Router` (a classifier, not an orchestrator), `SessionManager` (SQLite persistence), and `IdentifierAgent` (3-way parallel search across tag, vernacular, and embedding indexes).

**Wave:** 2 — Requires E0 (models) and E1 (tracing). Parallel with E2, E3, E5.

**Tech Stack:** Python 3.11+, asyncio, aiosqlite, anthropic SDK, pytest-asyncio

---

## Files to Create

- `knowledge_base/query/router.py`
- `knowledge_base/query/session_manager.py`
- `knowledge_base/query/agents/__init__.py`
- `knowledge_base/query/agents/identifier.py`
- `knowledge_base/query/agents/retriever.py`
- `tests/knowledge_base/test_router.py`
- `tests/knowledge_base/test_session_manager.py`

---

## Task E6-1: Router

**File:** `knowledge_base/query/router.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/knowledge_base/test_router.py
import pytest
from knowledge_base.query.router import Router
from knowledge_base.models.session import ProcessedQuery, Session

def _make_session(active_module: str | None = None) -> Session:
    return Session(
        session_id="s1", document_id="doc1", document_type="game_manual",
        active_module=active_module, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[],
        user_vocabulary={}, urgency="normal", expertise_level="intermediate"
    )

def _make_query(text: str, entities: dict | None = None) -> ProcessedQuery:
    return ProcessedQuery(
        cleaned_text=text, extracted_entities=entities or {},
        uncertainty_flags=[], corrections_detected=[],
        references_to_resolve=[], raw_text=text
    )

def test_router_stateful_continuation_when_active_module_and_next():
    router = Router()
    session = _make_session(active_module="entry_abc")
    query = _make_query("what's next")
    workflow, params = router.classify(query, session, "game_manual")
    assert workflow == "stateful_continuation"

def test_router_instruction_when_active_module_and_how():
    router = Router()
    session = _make_session(active_module="entry_abc")
    query = _make_query("how do I do this")
    workflow, params = router.classify(query, session, "game_manual")
    assert workflow == "instruction"
    assert params.get("module_id") == "entry_abc"

def test_router_identification_when_no_module_and_colors():
    router = Router()
    session = _make_session()
    query = _make_query("I have a red and blue wire", entities={"colors": ["red", "blue"]})
    workflow, params = router.classify(query, session, "game_manual")
    assert workflow == "identification"

def test_router_lookup_for_fact_query():
    router = Router()
    session = _make_session()
    query = _make_query("what is a parallel port")
    workflow, params = router.classify(query, session, "game_manual")
    assert workflow == "lookup"

def test_router_returns_none_for_ambiguous():
    router = Router()
    session = _make_session()
    query = _make_query("the thing")
    workflow, params = router.classify(query, session, "game_manual")
    assert workflow is None

def test_router_continue_triggers_stateful():
    router = Router()
    session = _make_session(active_module="entry_xyz")
    query = _make_query("continue")
    workflow, _ = router.classify(query, session, "game_manual")
    assert workflow == "stateful_continuation"

def test_router_instruction_on_assembly_guide_defaults():
    router = Router()
    session = _make_session(active_module="step_3")
    query = _make_query("instructions please")
    workflow, _ = router.classify(query, session, "assembly_guide")
    assert workflow == "instruction"
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_router.py -v
```
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Create `knowledge_base/query/router.py`**

```python
from knowledge_base.models.session import ProcessedQuery, Session

STATEFUL_TRIGGERS = {"next", "continue", "what's next", "whats next", "done", "go on", "keep going"}
INSTRUCTION_TRIGGERS = {"how", "what do i do", "instructions", "steps", "tell me what to do", "guide me"}
LOOKUP_TRIGGERS = {"what is", "what's", "tell me about", "define", "explain"}

class Router:
    def classify(
        self,
        query: ProcessedQuery,
        session: Session,
        document_type: str
    ) -> tuple[str | None, dict]:
        """
        Returns (workflow_id, params) or (None, {}) if no confident match.
        This is a classifier — it selects from a fixed menu of workflows.
        It does NOT orchestrate or create new workflows.
        """
        text = query.cleaned_text.lower().strip()
        entities = query.extracted_entities
        has_active_module = session.active_module is not None

        # Priority 1: Stateful continuation — active module + progress trigger
        if has_active_module and any(trigger in text for trigger in STATEFUL_TRIGGERS):
            return "stateful_continuation", {}

        # Priority 2: Instruction — active module + "how" / action request
        if has_active_module and any(trigger in text for trigger in INSTRUCTION_TRIGGERS):
            return "instruction", {"module_id": session.active_module}

        # Priority 3: Lookup — specific fact query, no visual entities
        if any(text.startswith(t) for t in LOOKUP_TRIGGERS) and not entities.get("colors"):
            return "lookup", {}

        # Priority 4: Identification — visual description with no active module
        has_visual_entities = any(
            entities.get(k) for k in ("colors", "positions", "labels")
        )
        if not has_active_module and has_visual_entities:
            return "identification", {}

        # Document type biases for fallthrough
        if document_type in ("assembly_guide", "recipe") and has_active_module:
            return "stateful_continuation", {}

        if document_type == "reference_manual":
            return "lookup", {}

        return None, {}
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_router.py -v
```
Expected: 7 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/query/router.py tests/knowledge_base/test_router.py
git commit -m "feat(E6): add Router with deterministic workflow classification"
```

---

## Task E6-2: SessionManager (SQLite persistence)

**File:** `knowledge_base/query/session_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/knowledge_base/test_session_manager.py
import pytest
from knowledge_base.query.session_manager import SessionManager
from knowledge_base.models.session import Session

@pytest.fixture
async def manager(tmp_path):
    m = SessionManager(db_path=str(tmp_path / "sessions.db"))
    await m.init()
    return m

@pytest.mark.asyncio
async def test_create_and_get_session(manager):
    session = await manager.create(document_id="doc1", document_type="game_manual")
    assert session.session_id is not None
    assert session.urgency == "normal"

    retrieved = await manager.get(session.session_id)
    assert retrieved is not None
    assert retrieved.document_id == "doc1"
    assert retrieved.document_type == "game_manual"

@pytest.mark.asyncio
async def test_get_nonexistent_returns_none(manager):
    result = await manager.get("nonexistent-id")
    assert result is None

@pytest.mark.asyncio
async def test_save_updates_session(manager):
    session = await manager.create("doc1", "game_manual")
    session.active_module = "module_wire_cutting"
    session.known_facts = {"serial_last": 7, "batteries": 2}
    session.urgency = "high"
    await manager.save(session)

    retrieved = await manager.get(session.session_id)
    assert retrieved.active_module == "module_wire_cutting"
    assert retrieved.known_facts["batteries"] == 2
    assert retrieved.urgency == "high"

@pytest.mark.asyncio
async def test_add_resolved_module(manager):
    session = await manager.create("doc1", "game_manual")
    session.resolved_modules = ["mod1", "mod2"]
    await manager.save(session)

    retrieved = await manager.get(session.session_id)
    assert "mod1" in retrieved.resolved_modules
    assert "mod2" in retrieved.resolved_modules

@pytest.mark.asyncio
async def test_user_vocabulary_persists(manager):
    session = await manager.create("doc1", "game_manual")
    session.user_vocabulary = {"the wide one": "parallel_port"}
    await manager.save(session)

    retrieved = await manager.get(session.session_id)
    assert retrieved.user_vocabulary == {"the wide one": "parallel_port"}
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_session_manager.py -v
```

- [ ] **Step 3: Create `knowledge_base/query/session_manager.py`**

```python
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
                    document_id TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    active_module TEXT,
                    step_state TEXT NOT NULL DEFAULT '{}',
                    known_facts TEXT NOT NULL DEFAULT '{}',
                    resolved_modules TEXT NOT NULL DEFAULT '[]',
                    user_vocabulary TEXT NOT NULL DEFAULT '{}',
                    urgency TEXT NOT NULL DEFAULT 'normal',
                    expertise_level TEXT NOT NULL DEFAULT 'intermediate'
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
            expertise_level="intermediate"
        )
        await self.save(session)
        return session

    async def save(self, session: Session) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?)
            """, (
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
            ))
            await db.commit()

    async def get(self, session_id: str) -> Session | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM sessions WHERE session_id=?", (session_id,)
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            return None
        return Session(
            session_id=row["session_id"],
            document_id=row["document_id"],
            document_type=row["document_type"],
            active_module=row["active_module"],
            step_state=json.loads(row["step_state"]),
            known_facts=json.loads(row["known_facts"]),
            resolved_modules=json.loads(row["resolved_modules"]),
            turn_history=[],  # turns not persisted in this table
            user_vocabulary=json.loads(row["user_vocabulary"]),
            urgency=row["urgency"],
            expertise_level=row["expertise_level"],
        )
```

- [ ] **Step 4: Run tests**

```
pytest tests/knowledge_base/test_session_manager.py -v
```
Expected: 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/query/session_manager.py tests/knowledge_base/test_session_manager.py
git commit -m "feat(E6): add SQLite SessionManager with full persistence"
```

---

## Task E6-3: IdentifierAgent (3-way parallel search)

**File:** `knowledge_base/query/agents/identifier.py`

- [ ] **Step 1: Write failing test**

```python
# Append to tests/knowledge_base/test_router.py
import asyncio
from unittest.mock import AsyncMock, MagicMock
from knowledge_base.query.agents.identifier import IdentifierAgent, Candidate

@pytest.mark.asyncio
async def test_identifier_merges_tag_and_vernacular():
    mock_store = MagicMock()
    mock_entry_a = MagicMock()
    mock_entry_a.id = "entry_a"
    mock_entry_b = MagicMock()
    mock_entry_b.id = "entry_b"

    mock_store.search_by_tag = AsyncMock(return_value=[mock_entry_a])
    mock_store.search_by_vernacular = AsyncMock(return_value=[mock_entry_b])

    agent = IdentifierAgent(store=mock_store)
    query = _make_query("red wire", entities={"colors": ["red"]})
    candidates = await agent.identify(query)

    assert len(candidates) == 2
    ids = {c.entry_id for c in candidates}
    assert "entry_a" in ids
    assert "entry_b" in ids

@pytest.mark.asyncio
async def test_identifier_deduplicates_same_entry():
    mock_store = MagicMock()
    mock_entry = MagicMock()
    mock_entry.id = "entry_x"

    mock_store.search_by_tag = AsyncMock(return_value=[mock_entry])
    mock_store.search_by_vernacular = AsyncMock(return_value=[mock_entry])

    agent = IdentifierAgent(store=mock_store)
    query = _make_query("parallel port", entities={"labels": ["parallel port"]})
    candidates = await agent.identify(query)

    assert len(candidates) == 1

@pytest.mark.asyncio
async def test_identifier_ranks_by_confidence():
    mock_store = MagicMock()
    mock_a = MagicMock(); mock_a.id = "a"
    mock_b = MagicMock(); mock_b.id = "b"

    mock_store.search_by_tag = AsyncMock(return_value=[mock_a])
    mock_store.search_by_vernacular = AsyncMock(return_value=[mock_b, mock_a])

    agent = IdentifierAgent(store=mock_store)
    query = _make_query("something", entities={"labels": ["x"]})
    candidates = await agent.identify(query)

    # Entry 'a' appeared in both searches — should have higher confidence
    top = candidates[0]
    assert top.entry_id == "a"
```

- [ ] **Step 2: Create `knowledge_base/query/agents/__init__.py`** (empty)

- [ ] **Step 3: Create `knowledge_base/query/agents/identifier.py`**

```python
import asyncio
from dataclasses import dataclass
from knowledge_base.models.session import ProcessedQuery
from knowledge_base.store.knowledge_store import KnowledgeStore

@dataclass
class Candidate:
    entry_id: str
    confidence: float
    match_reason: str

class IdentifierAgent:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def identify(self, query: ProcessedQuery) -> list[Candidate]:
        """
        Runs tag search and vernacular search in parallel.
        Merges results, deduplicates, and ranks by confidence.
        """
        tag_results, vernacular_results = await asyncio.gather(
            self._tag_search(query),
            self._vernacular_search(query)
        )
        return self._merge_and_rank(tag_results, vernacular_results)

    async def _tag_search(self, query: ProcessedQuery) -> list[Candidate]:
        all_entity_values = [
            str(v)
            for vals in query.extracted_entities.values()
            for v in (vals if isinstance(vals, list) else [vals])
        ]
        candidates = []
        for entity in all_entity_values:
            entries = await self.store.search_by_tag(entity)
            for entry in entries:
                candidates.append(Candidate(
                    entry_id=entry.id,
                    confidence=0.65,
                    match_reason=f"tag_match:{entity}"
                ))
        return candidates

    async def _vernacular_search(self, query: ProcessedQuery) -> list[Candidate]:
        entries = await self.store.search_by_vernacular(query.cleaned_text[:150])
        return [
            Candidate(entry_id=entry.id, confidence=0.75, match_reason="vernacular_match")
            for entry in entries
        ]

    def _merge_and_rank(self, *result_lists: list[Candidate]) -> list[Candidate]:
        # Merge: keep highest confidence per entry_id, boost if seen multiple times
        seen: dict[str, Candidate] = {}
        for candidates in result_lists:
            for c in candidates:
                if c.entry_id not in seen:
                    seen[c.entry_id] = c
                else:
                    # Entry appeared in multiple searches — boost confidence
                    existing = seen[c.entry_id]
                    boosted = min(existing.confidence + 0.15, 1.0)
                    seen[c.entry_id] = Candidate(
                        entry_id=c.entry_id,
                        confidence=boosted,
                        match_reason=f"{existing.match_reason}+{c.match_reason}"
                    )
        return sorted(seen.values(), key=lambda c: c.confidence, reverse=True)
```

- [ ] **Step 4: Create `knowledge_base/query/agents/retriever.py`**

```python
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.models.entry import KnowledgeEntry
from knowledge_base.models.session import ProcessedQuery

class RetrieverAgent:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def retrieve(self, query: ProcessedQuery, entry_id: str) -> KnowledgeEntry | None:
        return await self.store.get(entry_id)

    async def retrieve_many(self, entry_ids: list[str]) -> list[KnowledgeEntry]:
        import asyncio
        results = await asyncio.gather(*[self.store.get(eid) for eid in entry_ids])
        return [r for r in results if r is not None]
```

- [ ] **Step 5: Run all E6 tests**

```
pytest tests/knowledge_base/test_router.py tests/knowledge_base/test_session_manager.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add knowledge_base/query/agents/ tests/knowledge_base/test_router.py tests/knowledge_base/test_session_manager.py
git commit -m "feat(E6): add IdentifierAgent (parallel search), RetrieverAgent, SessionManager"
```

---

## Verification

```
pytest tests/knowledge_base/test_router.py tests/knowledge_base/test_session_manager.py -v
```
Expected: 15+ tests PASS, 0 failures.
