# LectureMind AI — UI/UX Audit

> Review of the single-page interface: design language, the upload →
> transcribe → generate → export workflow, component inventory, the UX
> improvement pass with per-item implementation status, responsive behavior,
> accessibility notes, and honest remaining ideas. The improvement pass is
> part of the polish plan; statuses are marked per item. Related:
> `AUDIT_REPORT.md` (A13 panel-state residual), `PERFORMANCE_AUDIT.md`
> (bundle size), `ROADMAP.md` (P2 polish).

## 1. Design language

| Aspect | Choice | Notes |
|---|---|---|
| Primary color | Indigo brand scale (50–900; `600` = `#4f46e5`) | `tailwind.config.js`; CTAs, links, active states, spinner |
| Neutrals | Slate (bg `slate-50`, text `slate-900`, borders `slate-200`) | Calm, academic feel; high text/background contrast |
| Semantic accents | Green/red only in quiz feedback | Correct = green border + tint, wrong = red border + tint |
| Typography | Inter (Google Fonts) for all text | Preconnect hints in `index.html`; system-ui fallback |
| Layout | Single centered column, `max-w-6xl`, 16px gutters, cards (`rounded-2xl`, white, `shadow-sm`, `ring-1 ring-slate-200`) | One page, no router |
| Components | Rounded buttons, dashed upload zone, pill badges, sticky header/footer | Consistent radii/spacing via Tailwind utilities |
| Motion | Minimal — spinner, subtle flashcard hover scale | Global `prefers-reduced-motion` guard |

## 2. The single-page workflow

```
upload → transcribe → (session + transcript) → generate notes/quiz/flashcards → export
```

1. **Upload** — choose an audio file (MP3/WAV/M4A, ≤ 50 MB). The uploader
   communicates constraints up front ("MP3, WAV, or M4A · Max 50 MB").
2. **Transcribe** — `POST /api/transcribe`; the UI shows a spinner labeled
   "Whisper is transcribing your lecture...". Can take a minute on long
   files (the server is waiting on Groq, not local compute).
3. **Transcript** — a scrollable panel (internal `max-h`) with a detected-
   language badge; the transcript becomes the source of truth for generation.
4. **Generate** — three buttons ("Generate Notes / Quiz / Flashcards")
   appear only once a transcript exists. Each action has its own loading
   state, so results can be produced independently.
5. **Study** — notes render as GFM-flavored markdown; the quiz is an
   interactive MCQ with submit → color feedback → explanations → score; the
   flashcards are a flip deck with Previous/Next.
6. **Export** — notes download as TXT or PDF (server-generated, Unicode-safe).

State lives in `Home.jsx` (`sessionId`, `transcript`, `notes`, `quiz`,
`flashcards`, per-action `loading`, `error`). A new upload clears all
generated material; errors surface in a banner at the top of the page.

## 3. Component inventory

| Component | Responsibility |
|---|---|
| `pages/Home.jsx` | The only page; owns all workflow state and the action buttons |
| `components/Header.jsx` | Sticky brand bar (logo mark, title, internship badge) |
| `components/AudioUploader.jsx` | File picker (accept `.mp3,.wav,.m4a`); disabled + "Transcribing..." state while busy |
| `components/TranscriptPanel.jsx` | Scrollable transcript with language badge; hidden until a transcript exists |
| `components/NotesPanel.jsx` | Renders markdown notes (react-markdown + `.prose-notes` styles); TXT/PDF download buttons |
| `components/QuizPanel.jsx` | Interactive MCQ: select → submit → correct/wrong coloring → explanation → score |
| `components/FlashcardsPanel.jsx` | Flip card with counter (`index + 1 / total`), Previous/Next |
| `components/Footer.jsx` | Author info + LinkedIn/GitHub links (SVG icons, `aria-label`) |
| `components/LoadingSpinner.jsx` | Centered spinner with a contextual label |
| `api/client.js` | Thin fetch wrapper; JSON error extraction; Blob downloads |

