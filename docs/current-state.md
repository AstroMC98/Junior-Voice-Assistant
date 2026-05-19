# Junior — Current State

> **Purpose:** Living reference for the Data Ingestion pipeline and Voice Conversation module. Edit freely to capture decisions, open questions, and design direction.

---

## 1. Data Ingestion

### 1.1 Overview

Users create a **Guide** by providing source material through one of three input methods. The material is processed by Claude into a structured step-by-step guide and persisted in Vercel KV (Redis). Images are stored separately in Vercel Blob and referenced by URL.

### 1.2 Input Sources

| Source | Component | Mechanism |
|--------|-----------|-----------|
| **PDF** | `PdfUploader.tsx` | Rendered client-side via `pdfjs-dist`; each page becomes a base64 PNG |
| **URL** | `UrlFetcher.tsx` | Fetched server-side via `/api/fetch-url`; HTML stripped to plain text (50 KB cap) |
| **Camera** | `CameraCapture.tsx` | Single frame captured via `getUserMedia()`; encoded as base64 PNG |

### 1.3 File Map

```
components/guide-creator/
  GuideCreator.tsx        — Orchestrator; collects inputs, POSTs to /api/guides
  PdfUploader.tsx         — PDF → per-page base64 PNG array (pdfjs-dist v5.7)
  UrlFetcher.tsx          — Submits URL; calls /api/fetch-url
  CameraCapture.tsx       — getUserMedia() → canvas → base64 capture

app/api/
  guides/route.ts         — POST /api/guides: validates, uploads images to Blob, calls processGuide()
  guides/[id]/route.ts    — GET /api/guides/:id: retrieve; POST: fork
  fetch-url/route.ts      — GET /api/fetch-url: SSRF-guarded fetch, HTML → text, 50 KB limit

api/
  index.py                — FastAPI equivalents of all TS routes (Mangum adapter)
  claude.py               — process_guide() and session_turn() in async Python
  kv.py                   — Upstash Redis REST wrappers
  blob.py                 — Vercel Blob HTTP PUT wrappers

lib/
  claude.ts               — processGuide(), sessionTurn() — Anthropic SDK calls
  kv.ts                   — getGuide(), saveGuide() — Vercel KV wrappers
  blob.ts                 — uploadImage() — Vercel Blob wrapper
  types.ts                — Guide, Step, SessionResponse type definitions
```

### 1.4 Data Flow

```
USER INPUT
  PDF → pdfjs (browser) → base64 PNG[]
  URL → /api/fetch-url  → plain text string
  Camera → canvas        → base64 PNG

        ↓  POST /api/guides
        {source, title, text?, images?[]}

INGESTION API (guides/route.ts)
  1. Validate source + title
  2. Upload each image → Vercel Blob → get public URL[]
  3. Call processGuide(source, {text | imageUrls})

CLAUDE PROCESSING (lib/claude.ts → processGuide)
  Model: claude-sonnet-4-6 (vision + text)
  PDF input:  page images labeled [Page 1], [Page 2]...
  URL input:  raw text string
  Output:     Step[] — {index, title, content, image_index?, crop?}

STORAGE
  Guide { id, title, source, steps[], created_at, fork_of? }
  → Vercel KV  keyed as  guide:{id}
```

### 1.5 Data Structures

```typescript
type Step = {
  index: number
  title: string
  content: string
  image_url?: string       // Vercel Blob public URL
  image_index?: number     // References [Page N] from PDF
  crop?: { x: number; y: number; w: number; h: number }  // % coordinates
}

type Guide = {
  id: string
  title: string
  source: 'pdf' | 'url' | 'camera'
  steps: Step[]
  fork_of?: string
  created_at: number
}
```

