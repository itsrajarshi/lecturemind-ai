# LectureMind AI — HTTP API Reference

> Describes the **current** API surface (post-hardening). Behavior was verified
> against `backend/app.py`, `backend/utils/security.py`, and the pytest suite.
> Companion docs: `ARCHITECTURE.md` (system overview), `SECURITY_AUDIT.md`
> (threat model), `AI_PIPELINE.md` (what happens inside each AI-backed endpoint).

## 1. Overview

LectureMind AI exposes a small JSON API under the `/api` prefix. In
production Flask serves both the API and the compiled React SPA from one
origin; in development the Vite dev server proxies `/api` to Flask.

| Property | Value |
|---|---|
| Base URL (production) | `https://lecturemind-ai.onrender.com/api` |
| Base URL (local dev) | `http://localhost:5000/api` (Vite proxy `/api` → `:5000`) |
| Protocol | HTTPS in production, HTTP locally |
| Bodies in | `application/json` (generate/download), `multipart/form-data` (transcribe) |
| Bodies out | `application/json`; `/api/download/notes` returns a binary file |
| Authentication | None — session-id bearer tokens only (§3) |

**All endpoints:**

| Method | Path | Description | Rate limit (per IP / hr) |
|---|---|---|---|
| GET | `/api/health` | Liveness probe | none |
| POST | `/api/transcribe` | Upload audio; returns session id + transcript | 5 |
| POST | `/api/generate/notes` | Markdown study notes from the transcript | 20 |
| POST | `/api/generate/quiz` | 10-question MCQ quiz | 20 |
| POST | `/api/generate/flashcards` | Flashcard deck (5–15 cards) | 20 |
| POST | `/api/download/notes` | Export notes as TXT or PDF | none |

Any other `/api/*` path returns `404 {"error": "Not found"}` (unknown GET
paths included — they are never served the SPA shell). Method mismatches
return `405 {"error": "Method not allowed"}`. Uploads above 50 MB return
`413 {"error": "File too large. Max 50MB."}`.

## 2. Conventions

### 2.1 Content types

- Send `Content-Type: application/json` for the generate/download endpoints
  and parse `application/json` responses.
- Send `multipart/form-data` with a field named **`audio`** for transcribe.
- Errors are always `application/json`, never HTML.

### 2.2 Error envelope

Every error response has exactly one shape:
`{ "error": "<human-readable, safe message>" }`. Messages never contain
exception internals, stack traces, or Groq payloads (see `SECURITY_AUDIT.md`
§3). Status codes:

| Code | Meaning | Typical message |
|---|---|---|
| 400 | Malformed request / invalid file | `"No audio file provided"`, `"Invalid file. Allowed: MP3, WAV, M4A"`, `"Transcript required"`, `"Invalid format. Use 'txt' or 'pdf'."` |
| 404 | Unknown `/api/*` route | `"Not found"` |
| 405 | Wrong HTTP method | `"Method not allowed"` |
| 413 | Body exceeds 50 MB | `"File too large. Max 50MB."` |
| 422 | No speech detected in audio | `"No speech detected in the audio. Please try a clearer recording."` |
| 429 | Rate limit exceeded | `"Too many requests. Please wait a moment and try again."` |
| 500 | Unexpected server error | `"Something went wrong. Please try again."` |
| 502 | AI service unreachable / generation failed | `"Could not reach the AI service. Please try again."` or a safe `GenerationError` message |
| 503 | Upstream Groq rate-limited | `"The AI service is busy. Please wait a moment and try again."` |
| 504 | Upstream timed out | `"The AI service timed out. Please try again."` |

