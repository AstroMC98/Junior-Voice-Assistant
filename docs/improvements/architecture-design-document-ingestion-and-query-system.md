# Document-to-Knowledge-Base Ingestion & Voice-Driven Query System

## Architecture Design Document

**Version:** 0.1 — Draft  
**Date:** 2026-05-18  
**Status:** Design Phase

---

## 1. Problem Statement

We need a system that can ingest arbitrary documents (game manuals, recipes, assembly guides, technical references, etc.), decompose them into a structured knowledge base, and answer voice-driven queries from users who are hands-free and describing what they see or need. The system must handle documents that are text-heavy, image-heavy, or a mix of both.

The demo case is the *Keep Talking and Nobody Explodes* bomb defusal manual, but the architecture must generalize to any document type without hardcoded schemas.

---

## 2. Design Principles

### 2.1 Workflows First, Execution as Fallback

The system uses **predetermined agentic workflows** (fixed sequences of agents with typed handoffs) for the vast majority of operations. Agentic execution (flexible orchestration) exists only as a last-resort fallback. This provides predictability, traceability, and debuggability in production while retaining flexibility for edge cases.

### 2.2 Voice-First Design

All query-time interactions assume the user is speaking (transcribed via OpenAI Whisper) and listening. This is not a text system with a voice wrapper — voice constraints shape every agent's behavior, from disambiguation strategies to response formatting.

### 2.3 Type-Aware but Not Type-Hardcoded

The knowledge store uses a universal entry schema with a type-specific payload. New document types don't require schema changes — only new `entry_type` classifiers and extractors.

### 2.4 Traceability Everywhere

Every agent invocation, every handoff, every decision is logged as a structured event. Any query can be fully replayed from logs. Failures include complete context about what was tried and why it failed.

### 2.5 Parallelization Where Possible

Independent operations run concurrently. The pipeline is designed to identify parallelism opportunities at both ingestion and query time to minimize latency.

---

## 3. System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     INGESTION PIPELINE                          │
│                     (offline, per document)                     │
│                                                                 │
│  Document → PageSegmenter → DocumentClassifier                  │
│               │                                                 │
│               ├── [Text Regions] → ChunkClassifier              │
│               │                    → TypeSpecificExtractor       │
│               │                                                 │
│               └── [Image Regions] → ImageClassifier             │
│                                    → Type-Specific Analyzer     │
│               │                                                 │
│               ├── VernacularGenerator (all entries)             │
│               ├── ModuleAssembler                               │
│               ├── ReferenceLinker                               │
│               ├── QualityChecker                                │
│               └── KnowledgeStore (write)                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      QUERY PIPELINE                             │
│                      (runtime, per session)                     │
│                                                                 │
│  Voice → Whisper → TranscriptPreprocessor                       │
│                        │                                        │
│                        ▼                                        │
│                      Router                                     │
│                        │                                        │
│              ┌─────────┼─────────┐                              │
│              ▼         ▼         ▼                               │
│           Tier 1    Tier 2    Tier 3                             │
│          Workflow   Recovery  Agentic                            │
│                        │                                        │
│                        ▼                                        │
│              ResponseFormatter → TTS                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. Knowledge Store Schema

### 4.1 Universal Entry Structure

Every knowledge entry shares a common envelope. The `entry_type` field determines the shape of `structured_data`.

```python
@dataclass
class KnowledgeEntry:
    # Identity
    id: str                          # unique identifier
    source_document: str             # which document this came from
    entry_type: str                  # drives structured_data schema

    # Universal fields
    title: str
    summary: str                     # 1-2 sentence gist for retrieval
    tags: list[str]                  # semantic labels for matching
    raw_text: str                    # always preserved, never lost
    vernacular_terms: list[str]      # spoken-language aliases (generated)

    # Type-specific payload
    structured_data: dict            # schema varies by entry_type

    # Visual context
    media: list[MediaBlob]           # images, diagrams, cropped regions

    # Graph edges
    references: list[str]            # IDs of entries this depends on
    referenced_by: list[str]         # reverse links

    # Metadata
    ingestion_trace_id: str          # links to full ingestion log
    confidence_score: float          # extraction confidence
    requires_review: bool            # flagged by QualityChecker
```

### 4.2 Supported Entry Types and Their Structured Data Schemas

