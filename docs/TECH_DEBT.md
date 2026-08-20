# LectureMind AI — Technical Debt Register

> An honest ledger of known limitations in the current codebase, with
> impact, suggested remediation, and priority. Items marked **Accepted**
> are deliberate demo-scope trade-offs; the rest feed `ROADMAP.md`.
> Related: `AUDIT_REPORT.md` (findings history), `PRODUCTION_READINESS.md`
> (operational impact), `PERFORMANCE_AUDIT.md` (concurrency context).

## 1. Register

Priority: **High** = blocks production use, **Medium** = hurts reliability
or scale, **Low** = cosmetic or cheap to leave. Remediations reference
`ROADMAP.md` items where applicable.

| # | Debt | Impact | Remediation | Priority |
|---|---|---|---|---|
| D1 | In-memory session store | All sessions and transcripts lost on restart/redeploy; app cannot serve multiple instances | SQLite/Postgres-backed store (P3-1) | High |
| D2 | No database | No history, user data, or analytics; everything ephemeral | Introduce SQLite first, Postgres for scale (P3-1) | High |
| D3 | Synchronous long requests block the worker | One transcribe/generate (90–120 s) freezes all other requests on the instance | Background job queue + polling (P3-9); interim `--threads 4` so static/health still respond | High |
| D4 | No background job queue | Consequence of D3: no job ids, no progress, no retry UI | RQ/Celery + job status endpoint (P3-9) | High |
| D5 | Rate limits are per-process | Counters live in process memory; redeploys reset them; multi-worker deployments weaken enforcement | Redis-backed counters when scaling (P3) | Medium |
| D6 | No authentication | Session ids are the only credential; anyone holding one can regenerate from that transcript | OAuth/magic-link auth (P3-2) | High |
| D7 | No metrics/tracing/error tracking | Observability is log-only; incidents are found by reading logs | Sentry + uptime pings; Prometheus when scaling (PRODUCTION_READINESS §5) | Medium |
| D8 | Prompts not A/B tested | Output quality (difficulty spread, hallucination rate) is unmeasured | Evaluation harness over a small transcript corpus | Medium |
| D9 | Magic-byte validation covers only mp3/wav/m4a | Other formats are rejected by design; a crafted file that passes the sniff costs a Groq call before failing | FFmpeg probe would widen coverage but adds a runtime dependency — probably not worth it for the demo | Low |
| D10 | Transcript truncation at 40k chars | Very long lectures silently drop the tail (a note is appended, but content is lost) | Chunked/iterative summarization pipeline | Medium |
| D11 | Hallucination risk remains | The LLM can still invent facts; grounding + markers + schema validation reduce but do not eliminate it | RAG grounding + citation extraction; "AI-generated" disclaimers in the UI | Medium |
| D12 | No i18n | UI is English-only | react-i18next; Hindi first (Devanagari PDF export already works) | Medium |
| D13 | Minimal E2E coverage | Backend has 29 pytest cases; frontend has zero test files (Vitest + Playwright are configured, no CI yet) | Vitest component tests + Playwright flows with stubbed API; CI workflow (P2-11) | Medium |
| D14 | Single-cloud deployment (Render) | Vendor lock-in, no multi-region, free-tier availability risk | Dockerfile to keep the door open; don't build around Render-specific features | Low |
| D15 | Logging is stdout-only | No log shipping/retention beyond Render's limited history | Log drains to a hosted service when needed | Low |
| D16 | No caching of generations | Identical transcripts re-pay the full Groq cost every time | Cache by transcript hash (pairs with D1/D2) | Medium |
| D17 | Session ids not revocable | Cannot expire an individual session early or ban one | Auth session layer (P3-2) or a denylist | Low |
| D18 | Frontend bundle not code-split | ~86 KB gzipped — fine now, grows with features | Route-level splitting when the app grows beyond one page | Low |

## 2. Items worth calling out

