import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import QuizPanel from "./QuizPanel";

const quiz = {
  quiz_title: "Data Structures Quiz",
  questions: [
    {
      id: 1,
      question: "What is a stack?",
      options: { A: "FIFO", B: "LIFO", C: "Random", D: "Sorted" },
      correct_answer: "B",
      difficulty: "easy",
      explanation: "Stacks are LIFO.",
    },
    {
      id: 2,
      question: "What is a queue?",
      options: { A: "FIFO", B: "LIFO", C: "Random", D: "Sorted" },
      correct_answer: "A",
      difficulty: "easy",
      explanation: "Queues are FIFO.",
    },
  ],
};

function questionBlock(questionText) {
  const node = screen.getByText(questionText);
  return node.closest("div");
}

function pick(questionText, letter) {
  return within(questionBlock(questionText)).getByRole("button", {
    name: new RegExp(`^${letter}\\.`),
  });
}

describe("QuizPanel", () => {
  it("shows nothing when there is no quiz and not loading", () => {
    const { container } = render(<QuizPanel quiz={null} loading={false} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("renders questions and options", () => {
    render(<QuizPanel quiz={quiz} loading={false} />);
    expect(screen.getByText(/What is a stack/)).toBeInTheDocument();
    expect(screen.getByText(/What is a queue/)).toBeInTheDocument();
  });

  it("disables submit until all questions are answered", () => {
    render(<QuizPanel quiz={quiz} loading={false} />);
    const submit = screen.getByRole("button", { name: /Answer all questions/ });
    expect(submit).toBeDisabled();
  });

  it("scores answers correctly after submission", () => {
    render(<QuizPanel quiz={quiz} loading={false} />);

    fireEvent.click(pick("What is a stack?", "B"));
    fireEvent.click(pick("What is a queue?", "A"));

    const submit = screen.getByRole("button", { name: /Submit Quiz/ });
    expect(submit).not.toBeDisabled();
    fireEvent.click(submit);

    expect(screen.getByText(/Score: 2\/2/)).toBeInTheDocument();
    expect(screen.getByText(/Stacks are LIFO/)).toBeInTheDocument();
  });

  it("resets answers when a new quiz is provided", () => {
    const { rerender } = render(<QuizPanel quiz={quiz} loading={false} />);

    fireEvent.click(pick("What is a stack?", "B"));
    fireEvent.click(pick("What is a queue?", "A"));
    fireEvent.click(screen.getByRole("button", { name: /Submit Quiz/ }));
    expect(screen.getByText(/Score: 2\/2/)).toBeInTheDocument();

    const quiz2 = { ...quiz, questions: quiz.questions.slice(0, 1) };
    rerender(<QuizPanel quiz={quiz2} loading={false} />);

    expect(screen.queryByText(/Score: 2\/2/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Answer all questions/ })).toBeInTheDocument();
  });

  it("renders a loading skeleton while generating", () => {
    render(<QuizPanel quiz={null} loading />);
    expect(screen.getByText("Generating Quiz…")).toBeInTheDocument();
  });
});