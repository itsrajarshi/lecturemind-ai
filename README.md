# LectureMind AI – Lecture Voice-to-Notes Generator

AICTE · Edunet Foundation · IBM SkillsBuild AI Internship Project

Convert lecture audio into transcripts, structured notes, quizzes, and flashcards using **Groq Whisper** and **Groq (Llama 3.3 70B)**.

## Live Demo

**https://lecturemind-ai.onrender.com**

## Quick Start (Local)

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Groq API key](https://console.groq.com/) (free tier)

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env and set GROQ_API_KEY
python app.py
```

Server runs at `http://localhost:5000`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

## Deploy on Render (Free)

One URL serves both the React UI and Flask API.

### 1. Push to GitHub

Make sure your code is on GitHub (public repo for internship submission).

### 2. Create a Render account

Sign up at [render.com](https://render.com) and connect your GitHub account.

### 3. Deploy with Blueprint

1. In Render, click **New +** → **Blueprint**
2. Connect the `lecturemind-ai` repository
3. Render reads `render.yaml` from the repo root
4. When prompted, set **`GROQ_API_KEY`** to your [Groq API key](https://console.groq.com/)
5. Click **Apply** and wait for the build (~3–5 minutes)

Your app will be live at `https://<service-name>.onrender.com`.

### Manual setup (alternative)

If you prefer not to use Blueprint:

| Setting | Value |
|---------|--------|
| **Root Directory** | `backend` |
| **Runtime** | Python 3 |
| **Build Command** | `bash render-build.sh` |
| **Start Command** | `gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120 --workers 1` |
| **Environment** | `GROQ_API_KEY` = your key, `NODE_VERSION` = `20` |

### Free tier notes

- The service **sleeps after ~15 minutes** of inactivity. The first visit after that may take **30–60 seconds** to wake up — open the link once before a demo.
- Audio and sessions are stored in memory / ephemeral disk and reset on redeploy.

### What gets submitted

| Field | Example |
|-------|---------|
| GitHub | `https://github.com/itsrajarshi/lecturemind-ai` |
| Live demo | `https://lecturemind-ai.onrender.com` |

## Features

| Feature | Technology |
|---------|------------|
| Audio upload (MP3/WAV/M4A) | React + Flask |
| Speech-to-text | Groq Whisper (`whisper-large-v3`) |
| Notes, Quiz, Flashcards | Groq `llama-3.3-70b-versatile` |
| Download notes | TXT / PDF |

## Project Structure

See [PROJECT_DOCUMENTATION.md](./PROJECT_DOCUMENTATION.md) for full architecture, API spec, prompts, demo flow, and internship submission materials.

## License

MIT – for educational internship use
