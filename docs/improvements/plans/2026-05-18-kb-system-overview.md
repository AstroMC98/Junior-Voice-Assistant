# Knowledge-Base Ingestion & Voice-Driven Query System — Master Plan

> **Architecture doc:** `docs/improvements/architecture-design-document-ingestion-and-query-system.md`
> **Epic files:** `docs/improvements/plans/epics/`
> **Date:** 2026-05-18

---

## What This Builds

A structured `knowledge_base/` Python package alongside the existing `api/` FastAPI backend. It adds:

1. **Ingestion pipeline** — 6-phase, asyncio-parallel pipeline that processes PDFs into a typed SQLite knowledge store
2. **Query pipeline** — 3-tier voice-driven query system (deterministic → recovery → agentic fallback)
3. **Tracing** — every agent call logged to a queryable trace store
4. **Feedback loop** — query-time signals improve ingestion over time
5. **Metrics endpoint** — `GET /api/kb/metrics` for monitoring

---

## Epic Wave Map

Epics within the same wave can be dispatched to parallel agents simultaneously.  
Each agent works from its own epic file — they share no session context.

| Wave | Epic | File | Depends On | Agent Slot |
|------|------|------|-----------|------------|
| **1** | E0 — Core Data Models & KnowledgeStore | [E0-core-data-models.md](epics/E0-core-data-models.md) | — | Agent A |
| **1** | E1 — Tracing Infrastructure | [E1-tracing-infrastructure.md](epics/E1-tracing-infrastructure.md) | — | Agent B |
| **2** | E2 — Segmentation & Classification | [E2-segmentation-classification.md](epics/E2-segmentation-classification.md) | E0, E1 | Agent A |
| **2** | E3 — Extraction Agents | [E3-extraction-agents.md](epics/E3-extraction-agents.md) | E0, E1 | Agent B |
| **2** | E5 — Voice I/O & Preprocessing | [E5-voice-io-preprocessing.md](epics/E5-voice-io-preprocessing.md) | E0 | Agent C |
| **2** | E6 — Router & Session Management | [E6-router-session.md](epics/E6-router-session.md) | E0, E1 | Agent D |
| **3** | E4 — Assembly, Linking & Quality | [E4-assembly-linking-quality.md](epics/E4-assembly-linking-quality.md) | E2, E3 | Agent A |
| **3** | E7 — Tier 1 Query Workflows | [E7-tier1-workflows.md](epics/E7-tier1-workflows.md) | E5, E6 | Agent B |
| **4** | E8 — Recovery & Tier 3 Fallback | [E8-recovery-agentic-fallback.md](epics/E8-recovery-agentic-fallback.md) | E7 | Agent A |
| **4** | E9 — Feedback & Monitoring | [E9-feedback-monitoring.md](epics/E9-feedback-monitoring.md) | E7, E8 | Agent B |

---

## Dependency Graph

```
Wave 1:  [E0]──────────────────────────────────┐
         [E1]──────────────────────────────────┤
                                               ▼
Wave 2:       [E2]──────────────────────────── ┐
              [E3]──────────────────────────── ┤
              [E5]──────────────────────────── ┤
              [E6]──────────────────────────── ┤
                                               ▼
Wave 3:            [E4] (needs E2+E3)──────── ┐
                   [E7] (needs E5+E6)──────── ┤
                                               ▼
Wave 4:                 [E8] (needs E7)──────┐
                        [E9] (needs E7+E8)───┘
```

---

## Gate Conditions (do not start next wave until these pass)

| Gate | Condition |
|------|-----------|
| Wave 1 → Wave 2 | `pytest tests/knowledge_base/test_models.py tests/knowledge_base/test_store.py tests/knowledge_base/test_tracing.py` all green |
| Wave 2 → Wave 3 | `pytest tests/knowledge_base/test_segmentation.py tests/knowledge_base/test_extraction.py tests/knowledge_base/test_voice.py tests/knowledge_base/test_router.py tests/knowledge_base/test_session_manager.py` all green |
| Wave 3 → Wave 4 | `pytest tests/knowledge_base/test_pipeline.py tests/knowledge_base/test_workflows.py` all green |
| Ship | `pytest tests/knowledge_base/ -v` all green (50+ tests) |

---

## Parallel Agent Dispatch Instructions

### Wave 1 — Dispatch both NOW

**Agent A prompt:**
```
Implement Epic E0 from docs/improvements/plans/epics/E0-core-data-models.md
Use superpowers:executing-plans to work through the tasks in order.
Do not start E1 — that's a separate agent.
Report back when all tests in tests/knowledge_base/test_models.py and test_store.py pass.
```

