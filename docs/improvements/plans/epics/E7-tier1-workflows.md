# E7 — Tier 1 Query Workflows

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Section 6.3, all sub-sections) before starting. Each workflow is detailed there.

**Goal:** Implement all 5 deterministic Tier 1 workflows with typed handoffs and typed failure returns. Also implement the supporting query agents: `ContextGatherer`, `InstructionWalker`, `PrerequisiteChecker`, `InfoGatherer`, `StateManager`, `Responder`.

**Wave:** 3 — Requires E5 (voice models) and E6 (router, session, identifier) to be merged first.

**Tech Stack:** Python 3.11+, asyncio, anthropic SDK, pytest-asyncio

---

## Files to Create

- `knowledge_base/query/workflows/__init__.py`
- `knowledge_base/query/workflows/base.py`
- `knowledge_base/query/workflows/identification.py`
- `knowledge_base/query/workflows/instruction.py`
- `knowledge_base/query/workflows/lookup.py`
- `knowledge_base/query/workflows/disambiguation.py`
- `knowledge_base/query/workflows/stateful_continuation.py`
- `knowledge_base/query/agents/context_gatherer.py`
- `knowledge_base/query/agents/instruction_walker.py`
- `knowledge_base/query/agents/prerequisite_checker.py`
- `knowledge_base/query/agents/info_gatherer.py`
- `knowledge_base/query/agents/state_manager.py`
- `knowledge_base/query/agents/responder.py`
- `tests/knowledge_base/test_workflows.py`

---

## Task E7-1: Base workflow and typed failures

**File:** `knowledge_base/query/workflows/base.py`

- [ ] **Step 1: Write failing test**

```python
# tests/knowledge_base/test_workflows.py
import pytest
from knowledge_base.query.workflows.base import WorkflowResult, TYPED_FAILURES

def test_workflow_result_success():
    r = WorkflowResult(success=True, response="Cut the wire.", failure_type=None, failure_context={})
    assert r.success is True
    assert r.response == "Cut the wire."

def test_workflow_result_failure():
    r = WorkflowResult(
        success=False, response=None,
        failure_type="ZERO_MATCHES",
        failure_context={"query": "the purple thing"}
    )
    assert r.success is False
    assert r.failure_type == "ZERO_MATCHES"

def test_typed_failures_contains_expected_keys():
    assert "ZERO_MATCHES" in TYPED_FAILURES
    assert "AMBIGUOUS_MATCH" in TYPED_FAILURES
    assert "MISSING_PREREQUISITE" in TYPED_FAILURES
    assert "CONFIDENCE_TOO_LOW" in TYPED_FAILURES
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_workflows.py -k "workflow_result or typed_failures" -v
```

- [ ] **Step 3: Create `knowledge_base/query/workflows/__init__.py`** (empty)

- [ ] **Step 4: Create `knowledge_base/query/workflows/base.py`**

```python
from dataclasses import dataclass
from knowledge_base.models.session import ProcessedQuery, Session

# All typed failure codes — exhaustive list
TYPED_FAILURES = {
    "ZERO_MATCHES": "No knowledge entries matched the query",
    "AMBIGUOUS_MATCH": "Multiple candidates above threshold; need disambiguation",
    "MISSING_PREREQUISITE": "Entry requires facts not yet known from session",
    "ENTRY_TYPE_UNSUPPORTED": "Entry type has no workflow handler",
    "CONFIDENCE_TOO_LOW": "Best match confidence below usable threshold",
}

@dataclass
class WorkflowResult:
    success: bool
    response: str | None          # voice-ready response when success=True
    failure_type: str | None      # one of TYPED_FAILURES keys when success=False
    failure_context: dict         # full context for Tier 2 recovery

class BaseWorkflow:
    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        raise NotImplementedError
```

- [ ] **Step 5: Run tests, commit**

```bash
git add knowledge_base/query/workflows/ tests/knowledge_base/test_workflows.py
git commit -m "feat(E7): add base workflow types and typed failure codes"
```

