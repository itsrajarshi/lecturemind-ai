const ACCEPT = ".mp3,.wav,.m4a,audio/mpeg,audio/wav,audio/x-m4a";

export default function AudioUploader({ onUpload, loading, disabled }) {
  const handleChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
  };

  return (
    <section className="rounded-2xl border-2 border-dashed border-brand-300 bg-white p-8 text-center shadow-sm">
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-3xl">
        🎙️
      </div>
      <h2 className="text-lg font-semibold text-slate-800">Upload Lecture Audio</h2>
      <p className="mt-1 text-sm text-slate-500">MP3, WAV, or M4A · Max 50 MB</p>
      <label
        className={`mt-6 inline-flex cursor-pointer items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white transition ${
          disabled || loading
            ? "cursor-not-allowed bg-slate-400"
            : "bg-brand-600 hover:bg-brand-700"
        }`}
      >
        {loading ? "Transcribing..." : "Choose Audio File"}
        <input
          type="file"
          accept={ACCEPT}
          className="hidden"
          disabled={disabled || loading}
          onChange={handleChange}
        />
      </label>
    </section>
  );
}
