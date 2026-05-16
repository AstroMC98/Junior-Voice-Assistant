# Junior — Design Spec
**Date:** 2026-05-16
**Status:** Approved

## Problem Definition

People doing hands-on tasks — cooking, repairs, assembly, playing KTANE — must repeatedly pause and look at a guide. Scrolling a recipe with floury hands or flipping through a 200-page manual while lying under a sink breaks flow and concentration. There is no hands-free assistant that understands *your specific guide* and can answer questions, surface the right diagram, and check your progress.

**Target user:** Anyone following a multi-step guide with their hands occupied.

**Primary inspiration:** *Keep Talking and Nobody Explodes* — one party has the visual problem, another has the guide. Junior collapses both roles into one voice-driven experience.

**Initial test case:** The KTANE Bomb Defusal Manual (bombmanual.com). Rich diagrams, genuinely complex steps, and the direct conceptual origin of the project.

---

## How the Solution Works

Junior is a web app where you load any guide (PDF, URL, or camera photo of a physical document), and then run a hands-free voice session against it. You navigate step-by-step by speaking, ask free-form questions, request visual references, and take progress-check photos — all without touching your phone or scrolling.

### User Flows

**1. Create a Guide**
- Upload a PDF, paste a URL, or photograph a physical document
- Claude processes the raw content: extracts structured steps, identifies associated images, and generates AI crop bounding boxes per step (what region of each image is most relevant to that step)
- Guide is saved to Vercel KV with a public nanoid slug (`/g/abc123`)
- Creator sees their guide and a shareable link

**2. Run a Session**
- User opens a guide (their own or via share link)
- Voice loop begins: Web Speech API captures speech → sent to Claude with full guide + current step in system prompt → Claude returns `{ speech, action, step }` → Speech Synthesis reads the response aloud
- Step navigation: saying "next", "done", "go back" advances or retreats
- Free-form Q&A: any question answered using guide context ("how many wires does a 6-wire module have?")
- Image display: triggered automatically on step advance (if the step has an image) or on voice request ("What do I expect to see?", "Show me the diagram") — Claude includes `{ action: "show_image" }` in its response and the UI renders the image with the AI crop overlay
- Progress check: user taps the camera button, photo is sent to Claude alongside current step context — Claude gives go/no-go feedback ("that looks right, move to the next step")

**3. Share and Fork**
- Any guide has a public share link: `/g/[id]`
- Recipient opens the link, runs a session, and can tap "Fork" to save a copy under a new ID for customisation
- Forks are saved immediately to Vercel KV with a new ID; `localStorage` tracks the list of guide IDs owned by this browser so the user can find their guides again without an account

---

## AI Design

### Guide Processing (one-time at creation)
```
System: You are processing a guide document. Extract ordered steps.
        For each step: title, content, and if an image is present on this page,
        return a bounding box { x, y, w, h } (as % of image dimensions) for
        the region most relevant to this step.
User:   [guide text + page images]
```

### Session Turn
```
System: You are Junior, a hands-free guide assistant.
        Guide: [full guide text]
        Current step: [N of M] — [step title]: [step content]
        Speak naturally and briefly. Confirm step aloud when user advances.
        When the user asks to see something visually, include a JSON action:
          { "action": "show_image", "step": N }
        On camera photo: assess whether it matches the current step. Give clear go/no-go.
        Always respond as valid JSON: { "speech": "...", "action": "show_image" | "advance" | null, "step": N | null }

User:   [voice transcript] + optional [image (progress check)]
```

The structured JSON response keeps the voice loop clean while enabling UI-driven side effects (image display, step advancement) without a separate tool-call round-trip.

---

## Data Model

```ts
type Guide = {
  id: string           // nanoid — public URL slug
  title: string
  source: 'pdf' | 'url' | 'camera'
  steps: Step[]
  fork_of?: string     // parent guide id if forked
  created_at: number
}

type Step = {
  index: number
  title: string
  content: string
  image_url?: string   // Vercel Blob URL
  crop?: {             // AI-generated bounding box (% of image)
    x: number
    y: number
    w: number
    h: number
  }
}
```

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | Next.js 14 (App Router) | Fast setup, API routes, Vercel-native |
| AI | Claude claude-sonnet-4-6 with vision | Single API handles OCR, Q&A, image analysis, progress check |
| Guide storage | Vercel KV (Redis) | No database setup, persistent, fast reads |
| Image storage | Vercel Blob | Paired with KV, trivial to use from Next.js |
| PDF rendering | pdf.js | Client-side PDF → image per page |
| Voice in | Web Speech API | Browser-native, no extra service or API key |
| Voice out | Web Speech Synthesis | Browser-native |
| Deployment | Vercel | Zero-config deploy from GitHub |

**No auth required.** Guides are identified by ID. Forks live in `localStorage` until saved. Sessions are stateless.

---

## Evaluation Method

Using the KTANE Bomb Defusal Manual as the primary test case:

1. **Task completion** — can a user defuse a Wires module guided solely by Junior, without touching the manual?
2. **Visual accuracy** — does "What do I expect to see?" surface the correct diagram with a sensible crop region?
3. **Q&A relevance** — does Junior answer module-specific questions correctly from the manual context?
4. **Progress check** — does the camera feedback give accurate go/no-go on a described scenario?

### Baseline Comparison
Direct ChatGPT/Claude without Junior:
- No guide context (answers from general training, not your specific document)
- No step tracking (loses position, requires re-prompting)
- No voice loop (requires typing)
- No image surface (can't show you the right diagram)
- No sharing/forking (ephemeral conversation)

---

## Limitations & Next Iterations

**Known limitations of v1:**
- Web Speech API accuracy degrades in noisy environments (kitchen, workshop)
- Forks not persistent across devices without an account
- PDF image extraction quality depends on PDF encoding (scanned PDFs may lose fidelity)
- No multi-language support

**Next iterations:**
- Whisper API for higher-accuracy voice recognition
- User accounts for persistent guide libraries across devices
- B/C image feature: user can drag/adjust the AI crop overlay mid-session
- Collaborative guide editing (shared edit link)
- Voice-activated progress check ("Junior, check my work") without a button tap
- Expand beyond cooking: auto-detect guide domain and adapt response tone/style