| Entry Type | Structured Data Shape | Example Source |
|---|---|---|
| `decision_tree` | `{conditions, branches, outcomes, default}` | KTANE wire rules |
| `procedure` | `{steps[], prerequisites[], warnings[]}` | Assembly instructions |
| `reference_table` | `{columns[], rows[], lookup_keys}` | Morse code frequency table |
| `recipe` | `{ingredients[], steps[], timing, servings}` | Cookbook recipes |
| `narrative` | `{key_points[], entities[], context}` | Blog posts, explanations |
| `visual_guide` | `{visual_description, identifying_features[], commonly_confused_with{}}` | Port/battery identification |
| `positional_layout` | `{coordinate_system, positions{}, mappings{}}` | Who's on First grid |
| `state_machine` | `{states[], transitions[], current_state_indicators}` | Memory module stages |
| `venn_logic` | `{dimensions[], regions[{conditions, action}]}` | Complicated Wires |
| `faq` | `{question, answer, related_questions[]}` | Help documents |

New types are added by implementing a classifier rule and an extractor — no schema migration required.

### 4.3 MediaBlob Structure

```python
@dataclass
class MediaBlob:
    blob_id: str
    media_type: str                  # "image/png", "image/jpeg", etc.
    role: str                        # "diagram", "reference", "state_repr", "decorative"
    data: bytes                      # raw binary
    descriptions: dict               # multi-level text descriptions
    # {
    #   "technical": "...",
    #   "layperson": "...",
    #   "distinguishing_features": [...],
    #   "commonly_confused_with": {...},
    #   "differentiators": {...}
    # }
    source_page: int
    bounding_box: tuple              # (x, y, w, h) in source page
```

---

## 5. Ingestion Pipeline — Detailed Design

### 5.1 Agent Inventory

| Agent | Input | Output | Parallelizable |
|---|---|---|---|
| `PageSegmenter` | Page image | List of regions with types + bounding boxes | Yes (per page) |
| `DocumentClassifier` | First N pages + metadata | Document type label + confidence | No (runs once) |
| `ChunkClassifier` | Text region + document type bias | `entry_type` label | Yes (per region) |
| `ImageClassifier` | Image region | Image role label (diagram, reference, positional, decorative, state_repr) | Yes (per region) |
| `DiagramAnalyzer` | Cropped image (logic diagram) | Structured logic extraction + description | Yes (per image) |
| `ReferenceImageProcessor` | Cropped image (reference) | Multi-level descriptions + differentiators | Yes (per image) |
| `PositionalAnalyzer` | Cropped image (layout) | Coordinate mapping + position-to-content map | Yes (per image) |
| `TypeSpecificExtractor` | Text chunk + entry_type | `structured_data` dict | Yes (per chunk) |
| `VernacularGenerator` | KnowledgeEntry (any) | List of spoken-language aliases | Yes (per entry) |
| `ModuleAssembler` | All extracted content for a logical section | Complete KnowledgeEntry | Partially (per section) |
| `ReferenceLinker` | All entries | Entries with populated `references` and `referenced_by` | No (needs full set) |
| `QualityChecker` | Complete entry | Validation report + `requires_review` flag | Yes (per entry) |

### 5.2 Pipeline Flow

```
PHASE 1: SEGMENTATION
──────────────────────
Input: Document (PDF)

  ┌─────────────────────────────────┐
  │  For each page (PARALLEL):      │
  │    PageSegmenter(page_image)    │
  │      → text_regions[]           │
  │      → image_regions[]          │
  └─────────────────────────────────┘
  
  DocumentClassifier(first_N_pages)
    → document_type                        # runs once, in parallel with segmentation


PHASE 2: CLASSIFICATION
───────────────────────
Depends on: Phase 1

  ┌──────────────────────────────────────────────────┐
  │  For each text_region (PARALLEL):                │
  │    ChunkClassifier(region, document_type_bias)   │
  │      → entry_type                                │
  │                                                  │
  │  For each image_region (PARALLEL):               │
  │    ImageClassifier(region)                       │
  │      → image_role                                │
  └──────────────────────────────────────────────────┘


PHASE 3: EXTRACTION
───────────────────
Depends on: Phase 2

  ┌──────────────────────────────────────────────────────┐
  │  For each classified text chunk (PARALLEL):          │
  │    TypeSpecificExtractor(chunk, entry_type)          │
  │      → structured_data                               │
  │                                                      │
  │  For each classified image (PARALLEL by role):       │
  │    if role == "logic_diagram":                       │
  │      DiagramAnalyzer(image) → structured_logic       │
  │    elif role == "reference":                         │
  │      ReferenceImageProcessor(image) → descriptions   │
  │    elif role == "positional_layout":                 │
  │      PositionalAnalyzer(image) → coordinate_map      │
  │    elif role == "state_repr":                        │
  │      ReferenceImageProcessor(image) → descriptions   │
  │    elif role == "decorative":                        │
  │      brief_description(image) → summary only         │
  └──────────────────────────────────────────────────────┘


PHASE 4: ASSEMBLY
─────────────────
Depends on: Phase 3

  ┌──────────────────────────────────────────────────────────┐
  │  For each logical section (PARALLEL where independent):  │
  │    ModuleAssembler(text_extractions, image_extractions)  │
  │      → KnowledgeEntry (draft)                            │
  │                                                          │
  │  For each draft entry (PARALLEL):                        │
  │    VernacularGenerator(entry)                            │
  │      → vernacular_terms[]                                │
  └──────────────────────────────────────────────────────────┘


PHASE 5: LINKING & VALIDATION
─────────────────────────────
Depends on: Phase 4

  ReferenceLinker(all_entries)            # SEQUENTIAL — needs full set
    → entries with cross-references

  ┌──────────────────────────────────────────────┐
  │  For each linked entry (PARALLEL):           │
  │    QualityChecker(entry)                     │
  │      → validation_report                     │
  │      → requires_review flag                  │
  └──────────────────────────────────────────────┘


PHASE 6: STORAGE
────────────────
Depends on: Phase 5

  Write all entries to KnowledgeStore
  Write all MediaBlobs to blob storage
  Index entries for retrieval (embeddings, tags, vernacular terms)
```