The generate endpoints return **502** with the safe `GenerationError`
message for expected failures ("Quiz generation produced invalid data.
Please try again.", "The AI service is unavailable. Please try again
later.").

### 2.3 Rate limits

- Sliding-window, keyed per IP: `transcribe:<ip>` and `generate:<ip>`.
- Defaults: transcribe **5/hour**, generate **20/hour** (window 3600 s).
  The three generate endpoints share one budget.
- `RATE_LIMIT_TRANSCRIBE=0` / `RATE_LIMIT_GENERATE=0` disables enforcement.
- Limits are **per-process** (reset on redeploy); with the single gunicorn
  worker this is equivalent to per-instance. See `TECH_DEBT.md` (D5).

### 2.4 Headers

- CORS applies to `/api/*` only, with origins from `CORS_ORIGINS`
  (comma-separated; `*` is the dev default — set a concrete list in prod).
- Every `/api/*` response carries `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, and
  `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`.
- Every request is logged to stdout with method, path, status, duration,
  and client IP (see `ARCHITECTURE.md` §5).

## 3. Authentication model (demo-appropriate)

- **No accounts.** The server generates a session id (`uuid.uuid4()`) during
  `/api/transcribe` and returns it; that id is the only credential.
- Pass it on subsequent calls via the **`X-Session-Id` header** (preferred)
  or the **`session_id` body field**. The header wins if both are present.
- Sessions live in memory for up to **6 hours** (sliding TTL). If a session
  is missing or expired, generate endpoints fall back to the `transcript`
  body field (the frontend always sends it, so this is transparent).
- The id is unguessable but **not authenticated**: anyone holding a session
  id can regenerate material from its transcript. Acceptable for a demo;
  auth is on the roadmap (`ROADMAP.md` P3).

## 4. Endpoints

### 4.1 GET /api/health

Liveness probe. No body, no rate limit.

```bash
curl https://lecturemind-ai.onrender.com/api/health
```

`200 OK`:

```json
{ "status": "ok", "service": "LectureMind AI" }
```

### 4.2 POST /api/transcribe

Upload a lecture audio file; returns a session id plus the transcript.

Request — `multipart/form-data`, field `audio` (file, required; extension in
{mp3, wav, m4a}; magic-byte signature check; ≤ 50 MB):

```bash
curl -X POST https://lecturemind-ai.onrender.com/api/transcribe \
  -F "audio=@lecture.mp3"
```

`200 OK`:

```json
{
  "session_id": "3f2c9f4a-....-uuid",
  "transcript": "Welcome to today's lecture on ...",
  "language": "en",
  "segments": [
    { "start": 0.0, "end": 12.5, "text": "Welcome to today's lecture on ..." }
  ]
}
```

Errors: 400 (missing file / bad extension / magic-byte failure — rejected
files are deleted immediately), 413 (too large), 422 (empty transcript),
429, 500/502/503/504 (upstream Whisper failure). On upstream failure the
uploaded file is also deleted.

### 4.3 POST /api/generate/notes

Generate structured markdown study notes. Transcript resolution: session
lookup (header or body `session_id`) first, else the body `transcript`. At
least one must yield text, else `400 {"error": "Transcript required"}`.

```bash
curl -X POST https://lecturemind-ai.onrender.com/api/generate/notes \
  -H "Content-Type: application/json" \
  -H "X-Session-Id: 3f2c9f4a-....-uuid" \
  -d '{}'
```

`200 OK`:

```json
{
  "notes": "## Key Takeaways\n\n- ...",
  "format": "markdown"
}
```

Errors: 400, 429, 502 (`GenerationError` safe message), 500. The transcript
is truncated server-side to 40,000 chars at a sentence boundary before being
sent to the model (`AI_PIPELINE.md` stage 6).

### 4.4 POST /api/generate/quiz

Generate exactly 10 multiple-choice questions. Same session/transcript
resolution and the same rate-limit bucket as notes. Response is the
validated, normalized quiz:

```json
{
  "quiz_title": "Practice Quiz",
  "questions": [
    {
      "id": 1,
      "question": "What is ...?",
      "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
      "correct_answer": "A",
      "difficulty": "medium",
      "explanation": "One sentence explaining why A is correct."
    }
  ]
}
```

Guarantees: `questions.length === 10`; ids 1–10; exactly 4 non-empty
options keyed A–D; `correct_answer` ∈ {A, B, C, D}; `difficulty` ∈
{easy, medium, hard}; no duplicate questions; `explanation` may be empty.
One regeneration retry happens server-side if the model output fails
validation (`AI_PIPELINE.md` stage 7).

### 4.5 POST /api/generate/flashcards

Generate a flashcard deck:

```json
{
  "deck_title": "Revision Deck",
  "flashcards": [
    { "id": 1, "question": "...", "answer": "..." }
  ]
}
```

Guarantees: 5–15 cards, sequential ids, no duplicate questions, every card
has non-empty question and answer. Same 502 semantics as the other
generate endpoints.

### 4.6 POST /api/download/notes

Export notes as a file download (no rate limit).

Request — JSON:

| Field | Type | Default | Constraints |
|---|---|---|---|
| `notes` | string | — | required, non-empty, ≤ 1,000,000 chars (else 400/413) |
| `format` | string | `txt` | `txt` or `pdf` (else 400) |
| `title` | string | `Lecture Notes` | capped at 120 chars |

```bash
curl -X POST https://lecturemind-ai.onrender.com/api/download/notes \
  -H "Content-Type: application/json" \
  -d '{"notes":"# Notes","format":"pdf"}' \
  -o notes.pdf
```

Response: `200` with `Content-Disposition: attachment`, filename
`lecture_notes.pdf` or `lecture_notes.txt`. PDF rendering uses bundled
DejaVu Sans + Noto Sans Devanagari fonts, so Latin and Devanagari (Hindi)
text export without the encoding crashes the older `AUDIT_REPORT.md`
described. Errors: 400/413 (`AppError`), 500 (sanitized).

## 5. Frontend / backend contract

The React client (`frontend/src/api/client.js`) relies on these guarantees;
the backend honors them:

| The client assumes | The server guarantees |
|---|---|
| `POST /api/transcribe` with FormData field `audio` returns JSON with `session_id`, `transcript`, `language`, `segments` | Exactly that shape; valid JSON, never HTML |
| Subsequent calls may send `X-Session-Id` and/or body `session_id` + `transcript` | Session resolution prefers the header; body transcript is the fallback |
| Non-2xx responses carry `{"error": ...}` | True for every error path (400/404/405/413/422/429/500/502/503/504) |
| Download endpoints return a Blob (`application/pdf` or `text/plain`) | True; served as an attachment with fixed filenames |
| All `/api` paths are same-origin in production | True (single Flask origin); CORS exists only for cross-origin dev clients |
| Generation is expensive (up to ~90 s server-side) | Timeouts/retries/backoff handled server-side; the client shows per-action loading (`UI_UX_AUDIT.md`) |

## 6. Non-API routes

Non-API GET routes serve the built SPA (`backend/static/index.html`,
client-side-routing friendly). If the frontend has not been built, the root
returns a small JSON status payload instead. Unknown `/api/*` paths never
receive the SPA shell — they get JSON 404.