# E8 — Tier 2 Recovery & Tier 3 Agentic Fallback

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement task-by-task.
>
> Read the architecture doc at `docs/improvements/architecture-design-document-ingestion-and-query-system.md` (Sections 6.4 and 6.5) before starting.

**Goal:** Implement the Tier 2 recovery registry (typed failure → recovery strategy) and the Tier 3 `Orchestrator` (constrained agentic fallback that cites entry IDs, has a hard turn limit, and logs its trace).

**Wave:** 4 — Requires E7 (all Tier 1 workflows) to be merged first.

**Tech Stack:** Python 3.11+, asyncio, anthropic SDK (tool use), pytest-asyncio

---

## Files to Create

- `knowledge_base/query/recovery/__init__.py`
- `knowledge_base/query/recovery/registry.py`
- `knowledge_base/query/recovery/broaden_search.py`
- `knowledge_base/query/recovery/clarification.py`
- `knowledge_base/query/recovery/raw_text_fallback.py`
- `knowledge_base/query/recovery/confirmation.py`
- `knowledge_base/query/recovery/info_gather.py`
- `knowledge_base/query/tier3/__init__.py`
- `knowledge_base/query/tier3/orchestrator.py`
- `tests/knowledge_base/test_recovery.py`

---

## Task E8-1: Recovery registry and base class

**Files:** `knowledge_base/query/recovery/registry.py`

- [ ] **Step 1: Write failing test**

```python
# tests/knowledge_base/test_recovery.py
import pytest
from knowledge_base.query.recovery.registry import BaseRecovery, attempt_recovery, RECOVERY_REGISTRY
from knowledge_base.query.workflows.base import WorkflowResult
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
        cleaned_text=text, extracted_entities={},
        uncertainty_flags=[], corrections_detected=[],
        references_to_resolve=[], raw_text=text
    )

def test_recovery_registry_has_expected_failure_types():
    assert "ZERO_MATCHES" in RECOVERY_REGISTRY
    assert "AMBIGUOUS_MATCH" in RECOVERY_REGISTRY
    assert "MISSING_PREREQUISITE" in RECOVERY_REGISTRY
    assert "ENTRY_TYPE_UNSUPPORTED" in RECOVERY_REGISTRY
    assert "CONFIDENCE_TOO_LOW" in RECOVERY_REGISTRY

@pytest.mark.asyncio
async def test_attempt_recovery_returns_none_for_unknown_type():
    result = await attempt_recovery("UNKNOWN_FAILURE", {}, _make_query("x"), _make_session())
    assert result is None

@pytest.mark.asyncio
async def test_attempt_recovery_returns_first_successful():
    class AlwaysSucceeds(BaseRecovery):
        async def attempt(self, failure_context, query, session):
            return WorkflowResult(success=True, response="Recovered!", failure_type=None, failure_context={})

    RECOVERY_REGISTRY["TEST_TYPE"] = [AlwaysSucceeds]
    result = await attempt_recovery("TEST_TYPE", {}, _make_query("x"), _make_session())
    assert result is not None
    assert result.success is True
    assert result.response == "Recovered!"
    del RECOVERY_REGISTRY["TEST_TYPE"]
```

- [ ] **Step 2: Run to verify failure**

```
pytest tests/knowledge_base/test_recovery.py -k "registry" -v
```

- [ ] **Step 3: Create `knowledge_base/query/recovery/__init__.py`** (empty)

- [ ] **Step 4: Create `knowledge_base/query/recovery/registry.py`**

```python
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session

class BaseRecovery:
    async def attempt(
        self,
        failure_context: dict,
        query: ProcessedQuery,
        session: Session
    ) -> WorkflowResult:
        raise NotImplementedError

# Registry maps failure_type -> ordered list of recovery strategies to try
# Populated as recovery classes are defined in subsequent tasks
RECOVERY_REGISTRY: dict[str, list[type[BaseRecovery]]] = {
    "ZERO_MATCHES": [],
    "AMBIGUOUS_MATCH": [],
    "MISSING_PREREQUISITE": [],
    "ENTRY_TYPE_UNSUPPORTED": [],
    "CONFIDENCE_TOO_LOW": [],
}

async def attempt_recovery(
    failure_type: str,
    failure_context: dict,
    query: ProcessedQuery,
    session: Session
) -> WorkflowResult | None:
    """
    Tries each registered recovery strategy in order.
    Returns the first successful result, or None if all fail.
    """
    strategies = RECOVERY_REGISTRY.get(failure_type, [])
    for strategy_cls in strategies:
        strategy = strategy_cls()
        result = await strategy.attempt(failure_context, query, session)
        if result.success:
            return result
    return None
```

