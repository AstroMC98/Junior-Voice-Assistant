interface Props {
  title: string
  content: string
  stepIndex: number
  totalSteps: number
  onPrev: () => void
  onNext: () => void
}

export default function StepDisplay({
  title,
  content,
  stepIndex,
  totalSteps,
  onPrev,
  onNext,
}: Props) {
  return (
    <div className="bg-slate-800 rounded-xl p-6 space-y-4">
      <div className="text-slate-500 text-xs font-medium tracking-wide uppercase">
        Step {stepIndex + 1} of {totalSteps}
      </div>
      <h2 className="text-xl font-semibold text-slate-100 leading-snug">{title}</h2>
      <p className="text-slate-300 leading-relaxed">{content}</p>
      <div className="flex gap-3 pt-1">
        <button
          onClick={onPrev}
          disabled={stepIndex === 0}
          className="flex-1 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300 text-sm font-medium transition-colors"
        >
          Previous
        </button>
        <button
          onClick={onNext}
          disabled={stepIndex >= totalSteps - 1}
          className="flex-1 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed text-slate-300 text-sm font-medium transition-colors"
        >
          Next
        </button>
      </div>
    </div>
  )
}
