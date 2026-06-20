NOTES_PROMPT = """You are an expert academic note-taker for university students.

Convert the following lecture transcript into structured, exam-oriented study notes.

Requirements:
- Use clear markdown headings (##, ###)
- Use bullet points for key ideas
- Bold **important terms**, definitions, and formulas
- Group content by topic
- Add a short "Key Takeaways" section at the end (5-7 bullets)
- Keep language concise and student-friendly
- Do NOT invent facts not present in the transcript

Lecture transcript:
---
{transcript}
---

Output only the formatted notes in markdown."""


QUIZ_PROMPT = """You are an exam paper setter for university courses.

Based ONLY on the lecture transcript below, create exactly 10 multiple-choice questions.

Requirements:
- Each question must have exactly 4 options labeled A, B, C, D
- Mark the correct option
- Mix difficulty: 4 easy, 4 medium, 2 hard
- Questions must be answerable from the transcript only
- Return valid JSON only, no markdown fences

JSON schema:
{{
  "quiz_title": "string",
  "questions": [
    {{
      "id": 1,
      "question": "string",
      "options": {{ "A": "string", "B": "string", "C": "string", "D": "string" }},
      "correct_answer": "A",
      "difficulty": "easy|medium|hard",
      "explanation": "one sentence why the answer is correct"
    }}
  ]
}}

Lecture transcript:
---
{transcript}
---"""


FLASHCARDS_PROMPT = """You are a revision coach creating flashcards for spaced repetition study.

From the lecture transcript below, generate exactly 15 flashcards.

Requirements:
- Each card: clear question on front, concise answer on back
- Cover definitions, concepts, comparisons, and "why/how" questions
- Answers should be 1-3 sentences max
- Return valid JSON only, no markdown fences

JSON schema:
{{
  "deck_title": "string",
  "flashcards": [
    {{ "id": 1, "question": "string", "answer": "string" }}
  ]
}}

Lecture transcript:
---
{transcript}
---"""
