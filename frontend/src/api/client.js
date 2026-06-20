const API_BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, options);
  const contentType = res.headers.get("content-type") || "";

  if (!res.ok) {
    let message = "Request failed";
    if (contentType.includes("application/json")) {
      const err = await res.json();
      message = err.error || message;
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
  return request("/transcribe", { method: "POST", body: form });
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
  a.click();
  URL.revokeObjectURL(url);
}