---

## Task E7-2: ContextGatherer and Responder agents

**Files:** `knowledge_base/query/agents/context_gatherer.py`, `knowledge_base/query/agents/responder.py`

- [ ] **Step 1: Add tests**

```python
from unittest.mock import AsyncMock, MagicMock
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.models.entry import KnowledgeEntry, MediaBlob

@pytest.mark.asyncio
async def test_context_gatherer_fetches_entry_and_references():
    mock_store = MagicMock()
    mock_entry = MagicMock(spec=KnowledgeEntry)
    mock_entry.id = "e1"
    mock_entry.references = ["e2"]
    mock_entry.media = []
    mock_ref = MagicMock(spec=KnowledgeEntry)
    mock_ref.id = "e2"
    mock_ref.media = []

    mock_store.get = AsyncMock(side_effect=lambda eid: mock_entry if eid == "e1" else mock_ref)
    gatherer = ContextGatherer(store=mock_store)
    context = await gatherer.gather("e1")
    assert context["entry"].id == "e1"
    assert len(context["referenced_entries"]) == 1
    assert context["referenced_entries"][0].id == "e2"

@pytest.mark.asyncio
async def test_context_gatherer_handles_missing_entry():
    mock_store = MagicMock()
    mock_store.get = AsyncMock(return_value=None)
    gatherer = ContextGatherer(store=mock_store)
    context = await gatherer.gather("missing_id")
    assert context["entry"] is None
```

- [ ] **Step 2: Create `knowledge_base/query/agents/context_gatherer.py`**

```python
import asyncio
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.models.entry import KnowledgeEntry

class ContextGatherer:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    async def gather(self, entry_id: str) -> dict:
        entry = await self.store.get(entry_id)
        if entry is None:
            return {"entry": None, "referenced_entries": [], "media_descriptions": []}

        # Fetch referenced entries in parallel (speculative)
        ref_results = await asyncio.gather(
            *[self.store.get(ref_id) for ref_id in entry.references],
            return_exceptions=True
        )
        referenced = [r for r in ref_results if isinstance(r, KnowledgeEntry)]

        # Collect all media descriptions
        media_descriptions = [
            {
                "blob_id": blob.blob_id,
                "role": blob.role,
                "descriptions": blob.descriptions
            }
            for blob in entry.media
        ]

        return {
            "entry": entry,
            "referenced_entries": referenced,
            "media_descriptions": media_descriptions
        }
```

- [ ] **Step 3: Create `knowledge_base/query/agents/responder.py`**

```python
import json
import anthropic
from knowledge_base.models.session import Session

anthropic_client = anthropic.AsyncAnthropic()

class Responder:
    async def respond_identification(self, context: dict, session: Session) -> str:
        entry = context["entry"]
        if entry is None:
            return "I couldn't find that in my knowledge base."

        media_hints = ""
        if context.get("media_descriptions"):
            for md in context["media_descriptions"][:2]:  # limit
                desc = md["descriptions"].get("layperson", "")
                if desc:
                    media_hints += f" It looks like: {desc}."

        prompt = (
            f"You found: {entry.title}. {entry.summary}.{media_hints} "
            "Confirm this identification in one concise spoken sentence."
        )
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            system="You are a voice assistant. Respond in one clear spoken sentence. No lists, no markdown.",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()

    async def respond_instruction(self, instruction: str, session: Session) -> str:
        urgency = session.urgency
        if urgency == "high":
            # Strip to essential action
            sentences = [s.strip() for s in instruction.split(".") if s.strip()]
            return sentences[0] + "." if sentences else instruction
        return instruction

    async def respond_lookup(self, entry_title: str, data_point: str, session: Session) -> str:
        return f"For {entry_title}: {data_point}"
```

- [ ] **Step 4: Run, commit**