### 5.3 Parallelization Strategy

The pipeline has natural parallelism at the **page level** (Phase 1), the **region level** (Phases 2-3), and the **entry level** (Phases 4-5 QC). The only sequential bottlenecks are:

- `DocumentClassifier` — runs once, fast, not a bottleneck
- `ReferenceLinker` — needs all entries before it can link; however, it's a graph operation on metadata, not an LLM call, so it's inherently fast
- `KnowledgeStore` write — can be batched

For a 23-page document like the KTANE manual, the expected parallelism profile is:

| Phase | Unit of Parallelism | Expected Concurrency | Estimated Time |
|---|---|---|---|
| Segmentation | Per page | 23 concurrent | ~5s (vision call per page) |
| Classification | Per region | ~50-80 concurrent | ~3s (lightweight calls) |
| Extraction | Per chunk/image | ~30-50 concurrent | ~10s (deep analysis calls) |
| Assembly | Per section | ~12 concurrent | ~5s |
| Linking | Sequential | 1 | ~1s (graph operation) |
| Validation | Per entry | ~15 concurrent | ~3s |

**Total estimated wall-clock time: ~27s** vs ~3-5 minutes sequential.

Implementation uses `asyncio` with semaphore-controlled concurrency to respect API rate limits:

```python
async def run_phase(agents: list[AgentCall], max_concurrency: int = 10):
    semaphore = asyncio.Semaphore(max_concurrency)
    
    async def bounded_call(agent_call):
        async with semaphore:
            trace = TraceEvent.start(agent_call)
            try:
                result = await agent_call.execute()
                trace.complete(result)
                return result
            except Exception as e:
                trace.fail(e)
                raise
    
    return await asyncio.gather(*[bounded_call(ac) for ac in agents])
```

### 5.4 Image Ingestion — Deep Dive

Images are the most challenging ingestion target. The `ImageClassifier` first categorizes every image into one of five roles, which determines the downstream processing path.

#### 5.4.1 Image Role Classification

| Role | Description | Processing Agent | Priority |
|---|---|---|---|
| `logic_diagram` | Encodes decision logic (Venn diagrams, flowcharts) | `DiagramAnalyzer` | Critical — wrong extraction = wrong answers |
| `reference` | Used for identification (ports, batteries, symbols) | `ReferenceImageProcessor` | High — powers "what is this?" queries |
| `positional_layout` | Position is data (grids, button layouts) | `PositionalAnalyzer` | High — spatial relationships matter |
| `state_repr` | Shows what a module/component looks like | `ReferenceImageProcessor` | Medium — used for identification flow |
| `decorative` | Contextual/illustrative, not directly referenced | Brief description only | Low — minimal processing |

#### 5.4.2 DiagramAnalyzer — Structured Logic Extraction

For logic diagrams, the agent must extract not just a description but the **operational logic** the diagram encodes:

```python
# Input: Complicated Wires Venn diagram image
# Output:
{
    "type": "venn_logic",
    "dimensions": ["has_red", "has_blue", "has_star", "led_on"],
    "regions": [
        {"conditions": {"has_red": False, "has_blue": False, "has_star": False, "led_on": False}, "action": "C"},
        {"conditions": {"has_red": True,  "has_blue": False, "has_star": False, "led_on": False}, "action": "S"},
        # ... all 16 combinations enumerated
    ],
    "action_legend": {
        "C": "Cut the wire",
        "D": "Do not cut the wire",
        "S": "Cut if last digit of serial number is even",
        "P": "Cut if bomb has a parallel port",
        "B": "Cut if bomb has two or more batteries"
    },
    "extraction_confidence": 0.85,
    "raw_description": "Four-set Venn diagram with overlapping regions..."
}
```

