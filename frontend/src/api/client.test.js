import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { validateFile, downloadNotes, MAX_FILE_SIZE } from "./client";

function makeFile(name, { size = 100, type = "audio/mpeg" } = {}) {
  return new File([new Uint8Array(size)], name, { type });
}

describe("validateFile", () => {
  it("accepts a valid mp3 file", () => {
    expect(validateFile(makeFile("lecture.mp3"))).toBeNull();
  });

  it("accepts a valid wav file", () => {
    expect(validateFile(makeFile("lecture.wav", { type: "audio/wav" }))).toBeNull();
  });

  it("accepts a valid m4a file by extension even without mime type", () => {
    expect(validateFile(makeFile("lecture.m4a", { type: "" }))).toBeNull();
  });

  it("rejects an unsupported extension", () => {
    expect(validateFile(makeFile("notes.pdf", { type: "" }))).toMatch(/Unsupported file type/);
  });

  it("rejects an empty file", () => {
    expect(validateFile(makeFile("empty.mp3", { size: 0 }))).toMatch(/empty/);
  });

  it("rejects an oversized file", () => {
    expect(validateFile(makeFile("big.mp3", { size: MAX_FILE_SIZE + 1 }))).toMatch(/too large/);
  });

  it("rejects a missing file", () => {
    expect(validateFile(null)).toMatch(/No file/);
  });
});

describe("downloadNotes", () => {
  let originalCreateObjectURL;
  let originalRevokeObjectURL;

  beforeEach(() => {
    originalCreateObjectURL = URL.createObjectURL;
    originalRevokeObjectURL = URL.revokeObjectURL;
    URL.createObjectURL = vi.fn(() => "blob:test");
    URL.revokeObjectURL = vi.fn();
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        headers: new Headers({ "content-type": "text/plain" }),
        blob: () => Promise.resolve(new Blob(["notes"], { type: "text/plain" })),
      }),
    );
    vi.useFakeTimers();
  });

  afterEach(() => {
    URL.createObjectURL = originalCreateObjectURL;
    URL.revokeObjectURL = originalRevokeObjectURL;
    global.fetch = undefined;
    vi.useRealTimers();
  });

  it("creates a download link and defers object URL revocation", async () => {
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    await downloadNotes("# Notes", "txt", "My Title");

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/download/notes",
      expect.objectContaining({ method: "POST" }),
    );
    expect(clickSpy).toHaveBeenCalled();
    expect(URL.revokeObjectURL).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1100);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test");
    clickSpy.mockRestore();
  });

  it("maps a backend error message onto a thrown Error", async () => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: false,
        status: 400,
        headers: new Headers({ "content-type": "application/json" }),
        json: () => Promise.resolve({ error: "Notes content required" }),
      }),
    );

    await expect(downloadNotes("", "txt")).rejects.toThrow("Notes content required");
  });

  it("maps network failures to a friendly message", async () => {
    global.fetch = vi.fn(() => Promise.reject(new TypeError("Failed to fetch")));
    await expect(downloadNotes("x", "txt")).rejects.toThrow(/Network error/);
  });
});