```bash
git add knowledge_base/query/agents/context_gatherer.py knowledge_base/query/agents/responder.py
git commit -m "feat(E7): add ContextGatherer and Responder agents"
```

---

## Task E7-3: IdentificationWorkflow

**File:** `knowledge_base/query/workflows/identification.py`

- [ ] **Step 1: Add tests**

```python
from unittest.mock import AsyncMock, MagicMock, patch
from knowledge_base.query.workflows.identification import IdentificationWorkflow
from knowledge_base.query.agents.identifier import Candidate
from knowledge_base.models.session import ProcessedQuery, Session

def _make_session():
    return Session(
        session_id="s1", document_id="doc1", document_type="game_manual",
        active_module=None, step_state={}, known_facts={},
        resolved_modules=[], turn_history=[],
        user_vocabulary={}, urgency="normal", expertise_level="intermediate"
    )

def _make_query(text: str):
    return ProcessedQuery(
        cleaned_text=text, extracted_entities={"colors": ["red"]},
        uncertainty_flags=[], corrections_detected=[],
        references_to_resolve=[], raw_text=text
    )

@pytest.mark.asyncio
async def test_identification_success_with_high_confidence():
    mock_identifier = MagicMock()
    mock_identifier.identify = AsyncMock(return_value=[
        Candidate(entry_id="e1", confidence=0.92, match_reason="tag_match:red")
    ])
    mock_gatherer = MagicMock()
    mock_gatherer.gather = AsyncMock(return_value={
        "entry": MagicMock(id="e1", title="Simple Wires", summary="Wire cutting rules", media=[], references=[]),
        "referenced_entries": [],
        "media_descriptions": []
    })
    mock_responder = MagicMock()
    mock_responder.respond_identification = AsyncMock(return_value="Found Simple Wires module.")

    workflow = IdentificationWorkflow(mock_identifier, mock_gatherer, mock_responder)
    session = _make_session()
    result = await workflow.run(_make_query("red wire"), session)

    assert result.success is True
    assert result.response == "Found Simple Wires module."
    assert session.active_module == "e1"

@pytest.mark.asyncio
async def test_identification_zero_matches():
    mock_identifier = MagicMock()
    mock_identifier.identify = AsyncMock(return_value=[])

    workflow = IdentificationWorkflow(mock_identifier, MagicMock(), MagicMock())
    result = await workflow.run(_make_query("purple thing"), _make_session())

    assert result.success is False
    assert result.failure_type == "ZERO_MATCHES"
    assert "query" in result.failure_context

@pytest.mark.asyncio
async def test_identification_ambiguous_match():
    mock_identifier = MagicMock()
    mock_identifier.identify = AsyncMock(return_value=[
        Candidate("e1", 0.55, "tag"),
        Candidate("e2", 0.52, "tag"),
    ])

    workflow = IdentificationWorkflow(mock_identifier, MagicMock(), MagicMock())
    result = await workflow.run(_make_query("the thing"), _make_session())

    assert result.success is False
    assert result.failure_type == "AMBIGUOUS_MATCH"
    assert "candidates" in result.failure_context
```

- [ ] **Step 2: Create `knowledge_base/query/workflows/identification.py`**

```python
from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.identifier import IdentifierAgent
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session

HIGH_CONFIDENCE_THRESHOLD = 0.80
LOW_CONFIDENCE_THRESHOLD = 0.40

class IdentificationWorkflow(BaseWorkflow):
    def __init__(self, identifier: IdentifierAgent, gatherer: ContextGatherer, responder: Responder):
        self.identifier = identifier
        self.gatherer = gatherer
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        candidates = await self.identifier.identify(query)

        if not candidates or candidates[0].confidence < LOW_CONFIDENCE_THRESHOLD:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"query": query.cleaned_text, "candidates": []}
            )

        above_low = [c for c in candidates if c.confidence >= LOW_CONFIDENCE_THRESHOLD]
        has_clear_winner = (
            len(above_low) == 1 or above_low[0].confidence >= HIGH_CONFIDENCE_THRESHOLD
        )

        if not has_clear_winner:
            return WorkflowResult(
                success=False, response=None,
                failure_type="AMBIGUOUS_MATCH",
                failure_context={
                    "candidates": [
                        {"id": c.entry_id, "confidence": c.confidence, "reason": c.match_reason}
                        for c in above_low[:5]
                    ],
                    "query": query.cleaned_text
                }
            )

        best = above_low[0]
        context = await self.gatherer.gather(best.entry_id)
        response = await self.responder.respond_identification(context, session)

        # Update session active module
        session.active_module = best.entry_id

        return WorkflowResult(
            success=True,
            response=response,
            failure_type=None,
            failure_context={}
        )
```

