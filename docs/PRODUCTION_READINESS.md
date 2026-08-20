# LectureMind AI — Production Readiness

> An honest assessment of what is safe to run in front of a demo audience
> today, what is demo-grade, and what must change before real users depend
> on it. Deployment target: Render free tier. Related: `ARCHITECTURE.md`
> §5–6, `PERFORMANCE_AUDIT.md` §3–4, `SECURITY_AUDIT.md`, `TECH_DEBT.md`.

## 1. Summary

| Area | Grade | What this means |
|---|---|---|
| Core functionality | Production-grade | Upload → transcribe → generate → export works end-to-end, hardened, and covered by 29 backend tests |
| Error handling | Production-grade | Sanitized JSON errors on every path (400/404/405/413/422/429/500/502/503/504); no internals leak |
| Security posture | Good for a demo | Secrets, rate limits, upload validation, and headers are solid; no auth, no antivirus, per-process limits |
| State | Demo-grade | In-memory sessions: lost on restart/redeploy, single-worker only |
| Concurrency | Demo-grade | One synchronous worker; long AI calls block all other requests |
| Observability | Minimal | Structured stdout logs only; no metrics, tracing, or error tracking |
| Availability | Demo-grade | Render free tier sleeps after ~15 min, cold-starts in 30–60 s, ephemeral disk, no SLA |

**Bottom line:** safe to demo, not safe to sell. The gap is almost entirely
architectural (state, concurrency, observability) rather than code quality.

## 2. Deployment topology (Render free tier)

- **Service**: single Python web service (`render.yaml`), `rootDir: backend`,
  free plan.
- **Build**: `bash render-build.sh` — `pip install -r requirements.txt`,
  then `cd ../frontend && npm ci && npm run build`, then wipes and repopulates
  `backend/static` from `dist/*` (a stale build can never be served).
- **Runtime**: Python 3.11.9; Node 20 used at build time only;
  `GROQ_API_KEY` injected via env with `sync: false` (never committed).
- **Start**: `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1`
  (current `render.yaml`).
- **Free-tier constraints** (behavioral):
  - Sleeps after ~15 minutes of inactivity; the first request wakes it
    (30–60 s cold start).
  - Ephemeral disk: `backend/uploads/` and session memory vanish on redeploy.
  - One instance only; no horizontal scaling without persistence first.

## 3. Single worker + threads model

| Fact | Implication |
|---|---|
| `--workers 1` | In-memory session store stays consistent (required — `ARCHITECTURE.md` §6) |
| One request at a time | A 90–120 s Groq call blocks every other request on the instance |
| `--timeout 120` > `WHISPER_TIMEOUT` (120) ≥ `GROQ_TIMEOUT` (90) | gunicorn only aborts after Groq itself gives up — deliberate, must be re-checked if timeouts change |
| No `--threads` | Even `/api/health` and static assets wait behind a long generate |

**Hardening plan (planned, not yet in `render.yaml`):**
- Raise the gunicorn timeout to **300 s** (`--timeout 300`) so slow Groq
  calls are never cut mid-flight; keep `--workers 1` for session
  consistency.
- Add **`--threads 4`** so the worker can answer health checks and serve
  static assets while one thread is blocked on Groq. The session store is
  lock-guarded (thread-safe); rate-limit counters are plain deques, safe
  under the GIL for these operations, but worth a dedicated test.
- This removes the worst "whole site frozen" behavior without breaking the
  single-process session invariant. The real scaling path still requires
  persistence (§4).

## 4. Scaling path (in order)

1. **Persistence** — sessions to SQLite (zero dependency) or Postgres
   (Render free tier includes a small Postgres). Unblocks multi-worker,
   restart survival, lecture history (`ROADMAP.md` P3).
2. **Async job queue** — transcribe/generate become background jobs (Redis +
   RQ, or Render background workers) with a job-id polling endpoint; HTTP
   requests stop blocking on AI calls.
3. **Horizontal scaling** — multiple workers/instances behind load
   balancing, shared rate limiting (Redis), shared file storage (Render
   Disk or S3-compatible).
4. **AI-layer improvements** — streaming generation, caching identical
   transcripts, RAG grounding.

## 5. Observability