**Fallback strategy:** If structured extraction confidence is below threshold (0.7), the entry stores the raw image blob and a text description. Query-time agents fall back to conversational walkthrough using the image.

#### 5.4.3 ReferenceImageProcessor — Multi-Level Descriptions

For reference images, the agent generates descriptions at multiple abstraction levels to support different query styles:

```python
# Input: Parallel port image
# Output:
{
    "descriptions": {
        "technical": "DB-25 parallel port, 25 pins in two rows (13/12)",
        "layperson": "wide rectangular connector with two rows of small holes",
        "distinguishing_features": [
            "widest connector type on the bomb",
            "two rows of holes: 13 on top, 12 on bottom",
            "screw mounts on each end"
        ],
        "commonly_confused_with": ["serial_port", "dvi_d"],
        "differentiators": {
            "vs_serial_port": "parallel is much wider with more holes; serial is narrow with fewer pins",
            "vs_dvi_d": "parallel has round holes; DVI-D has a flat rectangular pin cluster"
        }
    }
}
```

---

## 6. Query Pipeline — Detailed Design

### 6.1 Transcript Preprocessing

Raw Whisper output undergoes several transformations before reaching the Router:

```python
class TranscriptPreprocessor:
    """
    Cleans transcribed speech into structured intent.
    Has read access to KnowledgeStore vocabulary index
    for phonetic normalization.
    """

    def process(self, raw_transcript: str, session: Session) -> ProcessedQuery:
        # Step 1: Disfluency removal
        #   "um so like I have these uh wires" → "I have these wires"

        # Step 2: Self-correction detection
        #   "it's red... wait no, it's blue" → final answer: blue

        # Step 3: Phonetic normalization against known vocabulary
        #   Knowledge store maintains a term index (tags + vernacular_terms)
        #   "pair of lel port" → "parallel port"
        #   "the last wire is wait" → "the last wire is white" (color context)

        # Step 4: Implicit reference resolution
        #   "the other one" → resolves from session.active_entities
        #   "same as before" → pulls from session.history

        # Step 5: Confidence annotation
        #   "I think it's yellow" → {value: "yellow", confidence: 0.7}
        #   "it's definitely red" → {value: "red", confidence: 0.95}

        # Step 6: Entity extraction
        #   Pulls out colors, numbers, positions, labels

        return ProcessedQuery(
            cleaned_text=...,
            extracted_entities=...,
            uncertainty_flags=...,
            corrections_detected=...,
            references_to_resolve=...
        )
```

**Architectural note:** The preprocessor requires read access to the KnowledgeStore's vocabulary index. This creates a coupling between preprocessing and storage, which is an intentional design tradeoff — the alternative (passing misspelled/misheard terms downstream) produces worse outcomes.

### 6.2 Router

The Router classifies the query into a workflow. It is a **classifier, not an orchestrator** — it selects from a fixed menu, never invents new workflows.

```python
class Router:
    def classify(
        self,
        query: ProcessedQuery,
        session: Session,
        document_type: str
    ) -> tuple[WorkflowID | None, dict]:
        """
        Returns (workflow_id, extracted_params) or (None, {}) if no match.
        
        Classification considers:
          1. Query intent (identification, instruction, lookup, etc.)
          2. Session state (is there an active module? incomplete steps?)
          3. Document type bias (recipes default to procedural flow)
        """
```

**Router classification rules:**

| Condition | Selected Workflow |
|---|---|
| No module identified + query describes something visual/physical | `identification` |
| Module identified + "how" / "what do I do" / action request | `instruction` |
| Query asks for specific data point or fact | `lookup` |
| IdentifierAgent returns multiple candidates above threshold | `disambiguation` |
| Session has active module with incomplete steps | `stateful_continuation` |
| None of the above match confidently | `None` → escalate to Tier 2/3 |

**Document type biases:**

| Document Type | Bias |
|---|---|
| Game manual | Favor `identification` and `instruction` workflows |
| Recipe/cookbook | Default to `stateful_continuation` (linear progression) |
| Assembly guide | Default to `stateful_continuation` with prerequisite checks |
| Reference manual | Favor `lookup` workflow |
| Troubleshooting guide | Favor `instruction` (decision-tree traversal) |

### 6.3 Tier 1 — Deterministic Workflows

Each workflow is a fixed sequence of agents with typed inputs and outputs at every handoff point.

#### 6.3.1 Identification Workflow

**Trigger:** User describes something they see; no module currently active.