- [ ] **Step 3: Run tests, commit**

```bash
git add knowledge_base/query/workflows/identification.py
git commit -m "feat(E7): add IdentificationWorkflow with typed failure returns"
```

---

## Task E7-4: InstructionWorkflow

**File:** `knowledge_base/query/workflows/instruction.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.query.workflows.instruction import InstructionWorkflow
from knowledge_base.models.entry import KnowledgeEntry

@pytest.mark.asyncio
async def test_instruction_with_all_prerequisites_met():
    mock_checker = MagicMock()
    mock_checker.check = MagicMock(return_value={"met": ["serial_parity"], "missing": []})
    mock_walker = MagicMock()
    mock_walker.walk = AsyncMock(return_value="Cut the last red wire.")
    mock_responder = MagicMock()
    mock_responder.respond_instruction = AsyncMock(return_value="Cut the last red wire.")
    mock_gatherer = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_type = "decision_tree"
    mock_entry.structured_data = {"conditions": ["serial_parity"], "default": "dont_cut"}
    mock_gatherer.gather = AsyncMock(return_value={"entry": mock_entry, "referenced_entries": [], "media_descriptions": []})

    session = _make_session()
    session.active_module = "e1"
    session.known_facts = {"serial_parity": "even"}

    workflow = InstructionWorkflow(mock_gatherer, mock_checker, mock_walker, mock_responder)
    result = await workflow.run(_make_query("how do I do this"), session)

    assert result.success is True

@pytest.mark.asyncio
async def test_instruction_missing_prerequisites():
    mock_checker = MagicMock()
    mock_checker.check = MagicMock(return_value={"met": [], "missing": ["serial_last_digit"]})
    mock_gatherer = MagicMock()
    mock_entry = MagicMock()
    mock_entry.entry_type = "decision_tree"
    mock_entry.structured_data = {}
    mock_gatherer.gather = AsyncMock(return_value={"entry": mock_entry})

    session = _make_session()
    session.active_module = "e1"

    workflow = InstructionWorkflow(mock_gatherer, mock_checker, MagicMock(), MagicMock())
    result = await workflow.run(_make_query("instructions"), session)

    assert result.failure_type == "MISSING_PREREQUISITE"
    assert "serial_last_digit" in str(result.failure_context)
```

- [ ] **Step 2: Create supporting agents**

**`knowledge_base/query/agents/prerequisite_checker.py`:**
```python
from knowledge_base.models.session import Session

class PrerequisiteChecker:
    def check(self, entry_structured_data: dict, session: Session) -> dict:
        """
        Checks which prerequisites from entry are met by session.known_facts.
        Returns {"met": [...], "missing": [...]}.
        Prerequisites are conditions referenced in the entry's structured_data.
        """
        # Extract conditions from common entry types
        conditions = []
        if "conditions" in entry_structured_data:
            conditions = entry_structured_data["conditions"]
        elif "prerequisites" in entry_structured_data:
            conditions = entry_structured_data["prerequisites"]

        met = []
        missing = []
        for condition in conditions:
            # Normalize condition to a key name for lookup
            condition_key = condition.lower().replace(" ", "_")
            if condition_key in session.known_facts:
                met.append(condition_key)
            else:
                missing.append(condition_key)
        return {"met": met, "missing": missing}
```