### D3 — the blocking-worker math
`PERFORMANCE_AUDIT.md` §3 quantifies it: one worker × one blocking request
means a health check, download, or static asset waits behind someone else's
Groq call. The cheapest mitigation before the async rework is
`--threads 4` + `--timeout 300` (the session store is lock-protected; the
rate-limit deques are safe for these operations under the GIL, but should
get a dedicated thread-safety test). Note this is a **demo freeze**, not a
data-integrity issue — the store's lock keeps it consistent even under
concurrency.

### D6 — the "credential" problem
Session ids are `uuid4` (unguessable) and short-lived (6 h TTL), so the
practical risk is low: a leaked id can only regenerate material from one
transcript for a few hours. But there is no way to revoke one, and a user
who shares a demo link that embeds a session id exposes their transcript.
This is acceptable until auth lands (P3-2), and should be called out on
the demo page.

### D9 — validation is a filter, not a scanner
Magic bytes reject renamed binaries cheaply, but a file with a valid
container header and undecodable audio still costs a Groq transcription
call before failing at the API. Combined with the per-IP transcribe limit
(5/hr), the abuse cost is bounded. Deep inspection (FFmpeg decode test,
antivirus) is intentionally out of scope (see §3).

### D10 — truncation is a correctness debt
`groq_service._truncate` cuts at the last sentence boundary within 40k
chars. For a 90-minute lecture the budget is likely consumed by early
content, so later topics never reach the model. The prompt is told the
input was truncated, but the user is not clearly told what was dropped.
A chunked "section → summary → merge" pipeline is the proper fix.

### D13 — testing asymmetry
Backend coverage is solid: health, upload validation including magic bytes,
session TTL + file cleanup, generation mocking including sanitized errors,
export TXT/PDF including Unicode, rate-limit 429, API 404/405, and security
headers. Frontend coverage is zero today; the tooling is installed and the
CI workflow is planned. Playwright E2E should stub the API routes so no real
Groq key is needed in CI.

## 3. Intentionally deferred (Accepted — not worth the complexity now)

These are conscious demo-scope decisions, not accidents:

| Item | Why deferred |
|---|---|
| Local / self-hosted Whisper | Cloud Whisper on Groq needs no GPU or weights on the server and keeps the footprint tiny |
| Async job queue | Genuinely needed only past demo concurrency; adds Redis + worker infrastructure now |
| Auth & multi-tenancy | No real users yet; session-id bearer tokens fit the internship demo |
| Containerization / Kubernetes / HA | Render free tier is the target; a Dockerfile is cheap insurance, K8s is overkill |
| i18n | Single demo audience; UI strings are few and centralized |
| Streaming responses | Nice-to-have UX; adds SSE plumbing and per-token error handling |
| CDN / cache headers on static assets | ~86 KB gzipped bundle; Flask serving is fine at this scale |
| FFmpeg / format expansion | The 3-format whitelist covers the demo; each new format adds validation + testing surface |
| Antivirus / deep content inspection | Magic bytes + size cap + rate limits are proportionate; scanning is enterprise scope |
| CAPTCHA / anti-bot hardening | Per-IP rate limits already cap abuse cost |
| Data-retention / GDPR tooling | No accounts, no stored PII beyond transient transcripts; revisit with auth (P3-2) |

## 4. Debt payment plan

| When | Pay down | Why now |
|---|---|---|
| Before demo day | Nothing new required — current debt does not block the demo happy path | D3's freeze is the only visible symptom and only under concurrent load |
| When real users appear | D6 (auth), D7 (Sentry), D1/D2 (persistence) | Credentials, errors, and restart survival become user-facing issues |
| When scaling beyond one instance | D1–D5 as a package | Persistence + shared rate limiting + async jobs are prerequisites, not nice-to-haves |
| Opportunistically | D8, D10, D13, D16 | Each is a bounded, testable improvement that also de-risks AI output quality |

The frontier remains **persistence and concurrency** (D1–D4): the only
High-priority debts, and the ones that gate the rest of `ROADMAP.md`.