# KB System — Parallel Wave Orchestrator Plan

> **For agentic workers:** You ARE the orchestrator. Read this entire file before doing anything else.
> Your job is to dispatch sub-agents wave by wave, merge their branches, run gate checks, and advance to the next wave — without human intervention.

**Goal:** Implement all 10 epics of the knowledge-base system by dispatching parallel implementation sub-agents per wave, merging after each wave passes its gate check.

**Working directory:** `d:\Castro Consulting\Junior`

**Architecture doc (sub-agents must read this):** `docs/improvements/architecture-design-document-ingestion-and-query-system.md`

---

## Orchestrator Responsibilities

1. For each wave, dispatch all epics as **parallel background agents** (Agent tool, `isolation: "worktree"`, `run_in_background: true`)
2. Wait for all agents in the wave to complete (you will be notified)
3. Merge each completed branch into `main` in sequence
4. Run the wave's gate-check command — if it fails, dispatch a fix agent for the failing tests before advancing
5. Update the todo list between waves
6. Proceed to next wave

---

## Pre-flight Checks (do before Wave 1)

```bash
# Verify scaffolding exists
ls knowledge_base/__init__.py tests/knowledge_base/__init__.py pytest.ini

# Verify no uncommitted changes on main
git status

# Install new dependencies if not yet installed
pip install aiosqlite pymupdf openai pytest-asyncio anthropic
```

If scaffolding is missing, run:
```bash
mkdir -p knowledge_base/models knowledge_base/store knowledge_base/ingestion/agents \
  knowledge_base/query/agents knowledge_base/query/workflows knowledge_base/query/recovery \
  knowledge_base/query/tier3 knowledge_base/voice knowledge_base/feedback tests/knowledge_base
touch knowledge_base/__init__.py knowledge_base/models/__init__.py knowledge_base/store/__init__.py \
  knowledge_base/ingestion/__init__.py "knowledge_base/ingestion/agents/__init__.py" \
  knowledge_base/query/__init__.py "knowledge_base/query/agents/__init__.py" \
  "knowledge_base/query/workflows/__init__.py" "knowledge_base/query/recovery/__init__.py" \
  "knowledge_base/query/tier3/__init__.py" knowledge_base/voice/__init__.py \
  knowledge_base/feedback/__init__.py tests/__init__.py tests/knowledge_base/__init__.py
```

---

## Wave Definitions

### Wave 1 — Foundation (parallel, no dependencies)

**Gate check:** `pytest tests/knowledge_base/test_models.py tests/knowledge_base/test_store.py tests/knowledge_base/test_tracing.py -v`

| Epic | Plan file to load | Branch name |
|------|-------------------|-------------|
| E0 | `docs/improvements/plans/epics/E0-core-data-models.md` | `feat/kb-e0-models` |
| E1 | `docs/improvements/plans/epics/E1-tracing-infrastructure.md` | `feat/kb-e1-tracing` |

---

### Wave 2 — Pipeline agents (parallel, needs Wave 1 merged)

**Gate check:** `pytest tests/knowledge_base/test_segmentation.py tests/knowledge_base/test_extraction.py tests/knowledge_base/test_voice.py tests/knowledge_base/test_router.py tests/knowledge_base/test_session_manager.py -v`

| Epic | Plan file to load | Branch name |
|------|-------------------|-------------|
| E2 | `docs/improvements/plans/epics/E2-segmentation-classification.md` | `feat/kb-e2-segmentation` |
| E3 | `docs/improvements/plans/epics/E3-extraction-agents.md` | `feat/kb-e3-extraction` |
| E5 | `docs/improvements/plans/epics/E5-voice-io-preprocessing.md` | `feat/kb-e5-voice` |
| E6 | `docs/improvements/plans/epics/E6-router-session.md` | `feat/kb-e6-router` |

---

### Wave 3 — Assembly and Workflows (parallel, split by dependency)

**Gate check:** `pytest tests/knowledge_base/test_pipeline.py tests/knowledge_base/test_workflows.py -v`

| Epic | Plan file to load | Branch name | Needs |
|------|-------------------|-------------|-------|
| E4 | `docs/improvements/plans/epics/E4-assembly-linking-quality.md` | `feat/kb-e4-assembly` | E2 + E3 merged |
| E7 | `docs/improvements/plans/epics/E7-tier1-workflows.md` | `feat/kb-e7-workflows` | E5 + E6 merged |