```
ProcessedQuery
  → IdentifierAgent
      Input:  query text, extracted entities, visual descriptors
      Output: list[Candidate(entry_id, confidence, match_reason)]
      
      if single candidate above threshold (>0.8):
        → ContextGatherer
            Input:  matched entry_id
            Output: full entry + referenced entries + media descriptions
            
            → Responder
                Input:  entry context, session, urgency level
                Output: confirmation message + brief description
                
      if multiple candidates (all >0.4, none >0.8):
        → TYPED FAILURE: AMBIGUOUS_MATCH(candidates)
        
      if no candidates above 0.4:
        → TYPED FAILURE: ZERO_MATCHES(query)
```

#### 6.3.2 Instruction Workflow

**Trigger:** User asks how to do something; module identified.

```
ProcessedQuery + active_module
  → PrerequisiteChecker
      Input:  entry structured_data, session.known_facts
      Output: {met: [...], missing: [...]}
      
      if missing prerequisites:
        → InfoGatherer
            Input:  missing prerequisites list
            Output: targeted questions for user
            [PAUSE — wait for user response, update session.known_facts]
            
      → InstructionWalker
          Input:  structured_data, session.known_facts, entry_type
          Output: specific instruction/action to take
          
          → Responder
              Input:  instruction, confidence, urgency
              Output: voice-formatted response
```

#### 6.3.3 Lookup Workflow

**Trigger:** User asks for a specific fact.

```
ProcessedQuery
  → RetrieverAgent
      Input:  query terms, entity types sought
      Output: matching entry + specific data point
      
      → Responder
          Input:  data point, source entry
          Output: concise answer
```

#### 6.3.4 Disambiguation Workflow

**Trigger:** IdentifierAgent returned multiple candidates.

```
Candidates list
  → DisambiguationAgent
      Input:  candidates with their distinguishing_features and differentiators
      Output: optimal distinguishing question (maximizes info gain)
      [PAUSE — wait for user response]
      
      → IdentifierAgent (re-run with narrowed candidates)
          if resolved: → route to Identification or Instruction workflow
          if still ambiguous: → loop (max 3 iterations, then Tier 2)
```

#### 6.3.5 Stateful Continuation Workflow

**Trigger:** Active module with incomplete steps; user says "what's next" or provides new state info.

```
ProcessedQuery + session.active_module + session.step_state
  → StateManager
      Input:  current step, user input, step history
      Output: updated state, next step reference
      
      → InstructionWalker
          Input:  next step from structured_data, updated state
          Output: next instruction
          
          → StateManager (save)
          → Responder
```

### 6.4 Tier 2 — Guided Recovery

When a Tier 1 workflow produces a **typed failure**, recovery strategies are selected based on failure type. Recoveries are short (1-2 agent) sequences, not full workflows.

```python
RECOVERY_REGISTRY = {
    "ZERO_MATCHES": [
        BroadenSearchRecovery,       # relax query constraints, retry
        ClarificationRecovery,       # ask user to describe differently
        # if both fail → escalate to Tier 3
    ],
    "AMBIGUOUS_MATCH": [
        DisambiguationRecovery,      # ask distinguishing question
        # if 3 rounds fail → escalate to Tier 3
    ],
    "MISSING_PREREQUISITE": [
        InfoGatherRecovery,          # ask user for specific info
        AssumeDefaultsRecovery,      # proceed with reasonable defaults, flag uncertainty
    ],
    "ENTRY_TYPE_UNSUPPORTED": [
        RawTextFallbackRecovery,     # answer from raw_text instead of structured_data
    ],
    "CONFIDENCE_TOO_LOW": [
        ConfirmationRecovery,        # present best guess, ask user to confirm
    ],
}
```

Each recovery receives the **full failure context**:

```python
@dataclass
class FailureContext:
    failure_type: str
    failed_agent: str
    agent_input: dict
    agent_output: dict               # partial/failed output
    candidates: list | None          # for AMBIGUOUS_MATCH
    query: ProcessedQuery
    session: Session
    workflow_id: str
    trace_id: str
```

### 6.5 Tier 3 — Agentic Execution Fallback

When Tiers 1 and 2 cannot resolve the query, an orchestrator agent operates with more freedom. Key constraints:

1. **Receives the complete failure trace** from Tiers 1-2 — knows what was already tried.
2. **Has access to all workflow agent components** plus additional utility agents.
3. **Can only answer from KnowledgeStore content** — never from general knowledge (prevents hallucination).
4. **All tool calls are logged** with the same tracing infrastructure as Tiers 1-2.
5. **Has a hard turn limit** (e.g., 10 agent calls) to prevent runaway execution.

