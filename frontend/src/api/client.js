const API_BASE = "/api";

export const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50 MB, matches the backend
export const ACCEPTED_EXTENSIONS = ["mp3", "wav", "m4a"];
export const ACCEPTED_MIME_TYPES = ["audio/mpeg", "audio/wav", "audio/x-wav", "audio/x-m4a", "audio/mp4"];

export function validateFile(file) {
  if (!file) return "No file selected.";
  const ext = file.name.split(".").pop()?.toLowerCase() || "";
  if (!ACCEPTED_EXTENSIONS.includes(ext) && !ACCEPTED_MIME_TYPES.includes(file.type)) {
    return "Unsupported file type. Please upload an MP3, WAV, or M4A file.";
  }
  if (file.size > MAX_FILE_SIZE) {
    return "File is too large. The maximum size is 50 MB.";
  }
  if (file.size === 0) {
    return "The file appears to be empty.";
  }
  return null;
}

async function request(path, options = {}, timeoutMs = 180000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, signal: controller.signal });
  } catch (err) {
    clearTimeout(timer);
    if (err.name === "AbortError") {
      throw new Error("The request timed out. Please try again.");
    }
    throw new Error("Network error. Please check your connection and try again.");
  }
  clearTimeout(timer);

  const contentType = res.headers.get("content-type") || "";

  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    if (contentType.includes("application/json")) {
      const body = await res.json().catch(() => null);
      if (body && body.error) message = body.error;
    }
    throw new Error(message);
  }

  if (contentType.includes("application/json")) {
    return res.json();
  }
  return res.blob();
}

export async function transcribeAudio(file) {
  const form = new FormData();
  form.append("audio", file);
  return request("/transcribe", { method: "POST", body: form }, 300000);
}

export async function generateNotes(sessionId, transcript) {
  return request("/generate/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Session-Id": sessionId },
    body: JSON.stringify({ session_id: sessionId, transcript }),
  });
}

export async function generateQuiz(sessionId, transcript) {
  return request("/generate/quiz", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Session-Id": sessionId },
    body: JSON.stringify({ session_id: sessionId, transcript }),
  });
}

export async function generateFlashcards(sessionId, transcript) {
  return request("/generate/flashcards", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Session-Id": sessionId },
    body: JSON.stringify({ session_id: sessionId, transcript }),
  });
}

export async function downloadNotes(notes, format = "txt", title = "Lecture Notes") {
  const blob = await request("/download/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes, format, title }),
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = format === "pdf" ? "lecture_notes.pdf" : "lecture_notes.txt";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Defer revocation so the browser has time to start the download.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function formatFileSize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}