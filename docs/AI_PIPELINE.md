# LectureMind AI — AI Pipeline

> End-to-end description of the AI pipeline in the **current** codebase, with
> per-stage failure modes and their mitigations. All model calls are remote
> Groq calls; nothing runs locally.

## 1. Pipeline overview

```
 upload ──► validate ──► store ──► transcribe ──► transcript ──► generate ──► parse/validate ──► export
 (HTTP)    (ext+magic)  (disk)    (Groq Whisper) + segments     (Groq chat)   (schemas)         (TXT/PDF)
```

Stages and modules:

| # | Stage | Module / function | Notes |
|---|-------|-------------------|-------|
| 1 | Audio upload | `app.transcribe` | multipart field `audio` |
| 2 | Validation | `utils/file_validator` | extension + magic bytes + 50 MB cap |
| 3 | Storage | `app.transcribe` / `UPLOAD_FOLDER` | `{uuid}.{ext}` on disk |
| 4 | Transcription | `services/whisper_service.transcribe_audio` | Groq `whisper-large-v3`, `verbose_json` |
| 5 | Transcript + segments | `session_store.create` | text, language, segments |
| 6 | Chat generation | `services/groq_service.generate_{notes,quiz,flashcards}` | Groq `openai/gpt-oss-20b` |
| 7 | Parsing / validation | `utils/parsing` | `extract_json_object` + schema validation |
| 8 | Export | `services/export_service` | TXT/PDF |

## 2. Stage-by-stage detail and failure modes

### Stage 1–3: Upload, validation, storage

- Client sends `multipart/form-data` with `audio`. Server checks presence,
  extension (`{mp3, wav, m4a}`), writes with a sanitized `{uuid}.{ext}`
  filename, then verifies magic bytes (`ID3`/MPEG sync, `RIFF..WAVE`, `ftyp`).
- **Failure modes and mitigations:**
  - Missing field → 400 "No audio file provided".
  - Bad extension → 400 "Invalid file. Allowed: MP3, WAV, M4A".
  - Oversized (> 50 MB) → 413 (Werkzeug `RequestEntityTooLarge` handler).
  - Fake/renamed file that fails the signature → 400 and the file is deleted
    immediately (no linger).
  - Disk write/OS errors → caught in the route's try/except; file removed on
    failure; sanitized 500.

### Stage 4: Transcription (Groq Whisper)

`whisper_service.transcribe_audio` opens the saved file, calls
`client.audio.transcriptions.create(file=..., model=WHISPER_MODEL,
response_format="verbose_json")`, and reads `text`, `language`, and
`segments` defensively (attribute or dict access, because the SDK models only
`text`; the rest varies by SDK version). Each segment is normalized to
`{start, end, text}` with floats rounded to 2 decimals.

- **Models/config**: `WHISPER_MODEL=whisper-large-v3` (env-configurable),
  `WHISPER_TIMEOUT=120` (client timeout), key from `GROQ_API_KEY`.
- **Failure modes and mitigations:**
  - Empty/missing key → `ValueError("GROQ_API_KEY is not configured")` →
    sanitized error; production startup fails fast anyway (`validate_config`).
  - Groq API down / timeout / rate limit → exceptions bubble to `app.py`,
    logged with `logger.exception`, file deleted, and `error_response`
    returns a safe 502/503/504/500 message (no internals leaked).
  - No speech detected (empty `text`) → 422 "No speech detected in the audio.
    Please try a clearer recording." and the file is deleted.
  - Malformed segments → filtered: empty segment text is skipped, missing
    times become `0.0`.

### Stage 5: Session creation

On success, `store.create(...)` records the transcript, segments, language,
and on-disk path under a fresh `uuid4` session id; it is later resolved from
the `X-Session-Id` header or `session_id` body field. Failure mode is
negligible (in-memory); session expiry/sweep is covered in
`docs/ARCHITECTURE.md`.

### Stage 6: Chat generation (Groq, `gpt-oss-20b`)

`groq_service.generate_*` build the prompt with `build_prompt` (wraps the
transcript in `<lecture_transcript>` markers) and call `_chat`.

