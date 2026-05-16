# Junior

A hands-free guide assistant. Upload a PDF, URL, or camera photo of a guide, and Junior walks you through it step-by-step using voice commands.

## Architecture

```
Next.js (frontend)        FastAPI (backend)
──────────────────        ─────────────────
React UI             →    POST /api/guides        — create guide (Claude extracts steps)
app/g/[id]           →    GET  /api/guides/{id}   — fetch guide
                     →    POST /api/guides/{id}   — fork guide
VoiceLoop            →    POST /api/session        — voice/camera AI turn
UrlFetcher           →    GET  /api/fetch-url      — scrape URL text
```

Both run in the same Vercel project. In production, Next.js and FastAPI share the same domain — `/api/*` is routed to the Python serverless function via `vercel.json`.

**External services:** Anthropic Claude (AI), Vercel KV / Upstash Redis (guide storage), Vercel Blob (image hosting)

---

## Setup

### 1. System Requirements

| Tool | Version | Check |
|------|---------|-------|
| Node.js | 18+ | `node --version` |
| Python | 3.12+ | `python --version` |
| npm | 9+ | `npm --version` |

### 2. Clone and install Node dependencies

```bash
git clone <repo-url>
cd Junior
npm install
```

### 3. Set up Python environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

```bash
pip install fastapi "uvicorn[standard]" mangum anthropic upstash-redis httpx python-nanoid beautifulsoup4
```

To deactivate the virtual environment later: `deactivate`

### 4. Get an Anthropic API key

1. Go to [console.anthropic.com](https://console.anthropic.com) and sign in
2. Navigate to **API Keys** → **Create Key**
3. Copy the key (starts with `sk-ant-`) — you won't be able to see it again

### 5. Create a Vercel project and link storage

Junior uses Vercel KV (Redis) for guide storage and Vercel Blob for image hosting. Both require a Vercel account and a linked project.

**Create the project:**
1. Install the Vercel CLI: `npm i -g vercel`
2. Run `vercel login` and authenticate
3. Run `vercel link` in the project root — either create a new project or link to an existing one

**Add a KV store:**
1. Go to the [Vercel dashboard](https://vercel.com/dashboard) → your project → **Storage**
2. Click **Create Database** → select **KV**
3. Name it (e.g. `junior-kv`) and click **Create**
4. Once created, click **Connect to project** → select your project → **Connect**

**Add a Blob store:**
1. In the same **Storage** tab, click **Create Database** → select **Blob**
2. Name it (e.g. `junior-blob`) and click **Create**
3. Click **Connect to project** → select your project → **Connect**

### 6. Configure environment variables

**Option A — pull automatically with Vercel CLI (recommended):**
```bash
vercel env pull .env.local
```
This writes all Vercel-managed variables (`KV_REST_API_URL`, `KV_REST_API_TOKEN`, `BLOB_READ_WRITE_TOKEN`) to `.env.local` automatically. Then open the file and add the remaining variables manually.

**Option B — fill in manually:**
Open `.env.local` at the project root and fill in every value:

```env
# Anthropic — https://console.anthropic.com → API Keys
ANTHROPIC_API_KEY=sk-ant-...

# Vercel KV — dashboard → Storage → KV → .env.local tab → copy values
KV_REST_API_URL=https://...upstash.io
KV_REST_API_TOKEN=...

# Vercel Blob — dashboard → Storage → Blob → .env.local tab → copy values
BLOB_READ_WRITE_TOKEN=vercel_blob_rw_...

# Local dev only — points Next.js at the local FastAPI server
# Do NOT set these in the Vercel dashboard (leave unset in production)
NEXT_PUBLIC_API_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
```

> The last two variables (`NEXT_PUBLIC_API_URL`, `CORS_ORIGINS`) are for local development only. In production they must be unset so the frontend uses relative URLs on the same domain.

---

## Running Locally

Run the frontend and backend in two separate terminals:

**Terminal 1 — Next.js (frontend):**
```bash
npm run dev
# → http://localhost:3000
```

**Terminal 2 — FastAPI (backend, with .venv activated):**
```bash
uvicorn api.index:app --reload --port 8000
# → http://localhost:8000/docs  ← interactive API docs
```

### Verify it's working

```bash
# URL scraper — should return { "text": "..." }
curl "http://localhost:8000/api/fetch-url?url=https://example.com"

# SSRF protection — should return 403
curl "http://localhost:8000/api/fetch-url?url=http://localhost"

# Create a guide from plain text
curl -X POST http://localhost:8000/api/guides \
  -H "Content-Type: application/json" \
  -d '{"source":"url","title":"Test","text":"Step 1: Do the thing. Step 2: Done."}'
# → 201 with guide object including extracted steps
```

Open [http://localhost:3000](http://localhost:3000) and create a guide from a URL to test the full flow.

---

## Project Structure

```
app/                        Next.js App Router (frontend)
  g/[id]/page.tsx           — guide session page (client-side fetch)
  layout.tsx / page.tsx     — root layout and home page
  globals.css               — design system tokens + utility classes
api/                        FastAPI backend (Python)
  index.py                  — app entry point + all route handlers
  models.py                 — Pydantic models (Guide, Step, SessionResponse)
  claude.py                 — Anthropic client (process_guide, session_turn)
  kv.py                     — Vercel KV / Upstash Redis wrapper
  blob.py                   — Vercel Blob image upload
  utils.py                  — ID generation, JSON parsing, HTML stripping
components/
  guide-creator/            — PDF upload, URL fetch, camera capture
  session/                  — VoiceLoop, ProgressCheck, StepDisplay, ImageViewer
  layout/                   — AppShell (responsive mobile/desktop shell)
lib/
  types.ts                  — shared TypeScript types + API_BASE constant
design-system/              — Penpot handoff assets
requirements.txt            — Python dependencies
vercel.json                 — routes /api/* to Python function
```

---

## Deployment

```bash
vercel deploy
```

The `vercel.json` routes all `/api/*` traffic to the Python serverless function; Next.js handles everything else. No additional configuration needed if the KV and Blob stores are already linked.

**Environment variables in the Vercel dashboard:**
| Variable | Source |
|----------|--------|
| `ANTHROPIC_API_KEY` | Add manually under Project → Settings → Environment Variables |
| `KV_REST_API_URL` | Auto-injected when KV store is linked |
| `KV_REST_API_TOKEN` | Auto-injected when KV store is linked |
| `BLOB_READ_WRITE_TOKEN` | Auto-injected when Blob store is linked |

Do **not** add `NEXT_PUBLIC_API_URL` or `CORS_ORIGINS` to the Vercel dashboard.

---

## Running Tests

```bash
npm test
```