### 1.6 Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| PDF rendering | `pdfjs-dist` v5.7 (browser) | Offloads heavy work to client; avoids server memory spikes |
| Image storage | Vercel Blob | Public CDN URLs; referenced in Claude prompts for vision |
| Guide persistence | Vercel KV (Redis) | Fast key-value reads; guides accessed by ID on session start |
| AI processing | Claude Sonnet 4.6 (vision) | Handles both image and text sources in a single call |
| SSRF protection | Blocked-host allowlist in fetch-url | Prevents internal network access via user-supplied URLs |

### 1.7 Known Gaps & Open Questions

- **No client-side page count limit** — large PDFs (100+ pages) will be slow to render and may crash on low-memory devices. Should we cap at N pages before upload?
- **50 KB text cap on URL fetch** — truncates long guides. Is this the right threshold, or should we chunk and merge?
- **No image size validation** — a single high-res camera capture could be large. Should we downsample before base64 encoding?
- **Fork metadata** — `/api/guides/[id]` POST creates a copy but there is no UI to surface forked guides or a lineage view.
- **No versioning** — overwriting a guide's steps is destructive. Should edits create new versions or snapshots?
- **Dual backend** — both `app/api/` (Next.js) and `api/` (FastAPI/Python) implement the same routes. Which is authoritative? Is the Python backend still needed?

---

## 2. Voice Conversation Module

### 2.1 Overview

During a session, the user interacts with their guide entirely hands-free. They speak a question or command; the app transcribes it, sends it with guide context to Claude, and speaks the response back. An optional camera check-in lets Claude assess visual progress against the current step.

### 2.2 File Map

```
components/session/
  VoiceLoop.tsx       — Core loop: mic → transcription → API call → TTS playback
  ProgressCheck.tsx   — Camera capture → Claude visual assessment → TTS feedback
  SessionView.tsx     — Orchestrates stepIndex, showImage, lastSpeech state
  StepDisplay.tsx     — Renders current step title/content + prev/next navigation

app/api/
  session/route.ts    — POST /api/session: validates body, calls sessionTurn()

api/
  index.py            — POST /api/session (FastAPI equivalent)

lib/
  claude.ts           — sessionTurn(): builds system prompt, calls Claude, returns SessionResponse
  types.ts            — SessionResponse type definition
```

### 2.3 Voice Lifecycle

```
1. IDLE
   User taps "Tap to Speak"
   Status → 'listening'

2. RECORDING
   VoiceLoop.tsx: SpeechRecognition (or webkitSpeechRecognition)
   lang = 'en-US', interimResults = false
   Waits for browser to detect end-of-speech

3. TRANSCRIPTION (browser-native)
   event.results[0][0].transcript  (highest confidence)
   Status → 'thinking'

4. API CALL
   POST /api/session
   Body: { guide, currentStepIndex, transcript, photo? }

5. CLAUDE REASONING  (lib/claude.ts → sessionTurn)
   Model: claude-sonnet-4-6, max_tokens: 512
   System prompt carries: guide title, all steps, current step
   User content: [optional image block] + transcript text
   Returns JSON: { speech, action, step }

6. RESPONSE DISPATCH
   SessionView.tsx handleResponse():
     action = 'advance'     → setStepIndex(response.step)
     action = 'show_image'  → setShowImage(true)
     action = null          → no navigation

7. TTS PLAYBACK
   SpeechSynthesisUtterance(response.speech)
   rate = 1.05
   onend → status = 'idle'

→ Loop returns to step 1
```

### 2.4 Claude Decision Rules (sessionTurn system prompt)

| User says | Claude action | Navigation |
|-----------|--------------|------------|
| "next", "done", "continue" | `advance` | step + 1 |
| "back", "previous", "go back" | `advance` | step - 1 |
| "show me", "what does it look like" | `show_image` | stay |
| General question | `null` | stay |
| Photo provided | Assess vs current step; go/no-go + optional advance | varies |

Response target: **1–2 sentences, naturally spoken**.

### 2.5 SessionResponse Structure

```typescript
type SessionResponse = {
  speech: string                       // Spoken aloud via TTS
  action: 'show_image' | 'advance' | null
  step: number | null                  // 0-based index; null if no navigation
}
```

