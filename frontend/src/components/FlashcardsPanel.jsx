import { useCallback, useEffect, useState } from "react";

function shuffle(arr) {
  const copy = [...arr];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

export default function FlashcardsPanel({ deck, loading }) {
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [cards, setCards] = useState([]);

  // Sync local cards and reset navigation whenever a new deck arrives.
  useEffect(() => {
    setCards(deck?.flashcards || []);
    setIndex(0);
    setFlipped(false);
  }, [deck]);

  const card = cards[index];

  const next = useCallback(() => {
    setFlipped(false);
    setIndex((i) => (i + 1) % Math.max(cards.length, 1));
  }, [cards.length]);

  const prev = useCallback(() => {
    setFlipped(false);
    setIndex((i) => (i - 1 + cards.length) % Math.max(cards.length, 1));
  }, [cards.length]);

  useEffect(() => {
    const onKey = (e) => {
      if (!cards.length) return;
      if (e.key === "ArrowRight") next();
      if (e.key === "ArrowLeft") prev();
      if (e.key === " " || e.key === "Enter") {
        e.preventDefault();
        setFlipped((f) => !f);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cards.length, next, prev]);

  if (!deck && !loading) return null;

  return (
    <section aria-labelledby="flashcards-heading" className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 id="flashcards-heading" className="text-lg font-semibold text-slate-800">
          {loading ? "Generating Flashcards…" : deck?.deck_title || "Flashcards"}
        </h2>
        {!loading && cards.length > 0 && (
          <button
            type="button"
            onClick={() => {
              setFlipped(false);
              setIndex(0);
              setCards(shuffle(cards));
            }}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
          >
            Shuffle
          </button>
        )}
      </div>
      {loading ? (
        <div aria-live="polite" className="flex h-48 animate-pulse items-center justify-center rounded-2xl bg-slate-100">
          <span className="text-sm text-slate-400">Preparing your flashcards…</span>
        </div>
      ) : (
        card && (
          <>
            <button
              type="button"
              onClick={() => setFlipped((f) => !f)}
              aria-label={flipped ? "Show question" : "Show answer"}
              className="mb-4 flex min-h-[160px] w-full flex-col items-center justify-center rounded-2xl bg-gradient-to-br from-brand-600 to-brand-800 p-6 text-center text-white shadow-lg transition hover:scale-[1.01] focus-visible:ring-2 focus-visible:ring-brand-300"
            >
              <span className="mb-2 text-xs uppercase tracking-wide opacity-80">
                {flipped ? "Answer" : "Question"} · {index + 1}/{cards.length}
              </span>
              <p className="text-lg font-medium">{flipped ? card.answer : card.question}</p>
              <span className="mt-3 text-xs opacity-70">Click or press Space to flip</span>
            </button>
            <div className="flex items-center justify-between gap-2">
              <button
                type="button"
                onClick={prev}
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
              >
                ← Previous
              </button>
              <span className="text-xs text-slate-400">Arrow keys navigate</span>
              <button
                type="button"
                onClick={next}
                className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-brand-700"
              >
                Next →
              </button>
            </div>
          </>
        )
      )}
    </section>
  );
}