**Agent B prompt:**
```
Implement Epic E1 from docs/improvements/plans/epics/E1-tracing-infrastructure.md
Use superpowers:executing-plans to work through the tasks in order.
Do not start E0 — that's a separate agent.
Report back when all tests in tests/knowledge_base/test_tracing.py pass.
```

### Wave 2 — Dispatch all 4 after Wave 1 merges

**Agent A:** `Implement Epic E2 from docs/improvements/plans/epics/E2-segmentation-classification.md`
**Agent B:** `Implement Epic E3 from docs/improvements/plans/epics/E3-extraction-agents.md`
**Agent C:** `Implement Epic E5 from docs/improvements/plans/epics/E5-voice-io-preprocessing.md`
**Agent D:** `Implement Epic E6 from docs/improvements/plans/epics/E6-router-session.md`

### Wave 3 — Split by dependency

**Agent A:** `Implement Epic E4 from docs/improvements/plans/epics/E4-assembly-linking-quality.md` *(after E2+E3 merged)*
**Agent B:** `Implement Epic E7 from docs/improvements/plans/epics/E7-tier1-workflows.md` *(after E5+E6 merged)*

### Wave 4

**Agent A:** `Implement Epic E8 from docs/improvements/plans/epics/E8-recovery-agentic-fallback.md` *(after E7)*
**Agent B:** `Implement Epic E9 from docs/improvements/plans/epics/E9-feedback-monitoring.md` *(after E7+E8)*

---

## New File Tree (what gets created)

```
knowledge_base/
├── __init__.py
├── models/
│   ├── entry.py          # KnowledgeEntry, MediaBlob
│   ├── session.py        # Session, Turn, ProcessedQuery
│   └── trace.py          # TraceEvent
├── store/
│   ├── knowledge_store.py  # SQLite CRUD + tag/vernacular search
│   └── trace_store.py      # Trace write/query
├── tracing.py             # trace_agent() context manager
├── ingestion/
│   ├── phase_runner.py    # asyncio.gather with semaphore
│   ├── pipeline.py        # 6-phase orchestrator
│   └── agents/
│       ├── page_segmenter.py
│       ├── document_classifier.py
│       ├── chunk_classifier.py
│       ├── image_classifier.py
│       ├── diagram_analyzer.py
│       ├── reference_image_processor.py
│       ├── positional_analyzer.py
│       ├── type_specific_extractor.py
│       ├── vernacular_generator.py
│       ├── module_assembler.py
│       ├── reference_linker.py
│       └── quality_checker.py
├── query/
│   ├── preprocessor.py
│   ├── router.py
│   ├── session_manager.py
│   ├── agents/
│   │   ├── identifier.py
│   │   ├── retriever.py
│   │   ├── context_gatherer.py
│   │   ├── instruction_walker.py
│   │   ├── prerequisite_checker.py
│   │   ├── state_manager.py
│   │   └── responder.py
│   ├── workflows/
│   │   ├── base.py
│   │   ├── identification.py
│   │   ├── instruction.py
│   │   ├── lookup.py
│   │   ├── disambiguation.py
│   │   └── stateful_continuation.py
│   ├── recovery/
│   │   ├── registry.py
│   │   ├── broaden_search.py
│   │   ├── clarification.py
│   │   ├── raw_text_fallback.py
│   │   ├── confirmation.py
│   │   └── info_gather.py
│   └── tier3/
│       └── orchestrator.py
├── voice/
│   ├── whisper_client.py
│   └── formatter.py
└── feedback/
    ├── collector.py
    └── metrics.py

tests/knowledge_base/
├── test_models.py          # E0
├── test_store.py           # E0
├── test_tracing.py         # E1
├── test_segmentation.py    # E2
├── test_extraction.py      # E3
├── test_voice.py           # E5
├── test_router.py          # E6
├── test_session_manager.py # E6
├── test_pipeline.py        # E4
├── test_workflows.py       # E7
├── test_recovery.py        # E8
└── test_feedback.py        # E9
```

---

## New Dependencies (add to `requirements.txt`)

```
aiosqlite==0.20.0        # E0, E1
pymupdf                  # E2 (PDF to PNG)
openai>=1.0.0            # E5 (Whisper)
pytest-asyncio           # all tests
```

---

## End-to-End Verification

After all epics complete:

```bash
# 1. Run full test suite
pytest tests/knowledge_base/ -v

# 2. Manual ingest test
python -c "
import asyncio
from knowledge_base.store.knowledge_store import KnowledgeStore
from knowledge_base.ingestion.pipeline import ingest_document

async def main():
    store = KnowledgeStore()
    await store.init()
    result = await ingest_document('data/KeepTalkingAndNobodyExplodes-BombDefusalManual-v1.pdf', store)
    print(result)

asyncio.run(main())
"

# 3. Check metrics endpoint
curl http://localhost:8000/api/kb/metrics
```
