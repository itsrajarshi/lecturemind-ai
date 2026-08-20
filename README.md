# LectureMind AI — Lecture Voice-to-Notes Generator

> Turn lecture audio into a transcript, structured study notes, a practice quiz, and flashcards — in minutes.

**AICTE · Edunet Foundation · IBM SkillsBuild AI Internship Project**

![stack](https://img.shields.io/badge/React-18-61dafb) ![stack](https://img.shields.io/badge/Flask-3-10b981) ![stack](https://img.shields.io/badge/Groq-Whisper%20%2B%20LLM-ff4d4d) ![tests](https://img.shields.io/badge/tests-57%20passing-brightgreen) ![license](https://img.shields.io/badge/license-MIT-blue)

## Live Demo

**https://lecturemind-ai.onrender.com**

Upload a lecture recording → get a Whisper transcript → generate structured notes, a 10-question MCQ quiz with explanations, and revision flashcards → export notes as TXT or PDF.

---

## Why it exists

Students can't listen and write notes at the same time, and raw recordings are painful to revise from. LectureMind AI closes that gap with a single upload: **speech-to-text + generative AI → study-ready material**, powered entirely by free-tier Groq APIs (hosted Whisper for transcription, `gpt-oss-20b` for generation). No GPU, no local models, no API-key juggling on the client.

## Key features

| Feature | Details |
|---------|---------|
| 🎙️ **Audio upload** | Drag-and-drop MP3 / WAV / M4A, client + server validation (extension *and* content signature), 50 MB cap |
| 🗣️ **Speech-to-text** | Groq-hosted `whisper-large-v3` with segment timestamps + detected language |
| 📝 **Structured notes** | Markdown notes with headings, bold terms, and key takeaways, grounded in the transcript |
| ❓ **Practice quiz** | Exactly 10 MCQs with 4 options, difficulty mix, explanations, instant scoring, retake |
| 🃏 **Flashcards** | Flip cards with keyboard navigation, shuffle, and progress |
| ⬇️ **Export** | Notes as TXT or PDF (Unicode-safe, incl. Devanagari) |
| 🛡️ **Production hardening** | Rate limiting, sanitized errors, session TTL + file cleanup, prompt-injection resistance, structured logging |

## Technology stack

- **Frontend:** React 18 · Vite 5 · Tailwind CSS 3 · react-markdown (GFM)
- **Backend:** Flask 3 · Flask-CORS · python-dotenv
- **AI:** Groq SDK — `whisper-large-v3` (transcription) · `openai/gpt-oss-20b` (notes/quiz/flashcards)
- **Export:** fpdf2 (bundled DejaVu Sans + Noto Sans Devanagari fonts)
- **Deploy:** Render (single web service, Python runtime, frontend built into `backend/static`)
- **Testing:** pytest (backend) · Vitest + Testing Library (frontend) · Playwright (E2E) · GitHub Actions CI

## Architecture at a glance

```
Browser (React SPA)  ──HTTP──▶  Flask API  ──▶  Groq Whisper (transcribe)
                                     │                │
                                     ▼                ▼
                               In-memory sessions   Transcript + segments
                                     │                │
                                     ▼                ▼
                              Groq LLM ──▶ Notes / Quiz / Flashcards (validated JSON)
                                     │
                                     ▼
                              Export (TXT / PDF)
```

Full details in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [docs/AI_PIPELINE.md](docs/AI_PIPELINE.md).

## Project structure

```
.
├── backend/                  # Flask API
│   ├── app.py                # Routes, middleware, error handling
│   ├── config.py             # Env-driven configuration + validation
│   ├── services/             # whisper, groq, export, session store
│   ├── utils/                # prompts, parsing, security, file validation
│   ├── assets/fonts/         # Bundled Unicode fonts for PDF export
│   └── tests/                # pytest suite (29 tests)
├── frontend/                 # React + Vite + Tailwind SPA
│   ├── src/                  # components, pages, api client
│   └── e2e/                  # Playwright end-to-end tests
├── docs/                     # Architecture, audits, roadmap (10 docs)
├── render.yaml               # Render blueprint
└── .github/workflows/ci.yml  # CI: pytest + vitest + build + e2e
```

## Getting started (local development)

### Prerequisites
- Python 3.10+
- Node.js 18+
- A free [Groq API key](https://console.groq.com/)

### 1. Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # then set GROQ_API_KEY
python app.py                  # http://localhost:5000
```

### 2. Frontend
```bash
cd frontend
npm install
npm run dev                    # http://localhost:5173 (proxies /api -> :5000)
```

### 3. Run the tests
```bash
cd backend && pytest -q                # 29 backend tests
cd frontend && npm test                # 26 frontend tests
cd frontend && npm run test:e2e        # 2 Playwright E2E tests (no API key needed)
```

## Configuration

All settings are environment variables (see [backend/.env.example](backend/.env.example)):

| Variable | Default | Purpose |
|----------|---------|---------|
| `GROQ_API_KEY` | — | **Required** in production |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Chat model for generation |
| `WHISPER_MODEL` | `whisper-large-v3` | Transcription model |
| `MAX_CONTENT_LENGTH` | `52428800` | Max upload size (bytes) |
| `SESSION_TTL_SECONDS` | `21600` | Session lifetime before cleanup |
| `RATE_LIMIT_TRANSCRIBE` | `5` | Transcriptions per IP per hour (0 = off) |
| `RATE_LIMIT_GENERATE` | `20` | Generations per IP per hour (0 = off) |
| `TRANSCRIPT_MAX_CHARS` | `40000` | Transcript size sent to the LLM |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |

## API overview

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/api/health` | Liveness check |
| `POST` | `/api/transcribe` | Upload audio → transcript + session |
| `POST` | `/api/generate/notes` | Markdown study notes |
| `POST` | `/api/generate/quiz` | 10-question MCQ quiz (validated JSON) |
| `POST` | `/api/generate/flashcards` | Flashcard deck (validated JSON) |
| `POST` | `/api/download/notes` | Export notes as TXT or PDF |

Full contract, request/response examples, and status codes: [docs/API.md](docs/API.md).

## Deployment (Render, free tier)

One URL serves both the React UI and the Flask API. Render reads `render.yaml` (Blueprint):

1. Push the repo to GitHub.
2. In Render: **New + → Blueprint →** connect the `lecturemind-ai` repo.
3. Set **`GROQ_API_KEY`** when prompted.
4. Click **Apply**. The `render-build.sh` script installs Python deps, builds the frontend, and copies it into `backend/static`.

**Free-tier notes**
- The service sleeps after ~15 min of inactivity; the first request after sleep takes 30–60 s to wake up.
- Sessions and uploads live in memory / ephemeral disk and reset on redeploy. A single worker is required (in-memory session store) — see [docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md).

## Documentation

| Doc | What it covers |
|-----|----------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flow, directory layout |
| [API.md](docs/API.md) | Full API reference and contracts |
| [AI_PIPELINE.md](docs/AI_PIPELINE.md) | Whisper → LLM pipeline, failure modes, mitigations |
| [SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md) | Secrets, uploads, API & AI security |
| [PERFORMANCE_AUDIT.md](docs/PERFORMANCE_AUDIT.md) | Frontend/backend/API performance |
| [UI_UX_AUDIT.md](docs/UI_UX_AUDIT.md) | UX, responsive, accessibility review |
| [PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) | Deployment, runbook, scaling path |
| [ROADMAP.md](docs/ROADMAP.md) | Prioritized P0–P3 roadmap |
| [TECH_DEBT.md](docs/TECH_DEBT.md) | Honest debt register |
| [AUDIT_REPORT.md](docs/AUDIT_REPORT.md) | Full deep-codebase audit findings |

## Security

- No secrets in the repository; history was rewritten to remove accidentally committed build artifacts. Use `.env` locally and the Render dashboard in production.
- Rate limiting, sanitized error responses, CORS/CSP headers, magic-byte upload validation, session TTL + file cleanup.
- The transcript is treated as **untrusted data**: prompts wrap it in markers and explicitly ignore instructions inside it (prompt-injection resistance).
- See [docs/SECURITY_AUDIT.md](docs/SECURITY_AUDIT.md) for the full threat model and residual risks.

## Known limitations

- Hallucination risk cannot be fully eliminated — notes are grounded in the transcript but should be reviewed.
- Very long lectures are truncated to ~40k characters for generation.
- Sessions are in-memory: lost on redeploy, single worker required.
- Rate limits are per-process and reset on redeploy.

## Roadmap

Current status: **P0/P1 complete** (critical reliability + security), **P2 largely complete** (UX/accessibility polish). P3 ideas (persistence, auth, lecture history, sharing, async jobs, RAG grounding) are in [docs/ROADMAP.md](docs/ROADMAP.md).

## License

MIT — see [LICENSE](LICENSE).