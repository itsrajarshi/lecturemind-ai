import { useState } from "react";

export default function FlashcardsPanel({ deck, loading }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  if (!deck && !loading) return null;

  const cards = deck?.flashcards || [];
  const card = cards[index];

  const next = () => {
    setFlipped(false);
    setIndex((i) => (i + 1) % cards.length);
  };

  const prev = () => {
    setFlipped(false);
    setIndex((i) => (i - 1 + cards.length) % cards.length);
  };

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h2 className="mb-4 text-lg font-semibold text-slate-800">
        {loading ? "Generating Flashcards..." : deck?.deck_title || "Flashcards"}
      </h2>
      {!loading && card && (
        <>
          <button
            type="button"
            onClick={() => setFlipped((f) => !f)}
            className="mb-4 flex min-h-[160px] w-full flex-col items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 p-6 text-center text-white shadow-lg transition hover:scale-[1.01]"
          >
            <span className="mb-2 text-xs uppercase tracking-wide opacity-80">
              {flipped ? "Answer" : "Question"} · {index + 1}/{cards.length}
            </span>
            <p className="text-lg font-medium">
              {flipped ? card.answer : card.question}
            </p>
            <span className="mt-3 text-xs opacity-70">Tap to flip</span>
          </button>
          <div className="flex justify-between gap-2">
            <button
              type="button"
              onClick={prev}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
            >
              Previous
            </button>
            <button
              type="button"
              onClick={next}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700"
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