- [ ] **Step 5: Run tests, commit**

```bash
git add knowledge_base/query/recovery/ tests/knowledge_base/test_recovery.py
git commit -m "feat(E8): add Tier 2 recovery registry and BaseRecovery interface"
```

---

## Task E8-2: ClarificationRecovery (for ZERO_MATCHES)

**File:** `knowledge_base/query/recovery/clarification.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.query.recovery.clarification import ClarificationRecovery

@pytest.mark.asyncio
async def test_clarification_recovery_always_succeeds():
    recovery = ClarificationRecovery()
    result = await recovery.attempt(
        failure_context={"query": "the purple thing"},
        query=_make_query("the purple thing"),
        session=_make_session()
    )
    assert result.success is True
    assert result.response is not None
    assert len(result.response) > 0
```

- [ ] **Step 2: Create `knowledge_base/query/recovery/clarification.py`**

```python
from knowledge_base.query.recovery.registry import BaseRecovery, RECOVERY_REGISTRY
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session

class ClarificationRecovery(BaseRecovery):
    async def attempt(self, failure_context: dict, query: ProcessedQuery, session: Session) -> WorkflowResult:
        return WorkflowResult(
            success=True,
            response="I couldn't find that. Could you describe what you're looking at differently? For example, mention its color, shape, or size.",
            failure_type=None,
            failure_context={}
        )

RECOVERY_REGISTRY["ZERO_MATCHES"].append(ClarificationRecovery)
```

- [ ] **Step 3: Run, commit**

```bash
git add knowledge_base/query/recovery/clarification.py
git commit -m "feat(E8): add ClarificationRecovery for ZERO_MATCHES"
```

---

## Task E8-3: BroadenSearchRecovery (for ZERO_MATCHES, tries first)

**File:** `knowledge_base/query/recovery/broaden_search.py`

- [ ] **Step 1: Add test**

```python
from knowledge_base.query.recovery.broaden_search import BroadenSearchRecovery

@pytest.mark.asyncio
async def test_broaden_search_succeeds_when_store_has_match():
    from unittest.mock import MagicMock, AsyncMock
    mock_store = MagicMock()
    mock_entry = MagicMock()
    mock_entry.id = "e1"
    mock_entry.title = "Simple Wires"
    mock_entry.summary = "Wire cutting rules"
    mock_store.list_by_document = AsyncMock(return_value=[mock_entry])

    recovery = BroadenSearchRecovery(store=mock_store)
    result = await recovery.attempt(
        failure_context={"query": "the wires"},
        query=_make_query("the wires"),
        session=_make_session()
    )
    # Broaden search finds a match from the document
    assert result.success is True

@pytest.mark.asyncio
async def test_broaden_search_fails_gracefully_when_empty():
    from unittest.mock import MagicMock, AsyncMock
    mock_store = MagicMock()
    mock_store.list_by_document = AsyncMock(return_value=[])

    recovery = BroadenSearchRecovery(store=mock_store)
    result = await recovery.attempt({}, _make_query("x"), _make_session())
    assert result.success is False
```

- [ ] **Step 2: Create `knowledge_base/query/recovery/broaden_search.py`**

```python
from knowledge_base.query.recovery.registry import BaseRecovery, RECOVERY_REGISTRY
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore

class BroadenSearchRecovery(BaseRecovery):
    def __init__(self, store: KnowledgeStore | None = None):
        self.store = store

    async def attempt(self, failure_context: dict, query: ProcessedQuery, session: Session) -> WorkflowResult:
        if self.store is None:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context=failure_context)

        # Broaden: list all entries for this document and pick best by title similarity
        all_entries = await self.store.list_by_document(session.document_id)
        if not all_entries:
            return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context=failure_context)

        query_words = set(query.cleaned_text.lower().split())
        best = None
        best_score = 0
        for entry in all_entries:
            title_words = set(entry.title.lower().split())
            score = len(query_words & title_words)
            if score > best_score:
                best_score = score
                best = entry

        if best and best_score > 0:
            return WorkflowResult(
                success=True,
                response=f"Could this be {best.title}? {best.summary}",
                failure_type=None,
                failure_context={"broadened_match": best.id}
            )

        return WorkflowResult(success=False, response=None, failure_type="ZERO_MATCHES", failure_context=failure_context)

# BroadenSearch runs before Clarification
RECOVERY_REGISTRY["ZERO_MATCHES"].insert(0, BroadenSearchRecovery)
```

- [ ] **Step 3: Run, commit**