**`knowledge_base/query/agents/instruction_walker.py`:**
```python
import json
import anthropic
from knowledge_base.models.session import Session

anthropic_client = anthropic.AsyncAnthropic()

class InstructionWalker:
    async def walk(self, entry_structured_data: dict, entry_type: str, session: Session) -> str:
        facts = json.dumps(session.known_facts)
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=(
                "You are evaluating decision logic to produce a single clear instruction. "
                "Use the known facts to traverse any conditions. "
                "Return ONLY the specific action to take in one or two spoken sentences."
            ),
            messages=[{
                "role": "user",
                "content": (
                    f"Entry type: {entry_type}\n"
                    f"Structured data: {json.dumps(entry_structured_data)}\n"
                    f"Known facts: {facts}\n"
                    "What is the specific instruction given these facts?"
                )
            }]
        )
        return response.content[0].text.strip()
```

- [ ] **Step 3: Create `knowledge_base/query/workflows/instruction.py`**

```python
from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.prerequisite_checker import PrerequisiteChecker
from knowledge_base.query.agents.instruction_walker import InstructionWalker
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session

class InstructionWorkflow(BaseWorkflow):
    def __init__(
        self,
        gatherer: ContextGatherer,
        checker: PrerequisiteChecker,
        walker: InstructionWalker,
        responder: Responder
    ):
        self.gatherer = gatherer
        self.checker = checker
        self.walker = walker
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        if not session.active_module:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"reason": "no active module for instruction workflow"}
            )

        context = await self.gatherer.gather(session.active_module)
        entry = context.get("entry")
        if entry is None:
            return WorkflowResult(
                success=False, response=None,
                failure_type="ZERO_MATCHES",
                failure_context={"entry_id": session.active_module}
            )

        prereq_check = self.checker.check(entry.structured_data, session)
        if prereq_check["missing"]:
            return WorkflowResult(
                success=False, response=None,
                failure_type="MISSING_PREREQUISITE",
                failure_context={"missing": prereq_check["missing"], "entry_id": entry.id}
            )

        instruction = await self.walker.walk(entry.structured_data, entry.entry_type, session)
        response = await self.responder.respond_instruction(instruction, session)

        return WorkflowResult(success=True, response=response, failure_type=None, failure_context={})
```

- [ ] **Step 4: Run, commit**

```bash
git add knowledge_base/query/agents/prerequisite_checker.py knowledge_base/query/agents/instruction_walker.py knowledge_base/query/workflows/instruction.py
git commit -m "feat(E7): add InstructionWorkflow with prerequisite checking"
```

---

## Task E7-5: LookupWorkflow, DisambiguationWorkflow, StatefulContinuationWorkflow

**Files:** `lookup.py`, `disambiguation.py`, `stateful_continuation.py`, `state_manager.py`

- [ ] **Step 1: Create `knowledge_base/query/agents/state_manager.py`**

```python
from knowledge_base.models.session import Session

class StateManager:
    def advance(self, session: Session, step_result: dict) -> dict:
        current = session.step_state.get("current_step", 0)
        next_step = current + 1
        session.step_state["current_step"] = next_step
        session.step_state["last_result"] = step_result
        return session.step_state

    def get_next_step(self, structured_data: dict, session: Session) -> dict | None:
        steps = structured_data.get("steps", [])
        current = session.step_state.get("current_step", 0)
        if current < len(steps):
            return steps[current]
        return None  # no more steps
```

- [ ] **Step 2: Create `knowledge_base/query/workflows/lookup.py`**

