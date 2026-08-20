import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function NotesPanel({ notes, onDownloadTxt, onDownloadPdf, loading }) {
  const [collapsed, setCollapsed] = useState(false);

  if (!notes && !loading) return null;

  return (
    <section aria-labelledby="notes-heading" className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <h2 id="notes-heading" className="text-lg font-semibold text-slate-800">
          Study Notes
        </h2>
        <div className="flex flex-wrap gap-2">
          {notes && (
            <>
              <button
                type="button"
                onClick={() => setCollapsed((c) => !c)}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 transition hover:bg-slate-50"
              >
                {collapsed ? "Expand" : "Collapse"}
              </button>
              <button
                type="button"
                onClick={onDownloadTxt}
                className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-slate-50"
              >
                Download TXT
              </button>
              <button
                type="button"
                onClick={onDownloadPdf}
                className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-brand-700"
              >
                Download PDF
              </button>
            </>
          )}
        </div>
      </div>
      {loading ? (
        <div aria-live="polite" className="space-y-3">
          <div className="h-4 w-2/5 animate-pulse rounded bg-slate-200" />
          <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
          <div className="h-3 w-11/12 animate-pulse rounded bg-slate-100" />
          <div className="h-3 w-4/5 animate-pulse rounded bg-slate-100" />
        </div>
      ) : (
        <div
          className={`prose-notes overflow-y-auto text-sm transition-all ${collapsed ? "max-h-32 overflow-hidden" : "max-h-96"}`}
        >
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{notes}</ReactMarkdown>
        </div>
      )}
    </section>
  );
}