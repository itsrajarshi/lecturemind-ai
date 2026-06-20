# LectureMind AI – Complete Project Documentation

**AICTE + Edunet Foundation + IBM SkillsBuild · Artificial Intelligence Internship**

---

## 1. Project Overview

| Item | Detail |
|------|--------|
| **Project Title** | LectureMind AI – Lecture Voice-to-Notes Generator |
| **Objective** | Help students convert lecture audio into structured study materials without manual note-taking during class |
| **Scope** | Audio upload → Whisper transcription → Groq-powered notes, quiz (10 MCQs), flashcards → PDF/TXT export |
| **Expected Outcome** | A working web app demonstrable in 5 minutes; clear AI pipeline (STT + Generative AI); internship-ready documentation |

**Problem:** Students cannot listen and write simultaneously; they miss concepts and revise poorly from raw recordings.

**Solution:** Upload once → get transcript + exam-oriented notes + self-test quiz + revision flashcards.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         STUDENT (Browser)                                │
│                    React + Vite + Tailwind CSS                           │
│  ┌──────────┐ ┌────────────┐ ┌──────┐ ┌────────────┐ ┌──────────────┐  │
│  │  Upload  │ │ Transcript │ │Notes │ │ Quiz (10)  │ │ Flashcards   │  │
│  └────┬─────┘ └─────▲──────┘ └──▲───┘ └─────▲──────┘ └──────▲───────┘  │
└───────┼─────────────┼───────────┼───────────┼────────────────┼──────────┘
        │             │           │           │                │
        │  HTTP/REST  │           │           │                │
        ▼             │           │           │                │
┌─────────────────────────────────────────────────────────────────────────┐
│                    Flask API (Python) :5000                              │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌──────────────┐  │
│  │ File Upload │  │ Whisper Svc  │  │  Groq Svc   │  │ Export Svc   │  │
│  │  Validator  │  │  (local STT) │  │  (Llama 3.3)│  │ PDF / TXT    │  │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └──────────────┘  │
│         │                │                 │                             │
│         ▼                ▼                 ▼                             │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────────────────┐ │
│  │ uploads/    │  │ openai-      │  │ Groq API (cloud, free tier)      │ │
│  │  (disk)     │  │ whisper      │  │ llama-3.3-70b-versatile          │ │
│  └─────────────┘  └──────────────┘  └─────────────────────────────────┘ │
│         In-memory session store (no SQLite required)                       │
└─────────────────────────────────────────────────────────────────────────┘
```

**Data flow:**

1. User uploads MP3/WAV/M4A → saved to `backend/uploads/`
2. Whisper transcribes → transcript returned + `session_id`
3. User triggers notes/quiz/flashcards → Groq reads transcript → structured JSON/markdown
4. User downloads notes → `fpdf2` (PDF) or plain text

---

## 3. Complete Folder Structure

```
lecturemind-ai/
├── README.md
├── PROJECT_DOCUMENTATION.md
├── .gitignore
├── backend/
│   ├── app.py                 # Flask routes
│   ├── config.py              # Env & paths
│   ├── requirements.txt
│   ├── .env.example
│   ├── uploads/               # Temp audio files
│   ├── services/
│   │   ├── whisper_service.py
│   │   ├── groq_service.py
│   │   └── export_service.py
│   └── utils/
│       ├── file_validator.py
│       └── prompts.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── postcss.config.js
    ├── index.html
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css
        ├── api/
        │   └── client.js
        ├── pages/
        │   └── Home.jsx
        └── components/
            ├── Header.jsx
            ├── AudioUploader.jsx
            ├── TranscriptPanel.jsx
            ├── NotesPanel.jsx
            ├── QuizPanel.jsx
            ├── FlashcardsPanel.jsx
            └── LoadingSpinner.jsx
```

---

## 4. Frontend Design

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| Home | `/` | Single-page workflow: upload → generate → download |

### Components

| Component | Responsibility |
|-----------|----------------|
| `Header` | Branding, internship badge |
| `AudioUploader` | Drag-style upload, format validation |
| `TranscriptPanel` | Scrollable transcript + language tag |
| `NotesPanel` | Markdown render + download buttons |
| `QuizPanel` | 10 MCQs, submit, score, explanations |
| `FlashcardsPanel` | Flip card UI, prev/next navigation |
| `LoadingSpinner` | Async feedback for Whisper/Groq |

### Navigation Flow

```
[Upload Audio] → [View Transcript] → [Generate Notes | Quiz | Flashcards]
                                              ↓
                                    [Download TXT / PDF]
