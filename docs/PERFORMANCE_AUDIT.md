# LectureMind AI — Performance Audit

> Performance characteristics of the **current** codebase. The headline fact:
> LectureMind runs **no local AI models**. Both transcription and generation
> are remote calls to the Groq cloud, so the server is I/O-bound and small.

## 1. Frontend bundle

- Vite production build: roughly **274 KB of JavaScript** (≈ **86 KB gzipped**)
  for the single page, including `react`, `react-dom`, `react-markdown`, and
  `remark-gfm`.
- Styling is Tailwind (utility classes compiled at build time; only used
  classes ship). Google Fonts (Inter) loads from `fonts.googleapis.com` with
  preconnect hints in `index.html`.
- The app is a single route with lazy-free imports, so initial JS is the
  whole app — acceptable for a one-page tool and fast on the free tier.
- Deliberately **not** done: route-level code splitting (only one route),
  further dedupe of `react-markdown` (small win, not worth it yet).

## 2. No local model: the I/O-bound design

- Whisper runs on Groq's infrastructure (`whisper-large-v3`); the server only
  streams the uploaded file to the Groq API and parses the JSON response.
  There is no local `openai-whisper`, no model weights on disk, no GPU/CPU
  burn on the server, and no FFmpeg dependency.
- Notes/quiz/flashcards are Groq chat completions (`openai/gpt-oss-20b`),
  also remote.
- Consequence: the app scales with **network latency and Groq quotas**, not
  with server CPU. Memory and disk on the app server stay tiny.

## 3. Blocking vs. I/O-bound work

Flask runs a **synchronous** WSGI worker. Each request occupies its worker for
its whole duration:

| Request | Blocking time on the worker | Bound |
|---------|------------------------------|-------|
| `POST /api/transcribe` | Upload write + Groq Whisper call | Whisper timeout 120 s |
| `POST /api/generate/*` | Prompt build + Groq chat call | Groq timeout 90 s |
| `POST /api/download/notes` | PDF/TXT render | ms–seconds |
| `GET /api/health` | ~0 | — |

Because there is only **one worker**, while a transcription or generation is
in flight, no other request is being processed (in this deployment). Groq
timeouts (`WHISPER_TIMEOUT=120`, `GROQ_TIMEOUT=90`) bound the worst-case
stall; the gunicorn timeout must be larger than the longest blocking call.

## 4. Single-worker trade-offs and gunicorn tuning

`render.yaml` starts: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 300
--workers 1 --threads 4`.

- **Why 1 worker**: the in-memory session store is process-local; multiple
  workers would fragment sessions and break the `X-Session-Id` workflow (see
  `docs/ARCHITECTURE.md` §6).
- **Why `--threads 4`**: gunicorn runs a threaded (gthread) worker, so while
  one request is awaiting Groq (I/O-bound), other requests (e.g. health
  checks) are still served. Python's GIL keeps CPU-bound work serialized, but
  these endpoints are almost entirely network-bound.
- **Why `--timeout 300`**: the default gunicorn timeout (30 s) would kill a
  long Whisper call. 300 s > `WHISPER_TIMEOUT` (120 s Groq-side) and >
  `GROQ_TIMEOUT` (90 s), so gunicorn only aborts when Groq itself has given
  up. This is tuned deliberately and must be re-checked if timeouts change.
- **Concurrency impact**: effective concurrency is bounded by the 4 threads;
  heavy generation requests still queue. Acceptable for a demo; for real
  concurrency the app needs async jobs (see `docs/TECH_DEBT.md` and
  `docs/ROADMAP.md`).

## 5. Memory bounds (sessions)

`services/session_store.py` keeps transcripts, segments, and generated
material in memory:

- **TTL**: `SESSION_TTL_SECONDS` = 21,600 s (6 h) default. A session expires
  6 h after its last access.
- **Sweep**: `maybe_sweep()` runs at most every `SESSION_CLEANUP_INTERVAL`
  (300 s), invoked from the `before_request` hook, so no background thread is
  needed and the cost is amortized over requests.
- **Per-session memory** is dominated by the transcript (up to 40k chars by
  default) plus segments; generated notes/quiz/flashcards add a bounded
  amount. The `last_accessed` touch on every `get` keeps active sessions from
  being evicted.
- Worst-case memory = (concurrent active sessions) × (transcript + artifacts);
  the TTL and rate limits keep this small for a demo.

## 6. Uploads disk lifecycle

- Uploads land in `UPLOAD_FOLDER` (`backend/uploads/`, gitignored) capped at
  50 MB each by `MAX_CONTENT_LENGTH`.
- Rejected files (bad extension/magic bytes) are deleted inline.
- Empty-transcript files are deleted inline.
- Successful uploads stay on disk until their session expires, then the sweep
  `unlink`s them (`missing_ok=True`, OSError-guarded).
- Disk footprint is therefore bounded by active sessions, matching the
  ephemeral-disk reality of the free Render tier.

## 7. What was optimized

- **Prompt budget control**: transcripts truncated to 40k chars at a sentence
  boundary (`_truncate`) so long lectures cannot blow the token budget or
  silently exceed Groq limits; a note is appended when truncated.
- **Retries with backoff** on transient Groq failures (429/5xx/timeouts) and
  a **model fallback list** so a single model outage does not break
  generation (`groq_service._chat`).
- **Single regeneration retry** on schema-invalid quiz/flashcards instead of
  surfacing raw parse errors.
- **Lazy/amortized sweep** via `before_request` (no timer thread, no
  per-request full scan).
- **Debounced rate-limit cleanup** (hit queues pruned every 600 s) so the
  per-IP hit tables do not grow unboundedly.

## 8. What is intentionally NOT optimized

- **No async jobs / queues** — requests are synchronous by design for
  simplicity. Long AI calls block the single worker; that is a known demo
  trade-off, tracked in `docs/TECH_DEBT.md`.
- **No streaming responses** — the UI waits for the full JSON; no
  token-by-token UX.
- **No caching** — every generation re-invokes the model; caching identical
  transcripts is a roadmap item, not implemented.
- **No horizontal scaling** — explicitly incompatible with the in-memory
  store until persistence is added.
- **No CDN/caching headers on static assets** — served by Flask; fine for the
  bundle size, not optimized for repeat visits.

## 9. Metrics

There are **no runtime metrics or tracing** — only structured stdout logging
(request duration, per-request status, generation counts, Groq warnings).
Observing latency requires reading logs (see `docs/PRODUCTION_READINESS.md`).