```bash
git add knowledge_base/query/recovery/broaden_search.py
git commit -m "feat(E8): add BroadenSearchRecovery (tries word-overlap before asking user to clarify)"
```

---

## Task E8-4: RawTextFallbackRecovery and ConfirmationRecovery

- [ ] **Create `knowledge_base/query/recovery/raw_text_fallback.py`:**

```python
import anthropic
from knowledge_base.query.recovery.registry import BaseRecovery, RECOVERY_REGISTRY
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session

anthropic_client = anthropic.AsyncAnthropic()

class RawTextFallbackRecovery(BaseRecovery):
    def __init__(self, store=None):
        self.store = store

    async def attempt(self, failure_context: dict, query: ProcessedQuery, session: Session) -> WorkflowResult:
        entry_id = failure_context.get("entry_id")
        if not entry_id or self.store is None:
            return WorkflowResult(success=False, response=None, failure_type="ENTRY_TYPE_UNSUPPORTED", failure_context=failure_context)

        entry = await self.store.get(entry_id)
        if not entry:
            return WorkflowResult(success=False, response=None, failure_type="ENTRY_TYPE_UNSUPPORTED", failure_context=failure_context)

        # Answer from raw_text instead of structured_data
        response = await anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system="Answer the user's question using ONLY the provided text. One or two spoken sentences.",
            messages=[{
                "role": "user",
                "content": f"Question: {query.cleaned_text}\n\nSource text: {entry.raw_text[:3000]}"
            }]
        )
        return WorkflowResult(
            success=True,
            response=response.content[0].text.strip(),
            failure_type=None,
            failure_context={}
        )

RECOVERY_REGISTRY["ENTRY_TYPE_UNSUPPORTED"].append(RawTextFallbackRecovery)
```

- [ ] **Create `knowledge_base/query/recovery/confirmation.py`:**

```python
from knowledge_base.query.recovery.registry import BaseRecovery, RECOVERY_REGISTRY
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session

class ConfirmationRecovery(BaseRecovery):
    async def attempt(self, failure_context: dict, query: ProcessedQuery, session: Session) -> WorkflowResult:
        candidates = failure_context.get("candidates", [])
        if not candidates:
            return WorkflowResult(success=False, response=None, failure_type="CONFIDENCE_TOO_LOW", failure_context=failure_context)
        best = candidates[0]
        best_id = best.get("id", "unknown")
        return WorkflowResult(
            success=True,
            response=f"I'm not fully sure, but I think you mean {best_id}. Is that right?",
            failure_type=None,
            failure_context={"awaiting_confirmation": True, "candidate_id": best_id}
        )

RECOVERY_REGISTRY["CONFIDENCE_TOO_LOW"].append(ConfirmationRecovery)
```

- [ ] **Create `knowledge_base/query/recovery/info_gather.py`:**

```python
from knowledge_base.query.recovery.registry import BaseRecovery, RECOVERY_REGISTRY
from knowledge_base.query.workflows.base import WorkflowResult
from knowledge_base.models.session import ProcessedQuery, Session

class InfoGatherRecovery(BaseRecovery):
    async def attempt(self, failure_context: dict, query: ProcessedQuery, session: Session) -> WorkflowResult:
        missing = failure_context.get("missing", [])
        if not missing:
            return WorkflowResult(success=False, response=None, failure_type="MISSING_PREREQUISITE", failure_context=failure_context)

        first_missing = missing[0].replace("_", " ")
        return WorkflowResult(
            success=True,
            response=f"I need one more thing: what is the {first_missing}?",
            failure_type=None,
            failure_context={"awaiting_info": first_missing}
        )

RECOVERY_REGISTRY["MISSING_PREREQUISITE"].append(InfoGatherRecovery)
```

- [ ] **Run all recovery tests**

```
pytest tests/knowledge_base/test_recovery.py -v
```
Expected: All tests PASS

- [ ] **Commit**

```bash
git add knowledge_base/query/recovery/
git commit -m "feat(E8): add all Tier 2 recovery strategies"
```

---

## Task E8-5: Tier 3 Orchestrator

**File:** `knowledge_base/query/tier3/orchestrator.py`

- [ ] **Step 1: Add test**