**What exists:** structured stdout logs — timestamp, level, logger name, and
`key=value` fields (method, path, status, duration_ms, ip per request;
session created/expired/swept events; generation completed with output size;
Groq warnings with model + attempt). No metrics, no tracing, no error
tracking.

**Recommendations:**

| Gap | Recommendation | Effort |
|---|---|---|
| Error tracking | Sentry (free tier) — captures the detailed server-side exceptions behind sanitized responses | 30 min |
| Uptime monitoring | UptimeRobot / Better Stack ping on `/api/health` — also keeps the free instance warm | 15 min |
| Metrics | Prometheus/Grafana or Render metrics; per-endpoint latency percentiles | half day |
| Tracing | Not needed at this scale; add OpenTelemetry only when multi-worker | later |

## 6. Backup / disaster considerations

- **No durable data today**: sessions and uploads live in memory/ephemeral
  disk. A redeploy or crash loses everything in progress. For a demo this
  is acceptable (the workflow is minutes long).
- **Secrets**: `GROQ_API_KEY` exists only in the Render environment; rotation
  = update dashboard + redeploy. No secrets in git (verified; git history
  rewritten).
- **Recovery**: worst case is a service restart; users simply re-upload.
  README documents that state does not survive redeploys.
- If persistence is added (P3), a backup policy must be designed with the
  DB choice (SQLite file vs managed Postgres).

## 7. Runbook

### Environment variables (all documented in `backend/.env.example`)

| Variable | Default | Notes |
|---|---|---|
| `GROQ_API_KEY` | — | Required in production; `validate_config()` fails fast at startup |
| `GROQ_MODEL` | `openai/gpt-oss-20b` | Chat model; fallback `openai/gpt-oss-120b` |
| `WHISPER_MODEL` | `whisper-large-v3` | Groq-hosted |
| `MAX_CONTENT_LENGTH` | 52,428,800 (50 MB) | Upload cap |
| `SESSION_TTL_SECONDS` | 21,600 (6 h) | Sliding session TTL |
| `RATE_LIMIT_TRANSCRIBE` / `RATE_LIMIT_GENERATE` | 5 / 20 | Per IP per hour; `0` disables |
| `GROQ_TIMEOUT` / `WHISPER_TIMEOUT` | 90 / 120 | Must stay below the gunicorn timeout |
| `TRANSCRIPT_MAX_CHARS` | 40,000 | Prompt budget cap |
| `CORS_ORIGINS` | `*` | Set a concrete list in production |

### Deploy steps

1. Push to GitHub; the connected Render Blueprint auto-deploys.
2. Verify `https://<app>.onrender.com/api/health` returns
   `{"status": "ok", ...}`.
3. Smoke test: upload a small MP3 → generate notes → download PDF (both
   formats).
4. Watch the first minutes of logs for `request_failed` or Groq warnings.

### Rollback

- Render keeps deploy history: redeploy a previous deploy, or `git revert`
  + push. Sessions are lost either way (in-memory).
- If `GROQ_API_KEY` is suspected exposed: rotate it at console.groq.com,
  update the Render env var, redeploy. No other secrets exist in the system.

## 8. Readiness checklist

| Item | Status |
|---|---|
| Fails fast without API key in production | ✅ |
| Sanitized errors (no internals leak) | ✅ |
| Rate limits on cost-bearing endpoints | ✅ |
| Upload validation (extension + magic bytes + size) | ✅ |
| Session TTL + upload file cleanup | ✅ |
| JSON 404/405/413/422/429 on API | ✅ |
| Security headers on `/api/*` | ✅ |
| CORS restricted to `/api/*`, configurable origins | ✅ |
| Structured request logging | ✅ |
| Backend test suite green (29 tests) | ✅ |
| Frontend tests (Vitest) / E2E (Playwright) | ⏳ Planned |
| CI workflow (pytest + frontend build + vitest) | ⏳ Planned |
| gunicorn timeout 300 + `--threads 4` | ⏳ Planned |
| Sentry error tracking | ❌ Recommended |
| Uptime healthcheck pings | ❌ Recommended |
| Metrics / tracing | ❌ Deferred (not needed at this scale) |
| Authentication | ❌ P3 roadmap |
| Persistence (restart-safe state) | ❌ P3 roadmap |
| Availability / SLAs | N/A (free tier, demo) |