```python
from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.identifier import IdentifierAgent
from knowledge_base.query.agents.retriever import RetrieverAgent
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session

class LookupWorkflow(BaseWorkflow):
    def __init__(self, identifier: IdentifierAgent, retriever: RetrieverAgent, responder: Responder):
        self.identifier = identifier
        self.retriever = retriever
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        candidates = await self.identifier.identify(query)
        if not candidates:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context={"query": query.cleaned_text})
        best = candidates[0]
        entry = await self.retriever.retrieve(query, best.entry_id)
        if entry is None:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context={"entry_id": best.entry_id})
        response = await self.responder.respond_lookup(entry.title, entry.summary, session)
        return WorkflowResult(success=True, response=response, failure_type=None, failure_context={})
```

- [ ] **Step 3: Create `knowledge_base/query/workflows/disambiguation.py`**

```python
import json
import anthropic
from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session

anthropic_client = anthropic.AsyncAnthropic()

class DisambiguationWorkflow(BaseWorkflow):
    MAX_ROUNDS = 3

    def __init__(self, identifier, gatherer, responder):
        self.identifier = identifier
        self.gatherer = gatherer
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session, candidates: list | None = None) -> WorkflowResult:
        if not candidates:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context={})

        # Generate distinguishing question from top candidates
        candidate_summaries = []
        for c in candidates[:3]:
            ctx = await self.gatherer.gather(c["id"])
            entry = ctx.get("entry")
            if entry:
                candidate_summaries.append(f"- {entry.title}: {entry.summary[:100]}")

        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=128,
            system="You are helping narrow down which item a user is describing. Ask ONE short yes/no or multiple-choice question.",
            messages=[{
                "role": "user",
                "content": (
                    f"User said: '{query.cleaned_text}'\n"
                    f"Possible matches:\n" + "\n".join(candidate_summaries) + "\n"
                    "Ask a single clarifying question to determine which one they mean."
                )
            }]
        )
        question = response.content[0].text.strip()
        return WorkflowResult(success=True, response=question, failure_type=None, failure_context={"awaiting_disambiguation": True, "candidates": candidates})
```

- [ ] **Step 4: Create `knowledge_base/query/workflows/stateful_continuation.py`**

```python
from knowledge_base.query.workflows.base import BaseWorkflow, WorkflowResult
from knowledge_base.query.agents.context_gatherer import ContextGatherer
from knowledge_base.query.agents.state_manager import StateManager
from knowledge_base.query.agents.instruction_walker import InstructionWalker
from knowledge_base.query.agents.responder import Responder
from knowledge_base.models.session import ProcessedQuery, Session

class StatefulContinuationWorkflow(BaseWorkflow):
    def __init__(self, gatherer: ContextGatherer, state_mgr: StateManager, walker: InstructionWalker, responder: Responder):
        self.gatherer = gatherer
        self.state_mgr = state_mgr
        self.walker = walker
        self.responder = responder

    async def run(self, query: ProcessedQuery, session: Session) -> WorkflowResult:
        if not session.active_module:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context={"reason": "no active module"})

        context = await self.gatherer.gather(session.active_module)
        entry = context.get("entry")
        if entry is None:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context={"entry_id": session.active_module})

        next_step = self.state_mgr.get_next_step(entry.structured_data, session)
        if next_step is None:
            session.resolved_modules.append(session.active_module)
            session.active_module = None
            return WorkflowResult(success=True, response="That module is complete. What's next?", failure_type=None, failure_context={})

        instruction = await self.walker.walk({"steps": [next_step]}, entry.entry_type, session)
        self.state_mgr.advance(session, {"step": next_step})
        response = await self.responder.respond_instruction(instruction, session)
        return WorkflowResult(success=True, response=response, failure_type=None, failure_context={})
```

- [ ] **Step 5: Write tests for each remaining workflow, run all**

```
pytest tests/knowledge_base/test_workflows.py -v
```
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add knowledge_base/query/workflows/ knowledge_base/query/agents/state_manager.py
git commit -m "feat(E7): complete all 5 Tier 1 workflows with typed handoffs"
```

---

## Verification

```
pytest tests/knowledge_base/test_workflows.py -v
```
Expected: 15+ tests PASS, 0 failures.