```python
class Tier3Orchestrator:
    available_agents = [
        # All Tier 1 workflow components
        IdentifierAgent, RetrieverAgent, InstructionWalker,
        PrerequisiteChecker, InfoGatherer, DisambiguationAgent,
        StateManager, ContextGatherer,
        
        # Additional utility agents (Tier 3 only)
        ReasoningAgent,          # general-purpose chain-of-thought
        DocumentSearchAgent,     # raw full-text search over knowledge store
        UserDialogueAgent,       # freeform conversational interaction
    ]
    
    constraints = {
        "max_agent_calls": 10,
        "knowledge_store_only": True,     # no general knowledge answers
        "must_cite_entry_id": True,       # every claim traces to an entry
    }
```

**Tier 3 as a workflow incubator:** Every query that reaches Tier 3 is logged with full context. Periodic review of Tier 3 logs reveals patterns. If >5% of queries follow a similar Tier 3 path, that pattern should be promoted to a new Tier 1 workflow.

### 6.6 Parallelization in Query Pipeline

Query-time parallelism is more constrained than ingestion (user is waiting), but opportunities exist:

| Step | Parallelizable? | Strategy |
|---|---|---|
| Whisper transcription | No (streaming input) | N/A |
| TranscriptPreprocessor | Partially — phonetic normalization can run alongside entity extraction | Fan-out substeps |
| Router classification | No (lightweight, fast) | N/A |
| IdentifierAgent retrieval | Yes — search embeddings, tags, and vernacular in parallel | `asyncio.gather` over index types |
| ContextGatherer | Yes — fetch main entry + referenced entries in parallel | `asyncio.gather` over entry IDs |
| PrerequisiteChecker | No (logic evaluation, fast) | N/A |
| ResponseFormatter | No (depends on final answer) | N/A |

**Critical optimization:** The `IdentifierAgent` performs three parallel searches — embedding similarity, tag matching, and vernacular term matching — and merges results. This is the highest-latency step and benefits most from parallelism.

```python
async def identify(self, query: ProcessedQuery) -> list[Candidate]:
    embedding_results, tag_results, vernacular_results = await asyncio.gather(
        self.embedding_search(query.cleaned_text),
        self.tag_search(query.extracted_entities),
        self.vernacular_search(query.cleaned_text, query.extracted_entities)
    )
    return self.merge_and_rank(embedding_results, tag_results, vernacular_results)
```

**Speculative execution:** For high-confidence router decisions, begin ContextGatherer while IdentifierAgent is still running on the most likely candidate. If the Identifier confirms, ContextGatherer is already done. If it doesn't, discard the speculative result.

---

## 7. Response Formatting for Voice

The `ResponseFormatter` adapts every response for spoken delivery. It considers urgency (from session context or explicit user signals) and interaction phase.

### 7.1 Formatting Rules

| Principle | Rationale |
|---|---|
| Chunk into single steps | User can't re-read; one action per turn |
| Confirm inputs before irreversible actions | "You said two red wires and serial ends in 7 — cut the last red." |
| Progressive disclosure | Answer first, offer elaboration: "Want me to explain why?" |
| No visual references | "See diagram 3" is useless; describe what they should see instead |
| Periodic state summaries | "Recap: serial ends in 7, two batteries, no parallel port. Still right?" |

### 7.2 Urgency Levels

```python
class ResponseFormatter:
    def format(self, answer: AgentResponse, session: Session) -> VoiceResponse:
        urgency = session.urgency  # "high", "normal", "low"
        
        if urgency == "high":
            # Minimal. Direct. "Cut wire two."
            pass
        elif urgency == "normal":
            # Confirm + answer. "Two reds, serial odd — cut the last red."
            pass
        else:  # "low" — exploratory, learning
            # Full explanation + offer to elaborate.
            pass
```

---

## 8. Session State Management

```python
@dataclass
class Session:
    session_id: str
    document_id: str
    document_type: str
    
    # Active context
    active_module: str | None          # currently working module entry_id
    step_state: dict                   # progress within a stateful module
    known_facts: dict                  # serial number, battery count, etc.
    
    # History
    resolved_modules: list[str]        # completed module entry_ids
    turn_history: list[Turn]           # full conversation record
    
    # User adaptation
    user_vocabulary: dict[str, str]    # "the wide one" → "parallel_port"
    urgency: str                       # "high", "normal", "low"
    expertise_level: str               # "beginner", "intermediate", "expert"
    
    # Tracing
    trace_ids: list[str]               # all trace IDs for this session
```

**State summary cadence:** Every 5 turns, or when switching modules, or when known_facts change, the system proactively confirms state: "Quick recap: I've got serial ending in 7, two batteries, parallel port present. Still correct?"

---

## 9. Traceability & Logging

