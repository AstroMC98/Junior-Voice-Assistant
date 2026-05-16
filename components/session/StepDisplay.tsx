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
    <div className="card card-pad col" style={{ gap: 12 }}>
      <span className="tag stepnum mono">Step {stepIndex + 1} of {totalSteps}</span>
      <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600, letterSpacing: '-0.01em', lineHeight: 1.3, color: 'var(--ink)' }}>
        {title}
      </h2>
      <p style={{ margin: 0, color: 'var(--ink-2)', lineHeight: 1.65, fontSize: 15 }}>{content}</p>
      <div className="row between" style={{ paddingTop: 4 }}>
        <button
          onClick={onPrev}
          disabled={stepIndex === 0}
          className="btn btn-secondary"
          style={{ flex: 1, opacity: stepIndex === 0 ? 0.3 : 1, cursor: stepIndex === 0 ? 'not-allowed' : 'pointer' }}
        >
          Previous
        </button>
        <button
          onClick={onNext}
          disabled={stepIndex >= totalSteps - 1}
          className="btn btn-secondary"
          style={{ flex: 1, opacity: stepIndex >= totalSteps - 1 ? 0.3 : 1, cursor: stepIndex >= totalSteps - 1 ? 'not-allowed' : 'pointer' }}
        >
          Next
        </button>
      </div>
    </div>
  )
}
