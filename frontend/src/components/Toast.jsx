import { useEffect } from "react";

export default function Toast({ toast, onDismiss }) {
  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(onDismiss, 6000);
    return () => clearTimeout(timer);
  }, [toast, onDismiss]);

  if (!toast) return null;

  const tone = toast.type === "error" ? "border-red-200 bg-red-50 text-red-800" : "border-green-200 bg-green-50 text-green-800";

  return (
    <div
      role="status"
      aria-live="polite"
      className={`fixed bottom-6 right-6 z-[60] flex max-w-sm items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg ${tone}`}
    >
      <span className="mt-0.5">{toast.type === "error" ? "⚠️" : "✓"}</span>
      <span className="flex-1">{toast.message}</span>
      <button
        type="button"
        onClick={onDismiss}
        aria-label="Dismiss notification"
        className="text-slate-400 transition hover:text-slate-600"
      >
        ✕
      </button>
    </div>
  );
}