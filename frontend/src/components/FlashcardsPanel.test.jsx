import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FlashcardsPanel from "./FlashcardsPanel";

const deck = {
  deck_title: "Revision Deck",
  flashcards: [
    { id: 1, question: "Q1?", answer: "A1" },
    { id: 2, question: "Q2?", answer: "A2" },
    { id: 3, question: "Q3?", answer: "A3" },
  ],
};

describe("FlashcardsPanel", () => {
  it("shows nothing when there is no deck and not loading", () => {
    const { container } = render(<FlashcardsPanel deck={null} loading={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the first question by default", () => {
    render(<FlashcardsPanel deck={deck} loading={false} />);
    expect(screen.getByText("Q1?")).toBeInTheDocument();
    expect(screen.getByText(/1\/3/)).toBeInTheDocument();
  });

  it("flips between question and answer", () => {
    render(<FlashcardsPanel deck={deck} loading={false} />);
    fireEvent.click(screen.getByRole("button", { name: /Show answer/ }));
    expect(screen.getByText("A1")).toBeInTheDocument();
    expect(screen.getByText(/Answer/)).toBeInTheDocument();
  });

  it("navigates forward and wraps around", () => {
    render(<FlashcardsPanel deck={deck} loading={false} />);
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("Q2?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("Q1?")).toBeInTheDocument();
  });

  it("resets to the first card when a new deck arrives", () => {
    const { rerender } = render(<FlashcardsPanel deck={deck} loading={false} />);
    fireEvent.click(screen.getByRole("button", { name: /Next/ }));
    expect(screen.getByText("Q2?")).toBeInTheDocument();

    const deck2 = { ...deck, flashcards: [deck.flashcards[0]] };
    rerender(<FlashcardsPanel deck={deck2} loading={false} />);
    expect(screen.getByText("Q1?")).toBeInTheDocument();
    expect(screen.getByText(/1\/1/)).toBeInTheDocument();
  });

  it("renders a loading state while generating", () => {
    render(<FlashcardsPanel deck={null} loading />);
    expect(screen.getByText("Generating Flashcards…")).toBeInTheDocument();
  });
});