## 4. UX improvement pass

| Improvement | Status | Notes |
|---|---|---|
| Drag-and-drop uploader | Done | Drop-zone highlighting, click-to-browse fallback, client-side file validation + metadata chip |
| Pipeline progress indicator | Done | `Stepper` (upload → transcribe → generate) with done/current/pending states |
| Skeleton loading | Done | Shimmer placeholders for notes/quiz/flashcards panels |
| GFM markdown rendering | Done | `remark-gfm` wired into `NotesPanel`; `.prose-notes` covers tables, code, blockquotes, lists |
| Quiz progress + retake | Done | Answered counter + progress bar + Retake button |
| Quiz state reset on regeneration | Done | `useEffect` resets `answers`/`submitted` when a new quiz arrives |
| Flashcard keyboard navigation + reset | Done | Arrow keys navigate, Space/Enter flips, `index`/`flipped` reset on new deck, Shuffle |
| Copy transcript button | Done | One-click clipboard copy with feedback |
| Empty / error / success states | Done | Error banner + toast, "ready ✓" buttons, per-panel empty states |
| Toast notifications | Done | `Toast` component (role=status, auto-dismiss) |
| Skip-link | Done | `.skip-link` wired into `App.jsx`, visible on focus |
| `:focus-visible` outlines | Done | Global 2px indigo focus ring in `index.css` |
| `aria-live` regions | Done | Loading skeletons and toast announce async updates |
| Reduced-motion support | Done | Global `prefers-reduced-motion: reduce` rule in `index.css` |
| Favicon | Done | `public/favicon.svg` (mic mark) linked in `index.html` |

## 5. Responsive behavior

- **Desktop** — single centered column; quiz options in a two-column grid;
  action buttons in a row.
- **Tablet** — grids collapse (`sm:` breakpoints); `flex-wrap` on the action
  row; the footer switches from stacked to side-by-side.
- **Mobile** — one column throughout; panels go full width; transcripts and
  notes scroll internally so long content never stretches the page; sticky
  header/footer retained.
- No horizontal-scroll layouts by design; `overflow-x-auto` appears only on
  `pre`/code blocks.

## 6. Accessibility notes

- Semantic structure: one `h1` (header), panels are `section` elements with
  `h2` headings, `header`/`footer` landmarks.
- Interactive controls are real `<button>`/`<a>` elements with visible
  states; footer icons carry `aria-label`; decorative SVG icons are
  `aria-hidden`.
- Color is never the only signal: quiz feedback pairs color with text
  ("Score: X / 10", explanations).
- Language is declared (`<html lang="en">`); meta description and
  `theme-color` set.
- Remaining: `aria-live` for async updates, `aria-pressed`-style state on
  the flashcard flip, an accessible label for the (visually hidden) file
  input, and the skip-link wiring.

## 7. Remaining UX improvement ideas (honest)

1. **Progress must match reality.** Transcribe/generate are blocking server
   calls (single worker, `PERFORMANCE_AUDIT.md` §3). A pipeline indicator
   has to distinguish "queued" from "processing" or users will think the
   app is stuck during long Groq calls.
2. **Nothing survives refresh.** The client keeps all state in memory; a
   reload loses the session. "Resume last lecture" would need persistence
   (`ROADMAP.md` P3).
3. **Copy varies by failure.** 502/504 messages are safe but generic;
   context-aware copy ("Quiz generation failed — try again") would reduce
   friction when the AI service misbehaves.
4. **Download naming.** Filenames are fixed (`lecture_notes.pdf`); deriving
   them from the upload name or title would be a small win.
5. **Generation history.** Regeneration replaces in place; a lightweight
   per-session history (even client-side) would let users compare drafts.
6. **Dark mode.** Tailwind makes a class-based dark theme cheap, but it is
   out of scope for the demo.