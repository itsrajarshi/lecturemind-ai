export default function LoadingSpinner({ label = "Processing..." }) {
  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <div className="h-10 w-10 animate-spin rounded-full border-4 border-brand-200 border-t-brand-600" />
      <p className="text-sm text-slate-600">{label}</p>
    </div>
  );
}