### 9.1 Design Philosophy

Every operation — ingestion or query — produces structured trace events. Traces are the **single source of truth** for debugging, replay, quality monitoring, and workflow improvement.

### 9.2 Trace Event Schema

```python
@dataclass
class TraceEvent:
    # Identity
    trace_id: str                  # unique per event
    parent_trace_id: str | None    # links to parent (pipeline run or query session)
    span_id: str                   # groups events within a workflow step
    
    # What
    event_type: str                # "agent_call", "handoff", "failure", "recovery", "tier_escalation"
    agent_name: str                # which agent
    workflow_id: str | None        # which workflow (None for Tier 3)
    tier: int                      # 1, 2, or 3
    
    # Timing
    timestamp_start: datetime
    timestamp_end: datetime
    duration_ms: int
    
    # Data
    input_data: dict               # what the agent received (serializable)
    output_data: dict              # what the agent produced
    
    # Outcome
    status: str                    # "success", "failure", "timeout", "skipped"
    failure_type: str | None       # typed failure code if applicable
    failure_detail: str | None     # human-readable failure description
    
    # Context
    session_id: str | None         # for query-time events
    document_id: str | None        # for ingestion events
    
    # Performance
    token_count_in: int | None     # LLM tokens consumed (input)
    token_count_out: int | None    # LLM tokens consumed (output)
    model_id: str | None           # which model was called
```

### 9.3 What Gets Traced

**Ingestion pipeline:**

| Event | Logged Fields |
|---|---|
| Page segmentation | Page number, regions found, bounding boxes, time |
| Document classification | Document type, confidence, model used |
| Chunk/image classification | Region ID, classified type, confidence |
| Extraction | Entry type, structured_data output, confidence, time |
| Vernacular generation | Entry ID, generated terms |
| Quality check | Entry ID, validation result, issues found, requires_review |
| Knowledge store write | Entry ID, blob IDs, index updates |

**Query pipeline:**

| Event | Logged Fields |
|---|---|
| Transcript preprocessing | Raw text, cleaned text, corrections, entities, confidence flags |
| Router classification | Selected workflow, confidence, document type bias applied |
| Every agent call in workflow | Full input/output, timing, token count |
| Handoff between agents | Source agent, target agent, data passed |
| Typed failure | Failure type, failed agent, context |
| Recovery attempt | Recovery strategy, input, outcome |
| Tier escalation | From tier, to tier, failure trace reference |
| Response formatting | Raw answer, formatted answer, urgency level |

### 9.4 Trace Hierarchy

```
Ingestion Run (trace_id: "ingest-001")
  ├── Phase 1: Segmentation
  │     ├── PageSegmenter page 1 (span: "seg-p1")
  │     ├── PageSegmenter page 2 (span: "seg-p2")  ← parallel
  │     └── DocumentClassifier (span: "doc-class")  ← parallel with above
  ├── Phase 2: Classification
  │     ├── ChunkClassifier region 1 (span: "chunk-r1")
  │     └── ImageClassifier region 2 (span: "img-r2")  ← parallel
  └── ...

Query Session (trace_id: "session-042")
  ├── Turn 1 (span: "turn-1")
  │     ├── Preprocessing (span: "preproc-1")
  │     ├── Router (span: "router-1") → workflow: identification
  │     ├── IdentifierAgent (span: "ident-1") → AMBIGUOUS_MATCH
  │     ├── [Tier 2] DisambiguationRecovery (span: "disamb-1")
  │     └── ResponseFormatter (span: "format-1")
  ├── Turn 2 (span: "turn-2")
  │     ├── Preprocessing (span: "preproc-2")
  │     ├── IdentifierAgent (span: "ident-2") → resolved
  │     └── ...
```

### 9.5 Queryable Log Storage

Traces are stored in a structured format (JSON lines or a lightweight database) queryable by:

- `session_id` — replay an entire user session
- `trace_id` — inspect a specific pipeline run
- `agent_name` — analyze performance of a specific agent
- `failure_type` — find all queries that hit a specific failure mode
- `tier >= 2` — find all queries that needed recovery or agentic fallback
- `duration_ms > threshold` — find slow operations
- `confidence_score < threshold` — find low-confidence extractions

### 9.6 Monitoring Dashboards (Recommended Metrics)

| Metric | Purpose |
|---|---|
| % queries resolved at Tier 1 / 2 / 3 | System health — Tier 3 should trend downward |
| Mean latency per workflow | Performance monitoring |
| Most common failure types | Guides workflow improvement |
| Entries with `requires_review = True` | Ingestion quality monitoring |
| Tier 3 pattern clustering | Identifies candidates for new Tier 1 workflows |
| Token cost per query (by tier) | Cost monitoring — Tier 3 is most expensive |
| Disambiguation rounds per query | UX quality — fewer rounds = better vernacular/descriptions |