```

### UI Layout (Desktop)

```
┌────────────────────────────────────────────────────────┐
│  LM  LectureMind AI                    IBM SkillsBuild │
├────────────────────────────────────────────────────────┤
│              ┌ Upload Lecture Audio ─┐               │
│              │     Choose File        │               │
│              └────────────────────────┘               │
│  [Generate Notes] [Generate Quiz] [Generate Flashcards]│
├────────────────────────────────────────────────────────┤
│  Transcript          │  Study Notes (+ Download)       │
├──────────────────────┴─────────────────────────────────┤
│  Quiz (MCQ grid)     │  Flashcard (flip)               │
└────────────────────────────────────────────────────────┘
```

---

## 5. Backend Design

### Flask Structure

- **`app.py`** – HTTP layer, CORS, session dict, error handlers
- **`config.py`** – Centralized env (Groq key, Whisper model, upload limits)
- **`services/`** – Business logic isolated from routes
- **`utils/`** – Prompts, file validation

### Service Layer

| Service | Function |
|---------|----------|
| `whisper_service` | Load model once, `transcribe_audio(path)` |
| `groq_service` | `generate_notes`, `generate_quiz`, `generate_flashcards` |
| `export_service` | `notes_to_txt`, `notes_to_pdf` |

### Utility Layer

| Utility | Function |
|---------|----------|
| `file_validator` | Extension whitelist, `secure_filename` |
| `prompts` | Production prompts for notes/quiz/flashcards |

---

## 6. API Endpoints

### `GET /api/health`

**Response:**
```json
{ "status": "ok", "service": "LectureMind AI" }
```

---

### `POST /api/transcribe`

**Request:** `multipart/form-data`

| Field | Type | Required |
|-------|------|----------|
| audio | file | Yes |

**Response (200):**
```json
{
  "session_id": "uuid",
  "transcript": "full text...",
  "language": "en",
  "segments": [{ "start": 0.0, "end": 5.2, "text": "..." }]
}
```

**Errors:** `400` invalid file, `413` too large, `500` Whisper failure

---

### `POST /api/generate/notes`

**Request:**
```json
{ "session_id": "uuid", "transcript": "optional if session exists" }
```

**Headers:** `X-Session-Id: uuid` (optional)

**Response:**
```json
{ "notes": "## Topic\n- bullet", "format": "markdown" }
```

---

### `POST /api/generate/quiz`

**Request:** Same as notes

**Response:**
```json
{
  "quiz_title": "Data Structures Quiz",
  "questions": [
    {
      "id": 1,
      "question": "What is a stack?",
      "options": { "A": "...", "B": "...", "C": "...", "D": "..." },
      "correct_answer": "B",
      "difficulty": "easy",
      "explanation": "..."
    }
  ]
}
```

---

### `POST /api/generate/flashcards`

**Response:**
```json
{
  "deck_title": "Lecture Revision Deck",
  "flashcards": [{ "id": 1, "question": "...", "answer": "..." }]
}
```

---

### `POST /api/download/notes`

**Request:**
```json
{ "notes": "markdown text", "format": "txt|pdf", "title": "Lecture Notes" }
```

**Response:** File download (`lecture_notes.txt` or `lecture_notes.pdf`)

---

## 7. Database Design

**Decision:** SQLite **not used** for v1. Sessions stored in-memory on the server for the demo lifecycle. This keeps deployment simple and meets “SQLite only if necessary.”

**Optional future schema** (if persistence added):

```
lectures(id, filename, transcript, created_at)
notes(id, lecture_id, content_md)
quizzes(id, lecture_id, json_blob)
flashcards(id, lecture_id, json_blob)
```

---

## 8. Groq Integration

### Installation

```bash
pip install groq==0.11.0
```

### Environment

```env
GROQ_API_KEY=<YOUR_GROQ_API_KEY>
```

Get a free key: https://console.groq.com/

### Sample Implementation

```python
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

