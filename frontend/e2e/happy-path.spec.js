import { test, expect } from "@playwright/test";

const TRANSCRIPT =
  "Machine learning is the study of algorithms that improve with experience. " +
  "Supervised learning uses labeled data. Neural networks are composed of layers of neurons.";

const QUIZ = {
  quiz_title: "Machine Learning Quiz",
  questions: [
    {
      id: 1,
      question: "What does supervised learning use?",
      options: { A: "No data", B: "Labeled data", C: "Random data", D: "Unlabeled data" },
      correct_answer: "B",
      difficulty: "easy",
      explanation: "Supervised learning trains on labeled examples.",
    },
  ],
};

const DECK = {
  deck_title: "Revision Deck",
  flashcards: [
    { id: 1, question: "What is supervised learning?", answer: "Learning from labeled data." },
  ],
};

// The E2E suite stubs the AI backends so it runs deterministically without a
// real API key. Backend integration is covered by the pytest suite.
async function stubApi(page) {
  await page.route("**/api/transcribe", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        session_id: "test-session-123",
        transcript: TRANSCRIPT,
        language: "en",
        segments: [{ start: 0, end: 5, text: TRANSCRIPT }],
      }),
    }),
  );
  await page.route("**/api/generate/notes", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        notes: "## Key Takeaways\n\n- Machine learning improves with experience",
        format: "markdown",
      }),
    }),
  );
  await page.route("**/api/generate/quiz", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(QUIZ) }),
  );
  await page.route("**/api/generate/flashcards", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(DECK) }),
  );
  await page.route("**/api/download/notes", (route) =>
    route.fulfill({
      status: 200,
      contentType: "text/plain",
      body: "Lecture Notes\n============\n\n# Key Takeaways",
    }),
  );
}

test("full pipeline: upload → transcript → notes → quiz → flashcards → download", async ({ page }) => {
  await stubApi(page);
  await page.goto("/");

  await expect(page.getByRole("heading", { name: /Turn lecture audio/ })).toBeVisible();

  // Upload
  await page.setInputFiles('input[type="file"]', {
    name: "lecture.mp3",
    mimeType: "audio/mpeg",
    buffer: Buffer.from("ID3fakeaudiocontent"),
  });

  // Transcript appears after transcription
  await expect(page.getByText(/Machine learning is the study of algorithms/)).toBeVisible();

  // Generate notes
  await page.getByRole("button", { name: "Generate Notes" }).click();
  await expect(page.getByRole("heading", { name: "Study Notes" })).toBeVisible();
  await expect(page.getByText(/Machine learning improves with experience/)).toBeVisible();

  // Generate quiz and answer it
  await page.getByRole("button", { name: "Generate Quiz" }).click();
  await expect(page.getByRole("heading", { name: "Machine Learning Quiz" })).toBeVisible();
  await page.getByRole("button", { name: /B\. Labeled data/ }).click();
  await page.getByRole("button", { name: "Submit Quiz" }).click();
  await expect(page.getByText(/Score: 1\/1/)).toBeVisible();

  // Generate flashcards and flip
  await page.getByRole("button", { name: "Generate Flashcards" }).click();
  await expect(page.getByText(/What is supervised learning/)).toBeVisible();
  await page.getByRole("button", { name: "Show answer" }).click();
  await expect(page.getByText(/Learning from labeled data/)).toBeVisible();

  // Download notes (TXT)
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download TXT" }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe("lecture_notes.txt");
});

test("shows a friendly error when transcription fails", async ({ page }) => {
  await page.route("**/api/transcribe", (route) =>
    route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ error: "Something went wrong. Please try again." }),
    }),
  );
  await page.goto("/");

  await page.setInputFiles('input[type="file"]', {
    name: "lecture.mp3",
    mimeType: "audio/mpeg",
    buffer: Buffer.from("ID3fakeaudiocontent"),
  });

  await expect(page.getByText(/Something went wrong/).first()).toBeVisible();
});