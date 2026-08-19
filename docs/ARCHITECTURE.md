# LectureMind AI — System Architecture

> Applies to the **current** codebase state (post-hardening refactor, commit
> `57e74f5`). This document supersedes the older `PROJECT_DOCUMENTATION.md`,
> which still describes pre-refactor internals (e.g. a locally-hosted Whisper
> model and the deprecated Groq chat model) and should not be treated as
> authoritative for this state.

## 1. Overview

LectureMind AI is a **single-page application** that converts lecture audio into
a transcript, structured study notes, a multiple-choice quiz, and flashcards.
All AI work is performed **in the cloud by Groq**:

- **Transcription** uses Groq-hosted Whisper (`whisper-large-v3`) — there is no
  local Whisper model anywhere in the codebase.
- **Notes / quiz / flashcards generation** uses a Groq chat completion model,
  `openai/gpt-oss-20b` by default (`GROQ_MODEL`, env-configurable), with a
  fallback to `openai/gpt-oss-120b`.

The stack is deliberately small:

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + Tailwind CSS, single page |
| Backend | Flask 3 + the official `groq` Python SDK |
| AI | Groq-hosted `whisper-large-v3` + `openai/gpt-oss-20b` chat model |
| State | In-memory Python dict session store (no database) |
| PDF export | `fpdf2` (server-side, no client PDF dependency) |
| Deployment | Render free tier, built via `render-build.sh`, run by gunicorn (1 worker) |

In production the frontend is compiled with Vite and copied into
`backend/static/`; Flask serves both the static SPA and the JSON API from a
single origin.

## 2. Components

```
┌─────────────────────────────────────────────────────────────────┐
│                          Browser (SPA)                         │
│   Home.jsx state machine  ──  api/client.js (fetch)            │
│   AudioUploader · TranscriptPanel · NotesPanel                  │
│   QuizPanel · FlashcardsPanel · Header · Footer · Spinner       │
└───────────────────────────────┬─────────────────────────────────┘
                                │ JSON / multipart over HTTP
┌───────────────────────────────▼─────────────────────────────────┐
│                          Flask app (app.py)                    │
│  /api/health   /api/transcribe   /api/generate/{notes,quiz,     │
│  flashcards}   /api/download/notes                              │
│  rate_limit decorator · sanitized errors · CORS/CSP headers     │
└───────┬───────────────────────┬──────────────────────┬──────────┘
        │                       │                      │
┌───────▼────────┐   ┌──────────▼─────────┐  ┌─────────▼──────────┐
│ services/      │   │ services/          │  │ services/          │
│ whisper_service│   │ groq_service       │  │ export_service     │
│  (Groq Whisper)│   │  (Groq chat +      │  │  TXT/PDF export    │
│                │   │   validation)      │  │                    │
└───────┬────────┘   └──────────┬─────────┘  └────────────────────┘
        │                       │
        │                       └──────── utils/parsing.py (schemas)
┌───────▼─────────────────────────────────────────────────────────┐
│ services/session_store.py  (in-memory TTL store + sweep)        │
│   transcripts · segments · notes · quiz · flashcards · filepath │
└─────────────────────────────────────────────────────────────────┘
```

### Backend entry points and helpers

- `backend/app.py` — Flask app factory, routes, error handlers, SPA serving.
- `backend/config.py` — all env-driven configuration and a production
  `validate_config()` that fails fast if `GROQ_API_KEY` is missing.
- `backend/utils/` — `file_validator.py` (extension + magic-byte checks),
  `security.py` (rate limiting + sanitized errors), `parsing.py` (JSON
  extraction + quiz/flashcard schema validation), `prompts.py` (templates +
  transcript markers), `logging.py` (structured stdout logging).

### Frontend

- `frontend/src/pages/Home.jsx` — the only page; owns all workflow state
  (`sessionId`, `transcript`, `notes`, `quiz`, `flashcards`, per-action
  `loading`, `error`).
- `frontend/src/api/client.js` — thin `fetch` wrapper; serializes requests,
  surfaces the JSON `error` field, and triggers TXT/PDF downloads.
- `frontend/src/components/` — presentational panels: `AudioUploader`,
  `TranscriptPanel`, `NotesPanel` (react-markdown + remark-gfm),
  `QuizPanel` (interactive MCQ with scoring), `FlashcardsPanel` (flip deck),
  `Header`, `Footer`, `LoadingSpinner`.

## 3. End-to-end data flow

The canonical workflow is: **upload → validate → transcribe → session →
generate → export**.

1. **Upload** — `AudioUploader` sends the file as `multipart/form-data` with
   field `audio` to `POST /api/transcribe`.
2. **Validate** — `app.transcribe` checks that the field exists, the extension
   is in `ALLOWED_EXTENSIONS = {mp3, wav, m4a}`, the request is under
   `MAX_CONTENT_LENGTH` (50 MB default, enforced by Werkzeug, 413 on exceed),
   and — after saving — that the **magic bytes** match an MP3/WAV/M4A container
   (`utils/file_validator.has_valid_signature`). Invalid files are deleted
   immediately.
