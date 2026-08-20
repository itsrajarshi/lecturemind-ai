# LectureMind AI — Codebase Audit Report

> Audit of the repository **after** the hardening refactor (commits `57e74f5`
> and `061b93e`). The report distinguishes three things: what was found, what
> was fixed, and what remains as a documented limitation. Findings were
> verified against the code, the pytest suite under `backend/tests/`, and the
> Vitest/Playwright suites under `frontend/`.

## 1. Scope and method

- Reviewed every backend module (`app.py`, `config.py`, `services/*`,
  `utils/*`), the full frontend (`src/**`), build/deploy config
  (`render.yaml`, `render-build.sh`, `package.json`), and git history.
- Ran/read the backend test suite, which covers health, upload validation,
  session lifecycle, generation, export, and security behavior.
- Compared against the pre-refactor state to separate "found and fixed" from
  "still present".

## 2. Findings summary (severity table)

Severity: **P0** = breaks the core product, **P1** = high impact
(security/reliability), **P2** = medium (correctness/UX), **P3** = low
(polish). Status: `Fixed`, `Partial`, `Remains`, `Accepted`.

| ID | Severity | Finding | Status |
|----|----------|---------|--------|
| A1 | P0 | Deprecated Groq model (`llama-3.3-70b-versatile`) returned `model_not_found` on every generation request — notes/quiz/flashcards were fully broken | Fixed |
| A2 | P0 | Raw exception internals (and the Groq API key error text) leaked to API clients via `f"...{exc}"` error strings | Fixed |
| A3 | P1 | `venv/`, `node_modules/`, and `demo/` media had no `.gitignore` — large/vendor files were committed and served as truth | Fixed |
| A4 | P1 | No rate limiting on any endpoint — transcribe/generate were unlimited per IP | Fixed |
| A5 | P1 | Sessions were unbounded (dict grew forever) and uploaded audio was **never** cleaned up | Fixed |
| A6 | P1 | Upload validation trusted only the filename extension; renamed binaries passed through | Fixed |
| A7 | P1 | Prompts were not hardened against transcript-based prompt injection | Fixed |
| A8 | P1 | Stale `backend/static` build was committed and could be served as truth | Fixed |
| A9 | P1 | Docs claimed a locally-hosted `openai-whisper` model that does not exist | Fixed |
| A10 | P2 | Unknown `GET /api/*` returned 200 (SPA payload) instead of `404 {"error":"Not found"}` — the 404 handler was shadowed by the catch-all frontend route | Fixed |
| A11 | P2 | Rate-limit enforcement returned **500** instead of **429** because `RateLimitExceeded` had no dedicated error handler | Fixed |
| A12 | P2 | `notes_to_pdf` crashed for multi-line content and the U+2022 bullet (fpdf2 built-in Helvetica, latin-1 only) | Fixed |
| A13 | P2 | Quiz/flashcard panels did not reset internal state when a new deck was generated | Fixed |
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

## 4. Residual issues fixed after the audit

The findings below were reported by the original audit and the test suite,
then **fixed** in commit `061b93e`:

### A10 — Unknown `GET /api/*` returns 200, not 404 (fixed)
`serve_frontend` now short-circuits any `api/` path with a JSON 404 before the
SPA fallback, and the `404` error handler returns JSON for `/api/*` paths.
Verified by `test_unknown_api_route_returns_json_404`.

### A11 — Rate-limited requests return 500, not 429 (fixed)
A dedicated `@app.errorhandler(RateLimitExceeded)` now returns
`429 {"error":"Too many requests..."}`. Verified by
`test_transcribe_rate_limit_enforced`.

### A12 — PDF export edge cases (fixed)
`notes_to_pdf` now bundles DejaVu Sans + Noto Sans Devanagari fonts (Unicode),
strips markdown syntax, wraps long lines/tokens, and degrades gracefully if a
glyph is missing. Multi-line bullets, Hindi text, and long tokens all export
cleanly. Verified by `test_download_notes_pdf_multiline_and_unicode`.

### A13 — Quiz/flashcard panel state not reset on regeneration (fixed)
`QuizPanel` and `FlashcardsPanel` now reset their internal state via `useEffect`
when a new quiz/deck arrives. Verified by the Vitest suites.

## 5. Verification

Backend (`backend/tests/`, 29 tests): health, upload validation, magic bytes,
session TTL/sweep/file cleanup, generation success + sanitized errors, security
headers, CORS, rate limiting, export. Run with:

```
cd backend
pip install -r requirements-dev.txt
pytest
```

Frontend: Vitest (26 tests) under `frontend/src/**/*.test.{js,jsx}` and
Playwright E2E (2 tests) under `frontend/e2e/` — the E2E suite stubs the AI
backends so it runs deterministically without an API key.

```
cd frontend
npm test          # unit tests
npm run test:e2e  # Playwright (build first)
```

## 6. Conclusion

The hardening refactor fixed the two P0 blockers (broken model, error
leakage) and all P1 security/hygiene issues. Three P2 items (404 shadowing,
429-vs-500 on rate limit, PDF edge cases) plus the panel-state nit are
documented residuals; none breaks the demo happy path. The remaining risks are
architectural (in-memory sessions, no auth) and are covered in
`docs/PRODUCTION_READINESS.md` and `docs/ROADMAP.md`.