import { useCallback, useRef, useState } from "react";
import { ACCEPTED_EXTENSIONS, MAX_FILE_SIZE, formatFileSize, validateFile } from "../api/client";

export default function AudioUploader({ onUpload, loading, disabled }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);
  const [fileInfo, setFileInfo] = useState(null);
  const [clientError, setClientError] = useState("");

  const handleFile = useCallback(
    (file) => {
      if (!file) return;
      const err = validateFile(file);
      if (err) {
        setClientError(err);
        setFileInfo(null);
        return;
      }
      setClientError("");
      setFileInfo({ name: file.name, size: file.size });
      onUpload(file);
    },
    [onUpload],
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled || loading) return;
    handleFile(e.dataTransfer.files?.[0]);
  };

  const onSelect = (e) => {
    const file = e.target.files?.[0];
    if (file) handleFile(file);
    e.target.value = "";
  };

  const active = disabled || loading;

  return (
    <section
      onDragOver={(e) => {
        e.preventDefault();
        if (!active) setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={onDrop}
      aria-label="Upload lecture audio"
      className={`rounded-2xl border-2 border-dashed p-8 text-center shadow-sm transition ${
        dragOver
          ? "border-brand-500 bg-brand-50"
          : "border-brand-300 bg-white"
      }`}
    >
      <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-brand-50 text-3xl" aria-hidden="true">
        🎙️
      </div>
      <h2 className="text-lg font-semibold text-slate-800">Upload Lecture Audio</h2>
      <p className="mt-1 text-sm text-slate-500">
        Drag &amp; drop or choose a file · MP3, WAV, or M4A · Max {Math.round(MAX_FILE_SIZE / (1024 * 1024))} MB
      </p>

      {fileInfo && !loading && (
        <p className="mt-3 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
          <span aria-hidden="true">📁</span>
          <span className="max-w-[220px] truncate">{fileInfo.name}</span>
          <span className="text-slate-400">{formatFileSize(fileInfo.size)}</span>
        </p>
      )}

      {clientError && (
        <p role="alert" className="mt-3 text-sm font-medium text-red-600">
          {clientError}
        </p>
      )}

      <label
        className={`mt-5 inline-flex cursor-pointer items-center gap-2 rounded-xl px-6 py-3 text-sm font-semibold text-white transition ${
          active ? "cursor-not-allowed bg-slate-400" : "bg-brand-600 hover:bg-brand-700"
        }`}
      >
        {loading ? "Transcribing…" : "Choose Audio File"}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_EXTENSIONS.map((e) => `.${e}`).join(",")}
          className="sr-only"
          disabled={active}
          onChange={onSelect}
        />
      </label>
    </section>
  );
}