- **Model choices / parameters:**

  | Output | Temperature | max_tokens | Notes |
  |--------|-------------|-----------|-------|
  | Notes | 0.2 | 4096 | free-form markdown; min length check (>= 40 chars) |
  | Quiz | 0.4 | 4096 | schema: exactly 10 questions |
  | Flashcards | 0.35 | 4096 | schema: 5–15 cards |

- **Prompt design** (`utils/prompts.py`): each template declares the
  transcript "untrusted data between the markers", instructs ignoring any
  instructions inside it, forbids inventing facts, and demands the exact
  output shape (JSON schema for quiz/flashcards, markdown for notes). The
  system message is fixed in `SYSTEM_PROMPT` (grounding: generate strictly
  from the transcript, ignore in-transcript instructions).
- **Truncation** (`_truncate`): if the transcript exceeds
  `TRANSCRIPT_MAX_CHARS` (40k default), cut at the last `. ` within the
  budget (falling back to a hard cut only if no boundary past 60% of the
  limit) and append `[Note: the transcript was truncated...]` so the model
  knows the input is partial.
- **Retries and fallback** (`_chat`):
  - Up to `GROQ_MAX_RETRIES` (2) attempts.
  - Model list = `[GROQ_MODEL] + fallbacks`, i.e. `openai/gpt-oss-20b` then
    `openai/gpt-oss-120b` (dedup).
  - `RateLimitError`/429 → exponential backoff `2 ** attempt`.
  - `APITimeoutError`, `APIConnectionError`, 5xx → short sleep and retry.
  - 404 (model not found / no access) → `continue` to the next model.
  - Empty content → `GenerationError("Empty response from the AI model")`.
  - Other 4xx → `GenerationError("The AI service rejected the request")`.
  - Exhaustion → `GenerationError("The AI service is unavailable. Please try
    again later.")`.
- **Failure modes and mitigations:**
  - Groq quota/transient → backoff + retry + fallback model.
  - Deprecated/unavailable model → fallback list and configurable `GROQ_MODEL`.
  - Truncation silently degrading coverage → the appended note and a
    documented limitation (very long lectures are cut at 40k chars).

### Stage 7: Parsing and schema validation

`utils/parsing.extract_json_object` normalizes LLM output: strips markdown
fences, tries `json.loads`, then falls back to scanning balanced braces
(string- and escape-aware) to lift the first embedded JSON object. Raises
`SchemaError` if nothing parses.

- `validate_quiz` requires a `questions` list of **exactly 10**; each question
  has non-empty text, exactly 4 options keyed A–D (non-empty), a
  `correct_answer` in those letters, `difficulty` normalized to
  easy/medium/hard (default medium), an optional explanation; duplicate
  questions (casefolded) are rejected. Output is re-keyed with numeric `id`.
- `validate_flashcards` requires a non-empty `flashcards` list; skips invalid
  or duplicate cards, keeps up to 15, and requires at least 5 valid cards.
- **Regeneration retry**: for quiz/flashcards, if validation fails on the
  first attempt, one regeneration is attempted; a second failure surfaces a
  user-safe `GenerationError` ("... produced invalid data. Please try
  again.").
- **Failure modes and mitigations:**
  - Model wraps JSON in fences / adds prose → `extract_json_object` handles.
  - Model returns 9 or 11 questions / missing options / wrong difficulty →
    `SchemaError` → one retry → safe error.
  - Repeated malformed output → GenerationError → 502 to the client
    (`app.py` catches `GenerationError` and returns its message directly,
    which is safe by construction).

### Stage 8: Export

`export_service` converts generated markdown notes to TXT (`notes_to_txt`) or
PDF (`notes_to_pdf`, fpdf2). Validation caps title at 120 chars and notes at
1,000,000 chars (400/413 via `AppError`). Known content-dependent PDF crashes
are documented (`docs/AUDIT_REPORT.md` A12).

## 3. Reliability summary

- Timeouts: Whisper 120 s, chat 90 s — bounded by gunicorn `--timeout 120`.
- Retries: 2 attempts with backoff; one regeneration retry on schema failure.
- Fallbacks: second chat model (`gpt-oss-120b`).
- Grounding: fixed system prompt + "untrusted transcript" markers + "do not
  invent facts" instructions + schema-constrained outputs.
- Honest limits: transcript truncation at 40k chars; hallucination risk cannot
  be fully eliminated; notes are not schema-validated (free-form markdown).