client = Groq(api_key=GROQ_API_KEY)
response = client.chat.completions.create(
    model=GROQ_MODEL,  # llama-3.3-70b-versatile
    messages=[
        {"role": "system", "content": "You are LectureMind AI."},
        {"role": "user", "content": prompt},
    ],
    temperature=0.3,
    max_tokens=4096,
)
text = response.choices[0].message.content
```

See `backend/services/groq_service.py` for full implementation.

---

## 9. Whisper Integration

### Installation

```bash
pip install openai-whisper
# FFmpeg must be on PATH
```

### Model Selection

| Model | Speed | Accuracy | RAM |
|-------|-------|----------|-----|
| tiny | Fastest | Lower | ~1 GB |
| base | Balanced (default) | Good | ~1 GB |
| small | Slower | Better | ~2 GB |

Set in `.env`: `WHISPER_MODEL=base`

### Pipeline

1. Save uploaded audio to `uploads/{session_id}.ext`
2. `whisper.load_model()` once (singleton)
3. `model.transcribe(path, fp16=False)` → text + segments
4. Return JSON to frontend

See `backend/services/whisper_service.py`.

---

## 10. Prompt Engineering

Prompts live in `backend/utils/prompts.py`.

### A. Notes Generation

- **Input:** Lecture transcript (truncated to ~12k chars)
- **Processing:** Groq chat, temperature 0.2
- **Output:** Markdown with `##` headings, bullets, bold terms, Key Takeaways
- **Guardrails:** “Do NOT invent facts not in transcript”

### B. Quiz Generation

- **Input:** Transcript
- **Output:** JSON with exactly 10 MCQs, 4 options, correct answer, difficulty, explanation
- **Guardrails:** JSON-only response; answerable from transcript only

### C. Flashcards Generation

- **Input:** Transcript
- **Output:** JSON with 15 Q/A pairs, concise answers
- **Guardrails:** Revision-friendly phrasing

---

## 11. Implementation Roadmap (6 Weeks)

### Week 1 – Foundation
| Day | Task | Owner |
|-----|------|-------|
| 1-2 | Repo setup, Flask skeleton, CORS, health API | Backend |
| 3-4 | React + Vite + Tailwind, layout, Header | Frontend |
| 5 | Audio upload UI + file validation | Frontend |
| 6-7 | Integrate upload endpoint, test with sample MP3 | Both |

### Week 2 – Speech-to-Text
| Day | Task |
|-----|------|
| 1-2 | Install Whisper + FFmpeg, `whisper_service` |
| 3-4 | `/api/transcribe`, loading states, transcript panel |
| 5-7 | Test Hindi/English lectures, tune model size |

### Week 3 – Generative AI (Notes)
| Day | Task |
|-----|------|
| 1 | Groq account, `.env`, `groq_service` |
| 2-3 | Notes prompt + `/api/generate/notes` |
| 4-5 | Markdown render (`react-markdown`) |
| 6-7 | PDF/TXT export service + download API |

### Week 4 – Quiz & Flashcards
| Day | Task |
|-----|------|
| 1-3 | Quiz prompt, JSON parse, QuizPanel + scoring |
| 4-6 | Flashcards prompt, flip UI |
| 7 | Error handling, empty states |

### Week 5 – Polish & Testing
| Day | Task |
|-----|------|
| 1-2 | UI polish, responsive mobile |
| 3-4 | Functional + API testing |
| 5-7 | Record demo video, fix bugs |

### Week 6 – Submission
| Day | Task |
|-----|------|
| 1-3 | PPT, report, architecture diagrams |
| 4-5 | Mentor rehearsal (demo script) |
| 6-7 | Final submission + README |

**Team roles (3 members):**
- **Member A:** Backend + Whisper + Groq
- **Member B:** Frontend + UX
- **Member C:** Testing + Documentation + PPT/Demo

---

## 12. Testing Plan

### Functional Testing

| ID | Test | Expected |
|----|------|----------|
| F1 | Upload valid MP3 | Transcript appears |
| F2 | Upload .txt file | 400 error |
| F3 | Generate notes | Markdown with headings |
| F4 | Generate quiz | 10 questions, submit shows score |
| F5 | Generate flashcards | Flip works, navigation works |
| F6 | Download PDF | Valid PDF opens |

### API Testing (curl / Postman)

```bash
curl http://localhost:5000/api/health
curl -X POST -F "audio=@lecture.mp3" http://localhost:5000/api/transcribe
curl -X POST -H "Content-Type: application/json" \
  -d "{\"transcript\":\"Sample lecture about stacks and queues.\"}" \
  http://localhost:5000/api/generate/notes
```

### UI Testing

- Chrome + Edge desktop
- Mobile viewport (375px): buttons stack, cards readable
- Loading spinners during long Whisper runs

---

## 13. Demo Flow (Mentor Presentation – 5 Minutes)

