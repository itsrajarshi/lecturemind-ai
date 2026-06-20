export default function Header() {
  return (
    <header className="sticky top-0 z-50 shrink-0 border-b border-slate-200 bg-white/95 shadow-sm backdrop-blur supports-[backdrop-filter]:bg-white/90">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 text-lg font-bold text-white">
            LM
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">LectureMind AI</h1>
            <p className="text-xs text-slate-500">
              Lecture Voice-to-Notes Generator
            </p>
          </div>
        </div>
        <span className="rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
          IBM SkillsBuild · AI Internship
        </span>
      </div>
    </header>
  );
}
