export default function TranscriptPanel({ transcript, language }) {
  if (!transcript) return null;

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Transcript</h2>
        {language && (
          <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs text-slate-600">
            {language.toUpperCase()}
          </span>
        )}
      </div>
      <div className="max-h-64 overflow-y-auto rounded-lg bg-slate-50 p-4 text-sm leading-relaxed text-slate-700">
        {transcript}
      </div>
    </section>
  );
}