### 2.6 Status State Machine

```
VoiceLoop:      idle → listening → thinking → idle
ProgressCheck:  idle → capturing → checking → idle
SessionView:    tracks { stepIndex, showImage, lastSpeech }
```

### 2.7 Progress Check (Camera Assessment)

An optional "Check my progress" flow in `ProgressCheck.tsx`:

1. `getUserMedia({ video: { facingMode: 'environment' } })` — rear camera on mobile
2. Frame drawn to canvas → `toDataURL('image/jpeg', 0.85)` — lossy JPEG
3. POSTed to `/api/session` alongside a fixed transcript: `"Check my progress…"`
4. Claude receives the image + step context → returns pass/fail speech + optional advance
5. TTS plays the feedback; camera stream is released

### 2.8 Technology Choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Speech-to-text | Web Speech API (browser-native) | Zero latency, no API cost, works offline for transcription |
| Text-to-speech | SpeechSynthesis API (browser-native) | No streaming needed; system voice is acceptable for MVP |
| Camera capture | getUserMedia + canvas | Single frame capture; no continuous video stream sent to server |
| Image format | JPEG 0.85 for photos; PNG for PDF pages | JPEG reduces payload for camera; PNG preserves text fidelity for PDFs |
| AI model | Claude Sonnet 4.6 (vision + text) | Handles both text commands and camera photo assessments |

### 2.9 Known Gaps & Open Questions

- **Browser support** — SpeechRecognition is Chrome/Edge only. Safari has partial support. What's the fallback strategy for users on other browsers?
- **Language hardcoded to `en-US`** — No path to multilingual support today. Is this in scope?
- **`interimResults = false`** — No real-time transcription shown to user during speech. Would showing partial transcript reduce perceived latency?
- **No error recovery UX** — `rec.onerror` sets status back to `'idle'` silently. Users get no feedback on why the mic failed.
- **No conversation history** — Each turn is stateless from the session perspective. Claude has no memory of previous exchanges within the same session. Relevant for multi-turn clarifications.
- **TTS voice and rate** — `rate = 1.05` is hardcoded. Should users be able to adjust speed or voice?
- **Timeout on silence** — If the user stops mid-sentence, the browser may never fire `onresult`. No timeout to recover gracefully.
- **JPEG quality for small details** — 0.85 may not preserve fine detail in close-up step images. Dynamic quality or resolution scaling not implemented.
- **Sequential speak-then-navigate** — `onend` fires navigation after TTS completes. If speech is long, there is noticeable delay before the UI updates.
- **Dual backend** — Both TS and Python backends expose `/api/session`. Same question as ingestion: which is live?

---

## 3. Shared Infrastructure

| Service | Used by | Purpose |
|---------|---------|---------|
| Vercel KV (Redis) | Ingestion, Session | Guide read/write |
| Vercel Blob | Ingestion | Image CDN storage |
| Anthropic Claude Sonnet 4.6 | Both | Guide processing, session reasoning |
| Web Speech API | Voice module | STT + TTS (client-side) |
| pdfjs-dist v5.7 | Ingestion | Client-side PDF → PNG rendering |

---

## 4. Open Architecture Decisions

1. **Dual backend (Next.js vs FastAPI)** — Both `app/api/` and `api/` implement the same endpoints. Clarify which is deployed and whether the other should be removed.
2. **Guide editing** — No current path for a user to edit a generated guide's steps. Fork is the closest proxy. Intended design?
3. **Session persistence** — Sessions are ephemeral (in-memory React state). Should completed sessions be logged for analytics or replay?
4. **Offline / degraded mode** — If the Anthropic API is unavailable, both ingestion and voice fail hard. Is a graceful degradation mode needed?
5. **Authentication** — No user accounts today. Guides are accessible by ID with no auth. Is this intentional (shareable links) or a gap?
