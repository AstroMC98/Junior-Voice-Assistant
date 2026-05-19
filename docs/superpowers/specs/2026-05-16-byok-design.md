# BYOK (Bring Your Own Key) Design

**Date:** 2026-05-16
**Status:** Approved

## Summary

Remove the server-side `ANTHROPIC_API_KEY` entirely. Users supply their own Anthropic API key via a modal on the home page. The key is held in React memory (cleared on refresh), sent as an `X-Api-Key` HTTP header on every request, and used per-request on the backend. The key is never stored or logged anywhere on the server.

## Goals

- Zero cost exposure for the app owner — no server key to abuse
- Client trust — key is never stored or logged server-side, only used for the duration of a Claude call
- Minimal friction — user enters key once per session via a modal; all existing flows work unchanged

## Non-Goals

- Key persistence across browser sessions (intentionally session-only)
- Multi-user auth or accounts
- Server-side session management

---

## Data Flow

```
User enters key in modal → stored in React context (memory only, cleared on refresh)
         ↓
Every fetch to /api/* includes header: X-Api-Key: sk-ant-...
         ↓
Backend reads X-Api-Key header → creates Anthropic(api_key=...) per-request
Backend returns HTTP 401 if header is missing or blank
         ↓
Frontend catches 401 → shows "API key required" message and reopens modal
```

---

## Frontend

### `ApiKeyContext` (new)
- React context providing `{ apiKey: string; setApiKey: (k: string) => void }`
- State lives in memory — no localStorage, no sessionStorage
- Wraps the app in `app/layout.tsx`

### `ApiKeyModal` (new component)
- Triggered by the "API Key" button in `AppShell`
- Password-type input for the key
- Note: *"Sent over HTTPS only. Never stored or logged."*
- Link to `console.anthropic.com` to get a key
- "Save" button stores key into `ApiKeyContext` for the session

### `AppShell` (modified)
- Adds an "API Key" button/indicator in the header
- Shows a lock icon when a key is set; a warning indicator when not

### `apiFetch` helper (new, `lib/apiFetch.ts`)
- Plain function `apiFetch(url, apiKey, options?)` — accepts `apiKey` as a parameter (cannot use `useContext` outside React tree)
- Injects `X-Api-Key` header automatically; throws a typed `ApiKeyError` on 401
- Calling components read `apiKey` from context via `useApiKey()` and pass it in
- Replaces direct `fetch(${API_BASE}/api/...)` calls in:
  - `components/guide-creator/GuideCreator.tsx`
  - `components/session/SessionView.tsx`
  - `components/session/VoiceLoop.tsx`

---

## Backend

### `api/claude.py` (modified)
- Remove global `_client` singleton and `_get_client()`
- `process_guide(source, text, images, api_key: str)` — creates `Anthropic(api_key=api_key)` inline
- `session_turn(guide, current_step_index, transcript, photo, api_key: str)` — same pattern

### `api/index.py` (modified)
- New FastAPI dependency `require_api_key(request: Request) -> str`:
  - Reads `X-Api-Key` header
  - Raises `HTTP 401` with detail `"API key required"` if missing or blank
  - Must **never** be logged (add explicit comment)
- `create_guide` and `session_endpoint` depend on `require_api_key` and pass `api_key` to Claude functions
- `fork_guide` and `fetch_url` do **not** require the key (no Claude calls)
- Remove `ANTHROPIC_API_KEY` from `.env.local` and Vercel environment variables

### `api/models.py`
- No changes. The key never touches data models.

---

## Error Handling

| Scenario | Backend response | Frontend behaviour |
|---|---|---|
| No `X-Api-Key` header | `401 API key required` | Modal reopens with "API key required" message |
| Invalid key (Anthropic rejects it) | `500` (Anthropic throws AuthenticationError) | Existing error state: "Processing failed" |
| Key correct, Anthropic call succeeds | `200/201` | Normal flow |

---

## Security Notes

- HTTPS ensures the key is not visible to third parties in transit
- The server never persists the key (not in KV, not in logs, not in any model)
- FastAPI's default access log does not log headers; the `require_api_key` dependency includes an explicit comment to never log the value
- `fork_guide` and `fetch_url` intentionally excluded from key requirement — they make no Claude calls

---

## Files Changed

| File | Change |
|---|---|
| `app/layout.tsx` | Wrap with `ApiKeyContext` provider |
| `components/layout/AppShell.tsx` | Add API Key button/indicator |
| `components/ApiKeyModal.tsx` | New modal component |
| `lib/ApiKeyContext.tsx` | New context |
| `lib/apiFetch.ts` | New fetch wrapper |
| `components/guide-creator/GuideCreator.tsx` | Use `apiFetch` |
| `components/session/SessionView.tsx` | Use `apiFetch` |
| `components/session/VoiceLoop.tsx` | Use `apiFetch` |
| `api/claude.py` | Remove singleton; accept `api_key` param |
| `api/index.py` | Add `require_api_key` dependency; pass key to Claude functions |
| `.env.local` | Remove `ANTHROPIC_API_KEY` |