3. **Transcribe** — `services/whisper_service.transcribe_audio` streams the
   saved file to Groq `audio.transcriptions.create(model="whisper-large-v3",
   response_format="verbose_json")`. The text, detected language, and segment
   timestamps are extracted defensively.
4. **Session** — a new UUID session is created in the in-memory store with the
   transcript, segments, language, and the on-disk upload path.
5. **Generate** — the UI calls `POST /api/generate/{notes,quiz,flashcards}`.
   The backend resolves the transcript from the `X-Session-Id` header
   (preferred) or the `session_id`/`transcript` body fields, truncates it to
   `TRANSCRIPT_MAX_CHARS` (40k) at a sentence boundary, and calls
   `services/groq_service` with a prompt wrapped in transcript markers.
6. **Validate output** — quiz/flashcard responses are parsed
   (`utils/parsing.extract_json_object`) and validated against schemas
   (`validate_quiz`, `validate_flashcards`) with one regeneration retry.
7. **Export** — `POST /api/download/notes` turns the generated markdown notes
   into TXT or PDF (`services/export_service`) and streams it back as an
   attachment.

## 4. Directory layout

```
lecturemind-ai/
├── render.yaml                # Render Blueprint (web service, 1 worker)
├── README.md                  # quick start + deployment guide
├── PROJECT_DOCUMENTATION.md   # OLD doc — pre-refactor, partly outdated
├── docs/                      # this documentation set
├── backend/
│   ├── app.py                 # Flask app + routes
│   ├── config.py              # env configuration + validation
│   ├── render-build.sh        # builds frontend and copies into static/
│   ├── requirements.txt       # pinned runtime deps (flask, groq, gunicorn...)
│   ├── .env.example           # placeholder env template (no real secrets)
│   ├── uploads/               # runtime dir: uploaded audio (gitignored)
│   ├── static/                # build output copied here (gitignored)
│   ├── services/
│   │   ├── groq_service.py    # chat generation + retries/fallback/validation
│   │   ├── whisper_service.py # Groq Whisper transcription
│   │   ├── export_service.py  # TXT/PDF conversion
│   │   └── session_store.py   # in-memory TTL session store
│   ├── utils/
│   │   ├── file_validator.py  # extension + magic-byte checks
│   │   ├── security.py        # rate limiting, sanitized errors
│   │   ├── parsing.py         # JSON extraction + schema validation
│   │   ├── prompts.py         # note/quiz/flashcard templates + markers
│   │   └── logging.py         # stdout structured logging
│   └── tests/                 # pytest suite (Flask test client)
└── frontend/
    ├── index.html             # SPA shell (favicon, fonts, meta)
    ├── package.json           # React 18, Vite 5, Tailwind, vitest/playwright
    ├── vite.config.js         # dev server proxy /api → :5000
    ├── public/favicon.svg
    └── src/
        ├── main.jsx, App.jsx, index.css
        ├── api/client.js
        ├── pages/Home.jsx
        └── components/*.jsx
```

## 5. Deployment topology

- **Render Blueprint** (`render.yaml`): Python web service, free plan,
  `rootDir: backend`, `buildCommand: bash render-build.sh`,
  `startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`.
- `render-build.sh` installs Python deps, runs `npm ci && npm run build` in
  `../frontend`, removes `backend/static`, and copies `dist/*` into it. The
  build output is therefore always fresh and never committed to git.
- Flask serves the SPA (`serve_frontend`): known static files are served
  directly; everything else on non-API routes falls back to `index.html`
  (client-side routing-friendly). If the frontend has not been built, the root
  returns a small JSON status payload instead.
- API routes get `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  and a restrictive `Content-Security-Policy` header via the `after_request`
  hook.

## 6. Why in-memory sessions and a single worker?

`services/session_store.py` keeps sessions in a process-local dict guarded by a
lock. This is a deliberate trade-off for a demo on the free Render tier:

- **Consistency requires one worker.** The store is not shared across
  processes. With `--workers 1` every request in a deployment hits the same
  process, so the store is always consistent. Adding workers would split the
  store and break the `X-Session-Id` workflow.
- **Ephemeral disk and memory are bounded.** Sessions carry a TTL
  (`SESSION_TTL_SECONDS`, default 6 h) and a periodic sweep
  (`maybe_sweep`, at most every `SESSION_CLEANUP_INTERVAL` = 300 s) deletes
  expired sessions **and their uploaded audio file** from disk. Rejected
  uploads and empty transcripts are cleaned up inline too.
- **No database dependency** keeps the free-tier footprint tiny and the deploy
  trivial; the trade-off is that state is lost on restart/redeploy and
  sessions cannot be shared across instances (see
  `docs/PRODUCTION_READINESS.md` and `docs/TECH_DEBT.md`).

The store's locking also makes it safe against the small amount of concurrent
traffic a single worker can handle.