---

### Wave 4 — Hardening (parallel, needs Wave 3 merged)

**Gate check:** `pytest tests/knowledge_base/ -v` (full suite, 50+ tests expected)

| Epic | Plan file to load | Branch name |
|------|-------------------|-------------|
| E8 | `docs/improvements/plans/epics/E8-recovery-agentic-fallback.md` | `feat/kb-e8-recovery` |
| E9 | `docs/improvements/plans/epics/E9-feedback-monitoring.md` | `feat/kb-e9-feedback` |

---

## Sub-agent Prompt Template

When dispatching an implementation sub-agent, use this prompt (fill in the bracketed fields):

```
You are implementing [EPIC_ID] ([EPIC_TITLE]) for the Junior knowledge-base system.

## Your task
Read your epic plan file first, then implement every task in order using TDD (write failing test → implement → pass → commit).

## Epic plan file
[FULL CONTENT OF EPIC PLAN FILE — paste the entire contents, do not make the agent read it from disk]

## Project context
- Working directory: d:\Castro Consulting\Junior
- Python package being built: knowledge_base/ (alongside existing api/)
- All __init__.py files already exist — do not recreate them
- Git branch to use: [BRANCH_NAME] (create it from main before starting)
- Commit frequently — one commit per completed task
- Run pytest after each task; do not proceed with failing tests

## Files this epic creates (do not edit files outside this list):
[LIST OF FILES FROM THE EPIC'S "Files to Create" SECTION]

## Dependencies available (already installed or add to requirements.txt if missing):
- anthropic (already in requirements.txt)
- aiosqlite
- pymupdf (for E4 only)
- openai (for E5 only)
- pytest-asyncio

## When done
Report: DONE | DONE_WITH_CONCERNS | BLOCKED
Include: branch name, list of files created, test results (pass count)
```

---

## Merge Procedure (run after each wave)

For each completed branch in the wave:

```bash
# 1. Fetch the branch (if agent worked in a worktree, it already committed there)
git checkout main
git merge --no-ff [BRANCH_NAME] -m "merge: [EPIC_ID] - [description]"

# 2. If merge conflict (unlikely — epics touch non-overlapping files):
#    Resolve by keeping both sides (they created different files)
git add .
git merge --continue
```

If an agent reported `BLOCKED` or tests failed after merge: dispatch a fix agent with the failing test output as context before proceeding.

---

## Orchestrator Todo List (manage with TodoWrite)

```
[ ] Pre-flight checks
[ ] Wave 1: Dispatch E0 (background, worktree)
[ ] Wave 1: Dispatch E1 (background, worktree)
[ ] Wave 1: Merge E0 branch
[ ] Wave 1: Merge E1 branch
[ ] Wave 1: Gate check
[ ] Wave 2: Dispatch E2 (background, worktree)
[ ] Wave 2: Dispatch E3 (background, worktree)
[ ] Wave 2: Dispatch E5 (background, worktree)
[ ] Wave 2: Dispatch E6 (background, worktree)
[ ] Wave 2: Merge all Wave 2 branches
[ ] Wave 2: Gate check
[ ] Wave 3: Dispatch E4 (background, worktree)
[ ] Wave 3: Dispatch E7 (background, worktree)
[ ] Wave 3: Merge E4 branch
[ ] Wave 3: Merge E7 branch
[ ] Wave 3: Gate check
[ ] Wave 4: Dispatch E8 (background, worktree)
[ ] Wave 4: Dispatch E9 (background, worktree)
[ ] Wave 4: Merge all Wave 4 branches
[ ] Wave 4: Final gate check (full suite)
```

---

## Epic Context Summaries (for sub-agent prompt construction)

These summaries let the orchestrator construct a complete sub-agent prompt without reading the full epic file at dispatch time. **Always paste the full epic file content into the sub-agent prompt** — do not reference the file path.

### E0 — Core Data Models & Knowledge Store
- Creates: `knowledge_base/models/entry.py`, `knowledge_base/store/knowledge_store.py`, tests
- Key types: `KnowledgeEntry`, `MediaBlob` dataclasses; `KnowledgeStore` with aiosqlite CRUD + tag/vernacular search
- Dependency added: `aiosqlite==0.20.0`
- Test file: `tests/knowledge_base/test_models.py`, `tests/knowledge_base/test_store.py`

