import ReactMarkdown from "react-markdown";

export default function NotesPanel({ notes, onDownloadTxt, onDownloadPdf, loading }) {
  if (!notes && !loading) return null;

  return (
    <section className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold text-slate-800">Study Notes</h2>
        {notes && (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onDownloadTxt}
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:bg-slate-50"
            >
              Download TXT
            </button>
            <button
              type="button"
              onClick={onDownloadPdf}
              className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-brand-700"
            >
              Download PDF
            </button>
          </div>
        )}
      </div>
      {loading ? (
        <p className="text-sm text-slate-500">Generating notes...</p>
      ) : (
        <div className="prose-notes max-h-96 overflow-y-auto text-sm">
          <ReactMarkdown>{notes}</ReactMarkdown>
        </div>
      )}
    </section>
  );
}