---

## 10. Feedback Loop: Query-Time → Ingestion Improvement

### 10.1 Signals

| Signal | Meaning | Action |
|---|---|---|
| IdentifierAgent consistently fails on an entry | Vernacular terms are insufficient | Queue VernacularGenerator re-run |
| Disambiguation takes 3+ rounds for specific entries | Differentiators aren't distinctive enough | Queue ReferenceImageProcessor re-run |
| Users frequently use a term not in vocabulary index | Missing vernacular term | Add to entry's `vernacular_terms` |
| Tier 3 resolves using raw_text fallback | Structured extraction failed or was incomplete | Queue TypeSpecificExtractor re-run |
| QualityChecker flagged entry + queries against it fail | Extraction quality issue confirmed | Prioritize for human review |

### 10.2 Implementation

```python
class FeedbackCollector:
    """
    Listens to query trace events and aggregates signals
    for ingestion improvement.
    """
    
    def on_identification_failure(self, trace: TraceEvent, entry_ids_tried: list[str]):
        # Increment miss counter for relevant entries
        # If counter > threshold, queue for re-enrichment
        pass
    
    def on_new_user_vocabulary(self, term: str, resolved_entry_id: str):
        # Add term to entry's vernacular_terms
        # Update vocabulary index
        pass
    
    def on_tier3_resolution(self, trace: TraceEvent, resolution_path: list[str]):
        # Log the resolution pattern
        # Cluster with similar Tier 3 resolutions
        # Alert if cluster size > threshold (candidate for new workflow)
        pass
```

---

## 11. Open Questions & Risks

### 11.1 Open Design Questions

| Question | Options | Current Leaning |
|---|---|---|
| Knowledge store backend | SQLite, PostgreSQL, file-based JSON | SQLite for prototype; PostgreSQL for production |
| Embedding model for retrieval | OpenAI, Cohere, local model | Local model to avoid latency of external API call |
| LLM for agent calls | GPT-4o, Claude, mixed | Mixed — lightweight agents use smaller models, complex ones use frontier |
| Ingestion: human-in-the-loop for low-confidence extractions? | Fully automated vs. review queue | Review queue for entries where `confidence < 0.7` |
| Session persistence | In-memory vs. database | Database — sessions may span disconnects |

### 11.2 Known Risks

| Risk | Severity | Mitigation |
|---|---|---|
| DiagramAnalyzer produces wrong structured logic | **High** — wrong answers downstream | QualityChecker + confidence thresholds + raw_text fallback |
| Whisper transcription errors compound through pipeline | **Medium** — phonetic normalization helps but isn't perfect | Confirmation prompts for high-stakes actions |
| Tier 3 hallucination (answering from general knowledge) | **High** — user trusts the system | Hard constraint: Tier 3 must cite entry_id for every claim |
| Generalization breaks on unforeseen document types | **Medium** — new entry_types may be needed | Entry type system is extensible; monitor and add as needed |
| Latency under voice interaction expectations | **Medium** — users expect <2s responses | Parallel retrieval, speculative execution, model size optimization |

---

## 12. Implementation Roadmap

### Phase 1: KTANE End-to-End Prototype

- Manually segment KTANE manual into per-module page ranges
- Implement TypeSpecificExtractor for `decision_tree`, `reference_table`, `visual_guide`
- Implement KnowledgeStore with SQLite
- Implement Tier 1 workflows: Identification, Instruction, Lookup
- Implement ResponseFormatter for voice
- Integrate Whisper + TTS
- Validate: can a user defuse a bomb using only voice interaction?

### Phase 2: Automated Ingestion Pipeline

- Implement PageSegmenter, DocumentClassifier, ChunkClassifier, ImageClassifier
- Implement DiagramAnalyzer, ReferenceImageProcessor, PositionalAnalyzer
- Implement VernacularGenerator
- Implement QualityChecker with validation strategies per entry type
- Implement full tracing infrastructure
- Validate: ingest KTANE manual automatically, compare to Phase 1 manual output

### Phase 3: Generalization Stress Test

- Ingest a recipe document → validate query pipeline handles linear procedures
- Ingest an IKEA assembly guide → validate image-heavy documents
- Ingest a tax form guide → validate dense reference text
- Identify where abstractions break → add entry types, workflows, recovery strategies

### Phase 4: Production Hardening

- Implement Tier 2 recovery strategies
- Implement Tier 3 agentic fallback with constraints
- Implement feedback loop (query-time → ingestion improvement)
- Implement monitoring dashboards
- Load testing and latency optimization
