import { useCallback, useState } from "react";
import {
  downloadNotes,
  generateFlashcards,
  generateNotes,
  generateQuiz,
  transcribeAudio,
  validateFile,
} from "../api/client";
import AudioUploader from "../components/AudioUploader";
import FlashcardsPanel from "../components/FlashcardsPanel";
import Footer from "../components/Footer";
import Header from "../components/Header";
import NotesPanel from "../components/NotesPanel";
import QuizPanel from "../components/QuizPanel";
import Stepper from "../components/Stepper";
import Toast from "../components/Toast";
import TranscriptPanel from "../components/TranscriptPanel";

const EMPTY_LOADING = { transcribe: false, notes: false, quiz: false, flashcards: false };

export default function Home() {
  const [sessionId, setSessionId] = useState("");
  const [transcript, setTranscript] = useState("");
  const [language, setLanguage] = useState("");
  const [fileName, setFileName] = useState("");
  const [notes, setNotes] = useState("");
  const [quiz, setQuiz] = useState(null);
  const [flashcards, setFlashcards] = useState(null);
  const [error, setError] = useState("");
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(EMPTY_LOADING);
  const [generated, setGenerated] = useState({ notes: false, quiz: false, flashcards: false });

  const showToast = useCallback((message, type = "error") => {
    setToast({ message, type });
  }, []);

  const dismissToast = useCallback(() => setToast(null), []);

  const stage = !transcript
    ? loading.transcribe
      ? "transcribe"
      : "upload"
    : generated.notes && generated.quiz && generated.flashcards
      ? "complete"
      : "generate";

  const resetResults = () => {
    setNotes("");
    setQuiz(null);
    setFlashcards(null);
    setGenerated({ notes: false, quiz: false, flashcards: false });
  };

  const handleUpload = useCallback(
    async (file) => {
      const validationError = validateFile(file);
      if (validationError) {
        showToast(validationError);
        return;
      }
      setError("");
      resetResults();
      setFileName(file.name);
      setTranscript("");
      setSessionId("");
      setLanguage("");
      setLoading((l) => ({ ...l, transcribe: true }));
      try {
        const data = await transcribeAudio(file);
        setSessionId(data.session_id);
        setTranscript(data.transcript);
        setLanguage(data.language);
        setError("");
      } catch (e) {
        setError(e.message);
        showToast(e.message);
      } finally {
        setLoading((l) => ({ ...l, transcribe: false }));
      }
    },
    [showToast],
  );

  const runGenerate = useCallback(
    async (type) => {
      if (!transcript || generated[type] || loading[type]) return;
      setError("");
      setLoading((l) => ({ ...l, [type]: true }));
      try {
        if (type === "notes") {
          const data = await generateNotes(sessionId, transcript);
          setNotes(data.notes);
          showToast("Study notes ready ✓", "success");
        } else if (type === "quiz") {
          const data = await generateQuiz(sessionId, transcript);
          setQuiz(data);
          showToast("Practice quiz ready ✓", "success");
        } else {
          const data = await generateFlashcards(sessionId, transcript);
          setFlashcards(data);
          showToast("Flashcards ready ✓", "success");
        }
        setGenerated((g) => ({ ...g, [type]: true }));
      } catch (e) {
        setError(e.message);
        showToast(e.message);
      } finally {
        setLoading((l) => ({ ...l, [type]: false }));
      }
    },
    [transcript, sessionId, generated, loading, showToast],
  );

  const hasTranscript = Boolean(transcript);
  const busy = Object.values(loading).some(Boolean);

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main id="main" tabIndex={-1} className="mx-auto w-full max-w-6xl flex-1 space-y-6 px-4 py-8 outline-none">
        <section className="text-center">
          <h2 className="text-2xl font-bold text-slate-900 sm:text-3xl">
            Turn lecture audio into study-ready notes
          </h2>
          <p className="mx-auto mt-2 max-w-2xl text-sm text-slate-500 sm:text-base">
            Upload a lecture recording and LectureMind AI generates a transcript,
            structured notes, a practice quiz, and flashcards — powered by Whisper and Groq.
          </p>
        </section>

        <Stepper stage={stage} />

        {error && (
          <div role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        <AudioUploader
          onUpload={handleUpload}
          loading={loading.transcribe}
          disabled={busy}
        />

        <TranscriptPanel transcript={transcript} language={language} />

        {hasTranscript && (
          <div className="flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              disabled={loading.notes || generated.notes}
              onClick={() => runGenerate("notes")}
              className="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:bg-slate-400"
            >
              {loading.notes ? "Generating…" : generated.notes ? "Notes ready ✓" : "Generate Notes"}
            </button>
            <button
              type="button"
              disabled={loading.quiz || generated.quiz}
              onClick={() => runGenerate("quiz")}
              className="rounded-xl border border-brand-600 px-5 py-2.5 text-sm font-semibold text-brand-700 transition hover:bg-brand-50 disabled:opacity-50"
            >
              {loading.quiz ? "Generating…" : generated.quiz ? "Quiz ready ✓" : "Generate Quiz"}
            </button>
            <button
              type="button"
              disabled={loading.flashcards || generated.flashcards}
              onClick={() => runGenerate("flashcards")}
              className="rounded-xl border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:opacity-50"
            >
              {loading.flashcards
                ? "Generating…"
                : generated.flashcards
                  ? "Flashcards ready ✓"
                  : "Generate Flashcards"}
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
      <Toast toast={toast} onDismiss={dismissToast} />
    </div>
  );
}