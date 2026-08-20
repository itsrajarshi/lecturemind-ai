import { useEffect, useState } from "react";

export default function QuizPanel({ quiz, loading }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  // Reset answers when a new quiz arrives so stale selections cannot leak in.
  useEffect(() => {
    setAnswers({});
    setSubmitted(false);
  }, [quiz]);

  if (!quiz && !loading) return null;

  const questions = quiz?.questions || [];
  const answered = Object.keys(answers).length;
  const score = submitted
    ? questions.filter((q) => answers[q.id] === q.correct_answer).length
    : 0;

  const retake = () => {
    setAnswers({});
    setSubmitted(false);
  };

  return (
    <section aria-labelledby="quiz-heading" className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 id="quiz-heading" className="text-lg font-semibold text-slate-800">
          {loading ? "Generating Quiz…" : quiz?.quiz_title || "Practice Quiz"}
        </h2>
        {!loading && questions.length > 0 && (
          <div className="flex items-center gap-3 text-xs text-slate-500">
            <span aria-live="polite">
              {submitted ? `Score: ${score}/${questions.length}` : `${answered}/${questions.length} answered`}
            </span>
            <div className="h-1.5 w-24 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-brand-500 transition-all"
                style={{ width: `${(answered / Math.max(questions.length, 1)) * 100}%` }}
              />
            </div>
            {submitted && (
              <button
                type="button"
                onClick={retake}
                className="rounded-lg border border-slate-300 px-2.5 py-1 font-medium text-slate-600 transition hover:bg-slate-50"
              >
                Retake
              </button>
            )}
          </div>
        )}
      </div>
      {loading ? (
        <div aria-live="polite" className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-3/4 animate-pulse rounded bg-slate-200" />
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="h-8 animate-pulse rounded-lg bg-slate-100" />
                <div className="h-8 animate-pulse rounded-lg bg-slate-100" />
                <div className="h-8 animate-pulse rounded-lg bg-slate-100" />
                <div className="h-8 animate-pulse rounded-lg bg-slate-100" />
              </div>
            </div>
          ))}
        </div>
      ) : (
        questions.map((q) => (
          <div key={q.id} className="mb-6 border-b border-slate-100 pb-4 last:border-0">
            <p className="mb-2 font-medium text-slate-800">
              <span className="mr-1 text-slate-400">{q.id}.</span>
              {q.question}
              <span className="ml-2 text-xs text-slate-400">({q.difficulty})</span>
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(q.options).map(([key, val]) => {
                let cls = "rounded-lg border px-3 py-2 text-left text-sm transition ";
                if (submitted) {
                  if (key === q.correct_answer) cls += "border-green-500 bg-green-50 text-green-800";
                  else if (answers[q.id] === key) cls += "border-red-400 bg-red-50 text-red-800";
                  else cls += "border-slate-200 text-slate-600";
                } else if (answers[q.id] === key) {
                  cls += "border-brand-500 bg-brand-50";
                } else {
                  cls += "border-slate-200 hover:border-brand-300";
                }
                return (
                  <button
                    key={key}
                    type="button"
                    disabled={submitted}
                    aria-pressed={answers[q.id] === key}
                    className={cls}
                    onClick={() => setAnswers((a) => ({ ...a, [q.id]: key }))}
                  >
                    <span className="font-semibold">{key}.</span> {val}
                  </button>
                );
              })}
            </div>
            {submitted && <p className="mt-2 text-xs text-slate-500">{q.explanation}</p>}
          </div>
        ))
      )}
      {!loading && questions.length > 0 && !submitted && (
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={() => setSubmitted(true)}
            disabled={answered < questions.length}
            className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-slate-300"
          >
            {answered < questions.length
              ? `Answer all questions to submit (${answered}/${questions.length})`
              : "Submit Quiz"}
          </button>
        </div>
      )}
    </section>
  );
}