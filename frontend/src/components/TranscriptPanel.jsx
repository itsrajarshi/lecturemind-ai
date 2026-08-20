import { useState } from "react";

function wordCount(text) {
  return text.trim() ? text.trim().split(/\s+/).length : 0;
}

export default function TranscriptPanel({ transcript, language }) {
  const [copied, setCopied] = useState(false);

  if (!transcript) return null;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(transcript);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* Clipboard API unavailable — ignore. */
    }
  };

  const words = wordCount(transcript);
  const minutes = Math.round((transcript.length / 800) * 10) / 10;

  return (
    <section aria-labelledby="transcript-heading" className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 id="transcript-heading" className="text-lg font-semibold text-slate-800">
          Transcript
        </h2>
        <div className="flex items-center gap-2">
          {language && (
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
              {language.toUpperCase()}
            </span>
          )}
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-500">
            {words} words
          </span>
          <button
            type="button"
            onClick={copy}
            className="rounded-lg border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
          >
            {copied ? "Copied ✓" : "Copy"}
          </button>
        </div>
      </div>
      <div className="max-h-64 overflow-y-auto rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">
        {transcript}
      </div>
      {minutes > 0 && (
        <p className="mt-2 text-xs text-slate-400">Estimated reading time: ~{minutes} min</p>
      )}
    </section>
  );
}