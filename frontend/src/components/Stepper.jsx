const STEPS = [
  { key: "upload", label: "Upload", icon: "📤" },
  { key: "transcribe", label: "Transcribe", icon: "🗣️" },
  { key: "generate", label: "Generate", icon: "✨" },
];

const statusFor = (stage, stepKey) => {
  const order = { upload: 0, transcribe: 1, generate: 2, complete: 3 };
  const active = order[stage];
  const index = order[stepKey];
  if (index < active) return "done";
  if (index === active) return "current";
  return "pending";
};

export default function Stepper({ stage }) {
  return (
    <nav aria-label="Processing progress" className="flex items-center justify-center gap-2 sm:gap-4">
      {STEPS.map((step, i) => {
        const status = statusFor(stage, step.key);
        return (
          <div key={step.key} className="flex items-center gap-2 sm:gap-4">
            {i > 0 && (
              <div
                aria-hidden="true"
                className={`h-0.5 w-6 sm:w-12 rounded ${status === "done" ? "bg-brand-500" : "bg-slate-200"}`}
              />
            )}
            <div
              aria-current={status === "current" ? "step" : undefined}
              className="flex items-center gap-2"
            >
              <span
                className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold transition ${
                  status === "done"
                    ? "bg-brand-600 text-white"
                    : status === "current"
                      ? "bg-brand-100 text-brand-700 ring-2 ring-brand-500"
                      : "bg-slate-100 text-slate-400"
                }`}
              >
                {status === "done" ? "✓" : step.icon}
              </span>
              <span
                className={`text-xs font-medium sm:text-sm ${
                  status === "pending" ? "text-slate-400" : "text-slate-800"
                }`}
              >
                {step.label}
              </span>
            </div>
          </div>
        );
      })}
    </nav>
  );
}