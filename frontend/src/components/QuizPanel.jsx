import { useState } from "react";

export default function QuizPanel({ quiz, loading }) {
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);

  if (!quiz && !loading) return null;

  const questions = quiz?.questions || [];

  const score = submitted
    ? questions.filter((q) => answers[q.id] === q.correct_answer).length
    : 0;

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">
        {loading ? "Generating Quiz..." : quiz?.quiz_title || "Practice Quiz"}
      </h2>
      {!loading &&
        questions.map((q) => (
          <div key={q.id} className="mb-6 border-b border-slate-100 pb-4 last:border-0">
            <p className="mb-2 font-medium text-slate-800">
              {q.id}. {q.question}
              <span className="ml-2 text-xs text-slate-400">({q.difficulty})</span>
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {Object.entries(q.options).map(([key, val]) => {
                let cls =
                  "rounded-lg border px-3 py-2 text-left text-sm transition ";
                if (submitted) {
                  if (key === q.correct_answer)
                    cls += "border-green-500 bg-green-50 text-green-800";
                  else if (answers[q.id] === key)
                    cls += "border-red-400 bg-red-50 text-red-800";
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
                    className={cls}
                    onClick={() => setAnswers((a) => ({ ...a, [q.id]: key }))}
                  >
                    <span className="font-semibold">{key}.</span> {val}
                  </button>
                );
              })}
            </div>
            {submitted && (
              <p className="mt-2 text-xs text-slate-500">{q.explanation}</p>
            )}
          </div>
        ))}
      {!loading && questions.length > 0 && (
        <div className="flex items-center gap-4">
          {!submitted ? (
            <button
              type="button"
              onClick={() => setSubmitted(true)}
              className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-semibold text-white hover:bg-brand-700"
            >
              Submit Quiz
            </button>
          ) : (
            <p className="text-sm font-semibold text-brand-700">
              Score: {score} / {questions.length}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
