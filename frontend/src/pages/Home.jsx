import { useState } from "react";
import {
  downloadNotes,
  generateFlashcards,
  generateNotes,
  generateQuiz,
  transcribeAudio,
} from "../api/client";
import AudioUploader from "../components/AudioUploader";
import FlashcardsPanel from "../components/FlashcardsPanel";
import Footer from "../components/Footer";
import Header from "../components/Header";
import LoadingSpinner from "../components/LoadingSpinner";
import NotesPanel from "../components/NotesPanel";
import QuizPanel from "../components/QuizPanel";
import TranscriptPanel from "../components/TranscriptPanel";

export default function Home() {
  const [sessionId, setSessionId] = useState("");
  const [transcript, setTranscript] = useState("");
  const [language, setLanguage] = useState("");
  const [notes, setNotes] = useState("");
  const [quiz, setQuiz] = useState(null);
  const [flashcards, setFlashcards] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState({
    transcribe: false,
    notes: false,
    quiz: false,
    flashcards: false,
  });

  const hasTranscript = Boolean(transcript);

  const handleUpload = async (file) => {
    setError("");
    setNotes("");
    setQuiz(null);
    setFlashcards(null);
    setLoading((l) => ({ ...l, transcribe: true }));
    try {
      const data = await transcribeAudio(file);
      setSessionId(data.session_id);
      setTranscript(data.transcript);
      setLanguage(data.language);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading((l) => ({ ...l, transcribe: false }));
    }
  };

  const runGenerate = async (type) => {
    setError("");
    setLoading((l) => ({ ...l, [type]: true }));
    try {
      if (type === "notes") {
        const data = await generateNotes(sessionId, transcript);
        setNotes(data.notes);
      } else if (type === "quiz") {
        const data = await generateQuiz(sessionId, transcript);
        setQuiz(data);
      } else {
        const data = await generateFlashcards(sessionId, transcript);
        setFlashcards(data);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading((l) => ({ ...l, [type]: false }));
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-8">
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <AudioUploader
          onUpload={handleUpload}
          loading={loading.transcribe}
          disabled={loading.transcribe}
        />

        {loading.transcribe && (
          <LoadingSpinner label="Whisper is transcribing your lecture..." />
        )}

        <TranscriptPanel transcript={transcript} language={language} />

        {hasTranscript && (
          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={loading.notes}
              onClick={() => runGenerate("notes")}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-brand-700 disabled:bg-slate-400"
            >
              Generate Notes
            </button>
            <button
              type="button"
              disabled={loading.quiz}
              onClick={() => runGenerate("quiz")}
              className="rounded-xl border border-brand-600 px-5 py-2.5 text-sm font-semibold text-brand-700 hover:bg-brand-50 disabled:opacity-50"
            >
              Generate Quiz
            </button>
            <button
              type="button"
              disabled={loading.flashcards}
              onClick={() => runGenerate("flashcards")}
              className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 hover:bg-slate-100 disabled:opacity-50"
            >
              Generate Flashcards
            </button>
          </div>
        )}

        <NotesPanel
          notes={notes}
          loading={loading.notes}
          onDownloadTxt={() => downloadNotes(notes, "txt")}
          onDownloadPdf={() => downloadNotes(notes, "pdf")}
        />
        <QuizPanel quiz={quiz} loading={loading.quiz} />
        <FlashcardsPanel deck={flashcards} loading={loading.flashcards} />
      </main>
      <Footer />
    </div>
  );
}
