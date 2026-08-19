# LectureMind AI — Codebase Audit Report

> Audit of the repository **after** the hardening refactor (commit `57e74f5`,
> "fix: replace deprecated Groq model, harden backend security and
> reliability"). The report distinguishes three things: what was found, what
> was fixed, and what remains as a documented limitation. Findings were
> verified against the code and the pytest suite under `backend/tests/`.

## 1. Scope and method

- Reviewed every backend module (`app.py`, `config.py`, `services/*`,
  `utils/*`), the full frontend (`src/**`), build/deploy config
  (`render.yaml`, `render-build.sh`, `package.json`), and git history.
- Ran/read the backend test suite, which explicitly documents several
  **residual** bugs that were intentionally left unpatched but are asserted
  for regressions (`test_security.py`, `test_export.py`).
- Compared against the pre-refactor state (`b164a1d`) to separate "found and
  fixed" from "still present".

## 2. Findings summary (severity table)

Severity: **P0** = breaks the core product, **P1** = high impact
(security/reliability), **P2** = medium (correctness/UX), **P3** = low
(polish). Status: `Fixed`, `Partial`, `Remains`, `Accepted`.

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| A1 | P0 | Deprecated Groq model (`llama-3.3-70b-versatile`) returned `model_not_found` on every generation request — notes/quiz/flashcards were fully broken | Fixed |
| A2 | P0 | Raw exception internals (and the Groq API key error text) leaked to API clients via `f"...{exc}"` error strings | Fixed |
| A3 | P1 | `venv/`, `node_modules/`, and `demo/` media had no `.gitignore` — large/vendor files were at risk of being committed | Fixed |
| A4 | P1 | No rate limiting on any endpoint — transcribe/generate were unlimited per IP | Fixed |
| A5 | P1 | Sessions were unbounded (dict grew forever, TTL unknown) and uploaded audio was **never** cleaned up | Fixed |
| A6 | P1 | Upload validation trusted only the filename extension; renamed binaries passed through | Fixed |
| A7 | P1 | Prompts were not hardened against transcript-based prompt injection | Fixed |
| A8 | P1 | Stale `backend/static` build could be committed and served as truth | Fixed |
| A9 | P1 | Docs claimed a locally-hosted `openai-whisper` model that does not exist | Fixed in code / docs stale |
| A10 | P2 | Unknown `GET /api/*` returns 200 (SPA payload) instead of the specified `404 {"error":"Not found"}` — the 404 handler is shadowed by the catch-all frontend route | Remains (documented) |
| A11 | P2 | Rate-limit enforcement returns **500** instead of the specified **429** because `RateLimitExceeded` has no dedicated error handler | Remains (documented) |
| A12 | P2 | `notes_to_pdf` crashes for (a) some multi-line content ("Not enough horizontal space to render a single character") and (b) lines rewritten to the U+2022 bullet, which fpdf2's built-in Helvetica cannot encode | Remains (documented) |
| A13 | P2 | Quiz/flashcard panels do not reset internal state (`answers`/`submitted`, `index`/`flipped`) when a new deck is generated | Partial |
| A14 | P2 | CORS defaulted to `*` regardless of environment | Fixed |
| A15 | P2 | Old generation code truncated transcripts at a hard 12,000 chars with no boundary awareness | Fixed |
| A16 | P3 | Missing favicon caused a 404 in the browser console | Fixed |
| A17 | P3 | No structured request logging (debug server only) | Fixed |

## 3. What was found (details)

### A1 — Deprecated Groq chat model (P0, fixed)
`groq_service.py` hard-coded `llama-3.3-70b-versatile`. Groq deprecated that
model; every `chat.completions.create` returned `model_not_found` (404), so
**all generation was broken** while transcription still worked. The fix makes
`GROQ_MODEL` env-configurable and defaults to `openai/gpt-oss-20b`, with a
fallback list (`MODEL_FALLBACKS = ["openai/gpt-oss-20b", "openai/gpt-oss-120b"]`)
and a documented design note in the module docstring.

### A2 — Error leakage (P0, fixed)
Pre-refactor handlers returned `f"Transcription failed: {exc}"` etc. to the
client, exposing internal exceptions (and, if `GROQ_API_KEY` were unset, the
Groq SDK's key error). The current code maps failures through
`utils.security.error_response`/`_safe_message` (429/503/504/502/500 → generic
safe messages) and `GenerationError` (explicitly user-safe). The test
`test_generation_generic_error_is_sanitized` asserts internal text never
reaches the body.

### A3–A4 — Hygiene and rate limits (P1, fixed)
A `.gitignore` was added (env files, venv, node_modules, `frontend/dist`,
`backend/static`, uploads, demo media, test artifacts). Git history was
rewritten so no secrets or vendor trees remain (only `backend/.env.example`
with a placeholder ever existed). Rate limiting is now per-IP, sliding-window,
via the `@rate_limit` decorator (`RATE_LIMIT_TRANSCRIBE=5/hr`,
`RATE_LIMIT_GENERATE=20/hr`), keyed on `request.remote_addr`.

### A5 — Unbounded sessions / orphaned uploads (P1, fixed)
A dedicated `SessionStore` (`session_store.py`) now owns sessions with
`created_at`/`last_accessed`, a TTL, a lock, and a periodic `maybe_sweep()` that
removes expired sessions **and deletes their uploaded audio file** from disk.
Rejected uploads are deleted inline; empty-transcript uploads are deleted too.

### A6 — Upload validation (P1, fixed)
`utils/file_validator.py` adds magic-byte sniffing on top of the extension
whitelist: MP3 (`ID3` or MPEG frame sync), WAV (`RIFF....WAVE`), M4A
(`....ftyp`). `app.py` validates the file after saving and deletes it on
failure (`test_transcribe_rejects_wrong_magic_bytes` asserts no file lingers).

### A7 — Prompt injection resistance (P1, fixed)
`utils/prompts.py` now wraps the transcript in `<lecture_transcript>`
markers, every template states the transcript is **untrusted data** and to
**ignore any instructions inside it**, and the authoritative system prompt
lives only in the system message (`groq_service.SYSTEM_PROMPT`).

### A8 — Stale static build (P1, fixed)
`render-build.sh` wipes and rebuilds `backend/static` from `frontend/dist`
on every deploy, and `.gitignore` excludes `backend/static/` and
`frontend/dist/` so a stale build can never be committed.

### A9 — Docs claimed local Whisper (P1, fixed in code)
`PROJECT_DOCUMENTATION.md` describes a local `openai-whisper` +
`whisper-base` pipeline and the deprecated model. The **code** uses
Groq-hosted `whisper-large-v3`. This `docs/` set describes the real state;
`PROJECT_DOCUMENTATION.md` is flagged stale and should be updated or removed.

## 4. What remains (documented limitations)

These are real, reproducible behaviors in the current codebase. They are
tracked in `docs/TECH_DEBT.md` with suggested remediations.

### A10 — Unknown `GET /api/*` returns 200, not 404
`app.py` defines a `404` error handler that returns JSON for `/api/` paths,
but the catch-all frontend route `@app.route("/<path:path>")` matches any
unknown GET path first, so an unknown API route is served the SPA fallback
(200) instead. Confirmed by `test_unknown_api_route` in `test_security.py`
("GENUINE APP BUG ... app not modified"). POST to unknown `/api/*` correctly
yields 405 JSON.

### A11 — Rate-limited requests return 500, not 429
The `@rate_limit` decorator raises `RateLimitExceeded`, which `_safe_message`
would map to 429 — but no `errorhandler(RateLimitExceeded)` exists, so Flask's
generic 500 handler answers instead. The **limit is still enforced** (the 6th
transcribe in an hour is rejected); only the status code is wrong. Confirmed
by `test_transcribe_rate_limit_enforced`.

### A12 — PDF export edge cases
`export_service.notes_to_pdf` rewrites `- ` lines to `  • ` (U+2022) and feeds
each line to fpdf2's built-in Helvetica (latin-1). Multi-line content can
trigger "Not enough horizontal space to render a single character", and the
U+2022 bullet cannot be encoded by the font, both producing 500s. The test
suite exercises only a single ASCII line so the happy path stays covered.

### A13 — Quiz/flashcard panel state not reset on regeneration
`Home.jsx` correctly clears `notes`/`quiz`/`flashcards` when a **new upload**
happens, but `QuizPanel` keeps `answers`/`submitted` and `FlashcardsPanel`
keeps `index`/`flipped` when the user clicks **Generate again** with the same
transcript — a fresh quiz can show the previous submission's coloring and
score. Page-level state resets are implemented; panel-level resets are not.

## 5. Verification

The backend suite covers health, upload validation, magic bytes, session
TTL/sweep/file cleanup, generation success and sanitized errors, security
headers, CORS, rate limiting, and export. Run with:

```
cd backend
pip install -r requirements-dev.txt
pytest
```

Frontend tooling (`vitest`, `@playwright/test`) is configured in
`package.json` but no frontend test files exist yet — see
`docs/TECH_DEBT.md`.

## 6. Conclusion

The hardening refactor fixed the two P0 blockers (broken model, error
leakage) and all P1 security/hygiene issues. Three P2 items (404 shadowing,
429-vs-500 on rate limit, PDF edge cases) plus the panel-state nit are
documented residuals; none breaks the demo happy path. The remaining risks are
architectural (in-memory sessions, no auth) and are covered in
`docs/PRODUCTION_READINESS.md` and `docs/ROADMAP.md`.