### E1 — Tracing Infrastructure
- Creates: `knowledge_base/models/trace.py`, `knowledge_base/store/trace_store.py`, `knowledge_base/tracing.py`, tests
- Key types: `TraceEvent` dataclass; `TraceStore` with aiosqlite; `trace_agent()` async context manager
- Test file: `tests/knowledge_base/test_tracing.py`

### E2 — Document Segmentation & Classification
- Creates: `knowledge_base/ingestion/phase_runner.py`, `knowledge_base/ingestion/agents/page_segmenter.py`, `document_classifier.py`, `chunk_classifier.py`, `image_classifier.py`, tests
- Calls Claude vision API; uses Haiku for cheap classification, Sonnet for page segmentation
- Test file: `tests/knowledge_base/test_segmentation.py`

### E3 — Extraction Agents
- Creates: `knowledge_base/ingestion/agents/type_specific_extractor.py`, `diagram_analyzer.py`, `reference_image_processor.py`, `positional_analyzer.py`, tests
- All agents call Claude (vision + text); all mocked in tests
- Test file: `tests/knowledge_base/test_extraction.py`

### E4 — Assembly, Linking & Quality + Full Pipeline
- Creates: `vernacular_generator.py`, `module_assembler.py`, `reference_linker.py`, `quality_checker.py`, `knowledge_base/ingestion/pipeline.py`, tests
- Dependency added: `pymupdf` (PDF → PNG rendering)
- Test file: `tests/knowledge_base/test_pipeline.py`

### E5 — Voice I/O & Transcript Preprocessing
- Creates: `knowledge_base/models/session.py`, `knowledge_base/voice/whisper_client.py`, `knowledge_base/voice/formatter.py`, `knowledge_base/query/preprocessor.py`, tests
- Key types: `Session`, `ProcessedQuery`, `Turn` dataclasses
- Dependency added: `openai>=1.0.0` (Whisper)
- Test file: `tests/knowledge_base/test_voice.py`

### E6 — Router & Session Management
- Creates: `knowledge_base/query/router.py`, `knowledge_base/query/session_manager.py`, `knowledge_base/query/agents/identifier.py`, `knowledge_base/query/agents/retriever.py`, tests
- `Router` is a pure classifier (no LLM calls); `IdentifierAgent` does 2-way parallel search
- Test files: `tests/knowledge_base/test_router.py`, `tests/knowledge_base/test_session_manager.py`

### E7 — Tier 1 Query Workflows
- Creates: all 5 workflows in `knowledge_base/query/workflows/`, plus `context_gatherer.py`, `instruction_walker.py`, `prerequisite_checker.py`, `state_manager.py`, `responder.py`
- All workflows return typed `WorkflowResult`; failures have typed codes (ZERO_MATCHES, AMBIGUOUS_MATCH, etc.)
- Test file: `tests/knowledge_base/test_workflows.py`

### E8 — Tier 2 Recovery & Tier 3 Agentic Fallback
- Creates: all recovery strategies in `knowledge_base/query/recovery/`, `knowledge_base/query/tier3/orchestrator.py`, tests
- Tier 3 uses Claude tool-use (search_knowledge_base tool); hard 10-call limit
- Test file: `tests/knowledge_base/test_recovery.py`

### E9 — Feedback Loop & Monitoring
- Creates: `knowledge_base/feedback/collector.py`, `knowledge_base/feedback/metrics.py`, tests; modifies `api/index.py`
- Adds `GET /api/kb/metrics` route backed by TraceStore
- Test file: `tests/knowledge_base/test_feedback.py`

---

## Failure Handling

| Situation | Action |
|-----------|--------|
| Agent reports BLOCKED | Dispatch a fix agent with the blocker details + full epic file |
| Gate check fails | Dispatch a fix agent with: failing test output + relevant epic file |
| Merge conflict | Both branches added the same file: keep both sides, run `git add . && git merge --continue` |
| Agent created extra files | Remove extra files, re-run gate check |
| Tests pass but behavior wrong | Log concern, proceed — behavioral validation is a post-implementation step |