```python
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
async def test_tier3_orchestrator_returns_answer():
    from knowledge_base.query.tier3.orchestrator import Tier3Orchestrator
    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[])
    mock_store.list_by_document = AsyncMock(return_value=[])

    # Mock anthropic to return end_turn immediately
    mock_message = MagicMock()
    mock_message.stop_reason = "end_turn"
    mock_message.content = [MagicMock(text="Based on entry e1: cut the wire.", type="text")]

    with patch("knowledge_base.query.tier3.orchestrator.anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create = AsyncMock(return_value=mock_message)
        orch = Tier3Orchestrator(store=mock_store)
        result = await orch.resolve(
            query=_make_query("what do I do with the red wire"),
            session=_make_session(),
            failure_trace=[{"tier": 1, "failure": "ZERO_MATCHES"}]
        )
    assert "cut" in result.lower() or "wire" in result.lower()

@pytest.mark.asyncio
async def test_tier3_respects_turn_limit():
    from knowledge_base.query.tier3.orchestrator import Tier3Orchestrator, MAX_AGENT_CALLS
    mock_store = MagicMock()
    mock_store.search_by_tag = AsyncMock(return_value=[])

    # Always returns tool_use to force max iterations
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.id = "tu1"
    mock_tool_use.input = {"keyword": "wire"}

    mock_message = MagicMock()
    mock_message.stop_reason = "tool_use"
    mock_message.content = [mock_tool_use]

    with patch("knowledge_base.query.tier3.orchestrator.anthropic.AsyncAnthropic") as MockClient:
        instance = MockClient.return_value
        instance.messages.create = AsyncMock(return_value=mock_message)
        orch = Tier3Orchestrator(store=mock_store)
        result = await orch.resolve(_make_query("x"), _make_session(), [])
    assert isinstance(result, str)
    # Verify it did not run more than MAX_AGENT_CALLS iterations
    assert instance.messages.create.call_count <= MAX_AGENT_CALLS + 1
```

- [ ] **Step 2: Create `knowledge_base/query/tier3/__init__.py`** (empty)

- [ ] **Step 3: Create `knowledge_base/query/tier3/orchestrator.py`**

```python
import anthropic
from knowledge_base.models.session import ProcessedQuery, Session
from knowledge_base.store.knowledge_store import KnowledgeStore

MAX_AGENT_CALLS = 10

class Tier3Orchestrator:
    def __init__(self, store: KnowledgeStore):
        self.store = store
        self.client = anthropic.AsyncAnthropic()

    async def resolve(
        self,
        query: ProcessedQuery,
        session: Session,
        failure_trace: list[dict]
    ) -> str:
        """
        Agentic fallback. Key constraints:
        1. Only answers from KnowledgeStore content (tool-use for search).
        2. Must cite entry IDs for every claim.
        3. Hard limit of MAX_AGENT_CALLS tool invocations.
        """
        tools = [
            {
                "name": "search_knowledge_base",
                "description": (
                    "Search the knowledge base by keyword. "
                    "Returns entry titles and IDs. "
                    "Use entry IDs to cite your answer."
                ),
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "Search term (color, module name, object type, etc.)"
                        }
                    },
                    "required": ["keyword"]
                }
            }
        ]

        system = (
            "You are answering a voice query from someone following instructions. "
            "CRITICAL: Answer ONLY from the knowledge base via the search tool. "
            "Do NOT use general knowledge. "
            "Every claim must cite the entry ID (e.g., 'According to entry e123: ...'). "
            "Give a concise spoken answer in 1-2 sentences."
        )

        messages = [{
            "role": "user",
            "content": (
                f"Query: {query.cleaned_text}\n"
                f"Previously tried: {failure_trace}\n"
                f"Document: {session.document_id}\n"
                "Search the knowledge base and answer the query."
            )
        }]

        calls = 0
        while calls < MAX_AGENT_CALLS:
            response = await self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1024,
                system=system,
                tools=tools,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                text_blocks = [b.text for b in response.content if hasattr(b, "text")]
                return text_blocks[0] if text_blocks else "I was unable to find an answer."

            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if not tool_use:
                break

            keyword = tool_use.input.get("keyword", "")
            entries = await self.store.search_by_tag(keyword)
            if not entries:
                entries = await self.store.search_by_vernacular(keyword)

            tool_result_content = (
                [f"ID: {e.id} | Title: {e.title} | Summary: {e.summary}" for e in entries[:5]]
                if entries else ["No entries found for this keyword."]
            )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_use.id,
                    "content": "\n".join(tool_result_content)
                }]
            })
            calls += 1

        return "I was unable to find a definitive answer in the knowledge base."
```

- [ ] **Step 4: Run all E8 tests**

```
pytest tests/knowledge_base/test_recovery.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add knowledge_base/query/tier3/
git commit -m "feat(E8): add Tier 3 Orchestrator with tool-use search and hard turn limit"
```

---

## Verification

```
pytest tests/knowledge_base/test_recovery.py -v
```
Expected: 10+ tests PASS, 0 failures.