| Step | Action | What to Say |
|------|--------|-------------|
| 1 | Open `localhost:5173` | “This is LectureMind AI for students who miss notes in lectures.” |
| 2 | Upload 2–3 min sample lecture MP3 | “We support MP3, WAV, M4A up to 50 MB.” |
| 3 | Wait for transcript | “Whisper converts speech to text locally—no paid STT API.” |
| 4 | Click **Generate Notes** | “Groq Llama 3.3 creates exam-oriented structured notes.” |
| 5 | Click **Download PDF** | “Students can export for offline revision.” |
| 6 | Click **Generate Quiz** | “10 MCQs with instant scoring for self-assessment.” |
| 7 | Click **Generate Flashcards** | “Flip cards for spaced revision.” |
| 8 | Show architecture slide | “Simple Flask + React; free-tier Groq; no overengineering.” |

**Sample audio tip:** Use a clear 2-minute clip on one topic (e.g., “Introduction to Machine Learning”) for reliable demo timing.

---

## 14. PPT Structure (12–15 Slides)

1. **Title** – LectureMind AI, team names, internship logos  
2. **Problem Statement** – Listen vs write conflict, missed concepts  
3. **Existing Solutions** – Otter, Google Docs voice typing—no structured study pack  
4. **Proposed Solution** – One upload → transcript + notes + quiz + flashcards  
5. **Architecture** – ASCII/block diagram from Section 2  
6. **Technology Stack** – React, Flask, Whisper, Groq, Tailwind  
7. **Feature 1–2** – Upload + STT (screenshot)  
8. **Feature 3–4** – Notes + Quiz (screenshot)  
9. **Feature 5–6** – Flashcards + Download  
10. **AI Pipeline** – Input → Whisper → Groq → Output table  
11. **Demo** – Embedded video or live  
12. **Results** – Sample output, time saved, quiz score demo  
13. **Future Scope** – User accounts, Hindi UI, teacher dashboard (no RAG in scope)  
14. **Conclusion** – Impact on student learning  
15. **Thank You / Q&A**

---

## 15. Resume Description

### Resume Bullet Points

- Built **LectureMind AI**, a full-stack lecture assistant using **React**, **Flask**, **OpenAI Whisper**, and **Groq Llama 3.3** to convert audio into transcripts, structured notes, MCQ quizzes, and flashcards.  
- Designed REST APIs and prompt templates for **exam-oriented note generation** and **JSON-validated quiz output** with 10 MCQs and automated scoring UI.  
- Implemented **PDF/TXT export** and session-based processing pipeline; demonstrated end-to-end AI workflow for **AICTE–IBM SkillsBuild** internship evaluation.

### LinkedIn Project Description

**LectureMind AI | Lecture Voice-to-Notes Generator**

Internship project for AICTE + Edunet Foundation + IBM SkillsBuild. LectureMind AI helps students turn lecture recordings into study-ready materials in minutes. Upload MP3/WAV/M4A audio, get a Whisper-powered transcript, then generate structured markdown notes, a 10-question MCQ quiz with explanations, and interactive flashcards using Groq’s Llama 3.3 70B model. Built with React, Tailwind CSS, Python Flask, and free-tier AI tools—designed to be simple, demonstrable, and production-minded without unnecessary complexity.

**Tech:** React · Vite · Tailwind · Python · Flask · Whisper · Groq · fpdf2

---

## AI Component Reference

| Component | Input | Processing | Model | Output |
|-----------|-------|------------|-------|--------|
| Speech-to-Text | Audio file | Whisper transcribe | `whisper-base` (local) | Plain text + segments |
| Summarization (Notes) | Transcript | Groq chat + prompt | `llama-3.3-70b-versatile` | Markdown notes |
| Quiz Generation | Transcript | Groq + JSON prompt | Same | 10 MCQs JSON |
| Flashcard Generation | Transcript | Groq + JSON prompt | Same | 15 Q/A JSON |
| Export | Markdown notes | fpdf2 / encode | N/A | PDF or TXT file |

---

## Evaluation Metrics (For Report)

| Category | Metric |
|----------|--------|
| STT | Word Error Rate (manual check on 1 sample) |
| Notes | Mentor rubric: structure, coverage, no hallucination |
| Quiz | 10/10 questions present, valid JSON |
| Performance | Transcribe 3 min audio &lt; 2 min on base model |
| UX | Task completion without help in demo |

---

*Document version 1.0 · LectureMind AI · Internship Submission*
