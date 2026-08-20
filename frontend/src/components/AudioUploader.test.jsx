import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import AudioUploader from "./AudioUploader";

function makeFile(name, { size = 100, type = "audio/mpeg" } = {}) {
  return new File([new Uint8Array(size)], name, { type });
}

describe("AudioUploader", () => {
  it("calls onUpload with a valid file", () => {
    const onUpload = vi.fn();
    render(<AudioUploader onUpload={onUpload} loading={false} disabled={false} />);

    const input = screen.getByLabelText("Choose Audio File");
    const file = makeFile("lecture.mp3");
    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).toHaveBeenCalledWith(file);
    expect(screen.getByText("lecture.mp3")).toBeInTheDocument();
  });

  it("rejects an invalid file client-side without calling onUpload", () => {
    const onUpload = vi.fn();
    render(<AudioUploader onUpload={onUpload} loading={false} disabled={false} />);

    const input = screen.getByLabelText("Choose Audio File");
    const file = makeFile("notes.pdf", { type: "" });
    fireEvent.change(input, { target: { files: [file] } });

    expect(onUpload).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Unsupported file type/);
  });

  it("handles drag-and-drop files", () => {
    const onUpload = vi.fn();
    render(<AudioUploader onUpload={onUpload} loading={false} disabled={false} />);

    const section = screen.getByLabelText("Upload lecture audio");
    const file = makeFile("dropped.wav", { type: "audio/wav" });
    fireEvent.drop(section, { dataTransfer: { files: [file] } });

    expect(onUpload).toHaveBeenCalledWith(file);
  });

  it("disables input while loading", () => {
    render(<AudioUploader onUpload={vi.fn()} loading disabled={false} />);
    expect(screen.getByLabelText(/Transcribing/)).toBeDisabled();
    expect(screen.getByText(/Transcribing/)).toBeInTheDocument();
  });
});