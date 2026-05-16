'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import type { Guide, SessionResponse } from '@/lib/types'
import StepDisplay from './StepDisplay'
import ImageViewer from './ImageViewer'
import VoiceLoop from './VoiceLoop'
import ProgressCheck from './ProgressCheck'

interface Props {
  guide: Guide
}

function ForkIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="18" r="3" /><circle cx="6" cy="6" r="3" /><circle cx="18" cy="6" r="3" />
      <path d="M18 9v2a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V9" /><line x1="12" y1="12" x2="12" y2="15" />
    </svg>
  )
}

function ImageIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="3" width="18" height="18" rx="2" /><circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21 15 16 10 5 21" />
    </svg>
  )
}

export default function SessionView({ guide }: Props) {
  const [stepIndex, setStepIndex] = useState(0)
  const [showImage, setShowImage] = useState(false)
  const [lastSpeech, setLastSpeech] = useState<string | null>(null)
  const router = useRouter()

  const step = guide.steps[stepIndex]

  function handleResponse(response: SessionResponse) {
    setLastSpeech(response.speech)
    if (response.action === 'advance' && response.step !== null) {
      const next = Math.min(Math.max(response.step, 0), guide.steps.length - 1)
      setStepIndex(next)
      setShowImage(!!guide.steps[next]?.image_url)
    } else if (response.action === 'show_image') {
      setShowImage(true)
    }
  }

  async function fork() {
    const res = await fetch(`/api/guides/${guide.id}`, { method: 'POST' })
    if (!res.ok) return alert('Fork failed')
    const forked: Guide = await res.json()
    const stored = JSON.parse(localStorage.getItem('junior_guides') ?? '[]') as string[]
    localStorage.setItem('junior_guides', JSON.stringify([forked.id, ...stored].slice(0, 20)))
    router.push(`/g/${forked.id}`)
  }

  function goTo(index: number) {
    const clamped = Math.min(Math.max(index, 0), guide.steps.length - 1)
    setStepIndex(clamped)
    setShowImage(!!guide.steps[clamped]?.image_url)
  }

  const imageArea = (
    <>
      {showImage && step.image_url && (
        <ImageViewer imageUrl={step.image_url} crop={step.crop} />
      )}
      {!showImage && step.image_url && (
        <button
          onClick={() => setShowImage(true)}
          className="btn btn-secondary btn-block"
          style={{ gap: 8 }}
        >
          <ImageIcon />
          Show image for this step
        </button>
      )}
    </>
  )

  const speechBubble = lastSpeech ? (
    <div className="card card-pad" style={{ fontStyle: 'italic', color: 'var(--muted)', fontSize: 14, lineHeight: 1.6 }}>
      &ldquo;{lastSpeech}&rdquo;
    </div>
  ) : null

  const voiceArea = (
    <div className="col" style={{ gap: 12 }}>
      <VoiceLoop guide={guide} currentStepIndex={stepIndex} onResponse={handleResponse} />
      <ProgressCheck guide={guide} currentStepIndex={stepIndex} onResult={handleResponse} />
      {speechBubble}
    </div>
  )

  const forkBtn = (
    <button onClick={fork} className="btn btn-ghost btn-sm" style={{ gap: 6 }}>
      <ForkIcon />
      Fork
    </button>
  )

  return (
    <>
      {/*
        Both layouts render in the DOM simultaneously; CSS media queries toggle visibility.
        This avoids React hydration mismatches that occur when JS-based viewport detection
        produces a different tree on server vs. client. Stateful children (VoiceLoop,
        ProgressCheck) are mounted twice but the hidden layout's buttons are unreachable
        via pointer events, so there is no risk of duplicate interactions.
      */}

      {/* ── Mobile layout (single column, shown on small screens) ── */}
      <div className="col mobile-session" style={{ gap: 14 }}>
        <div className="row between">
          <span style={{ color: 'var(--muted)', fontSize: 13, fontFamily: 'var(--font-mono)', letterSpacing: '0.04em' }}>
            {guide.title}
          </span>
          {forkBtn}
        </div>

        <StepDisplay
          title={step.title}
          content={step.content}
          stepIndex={stepIndex}
          totalSteps={guide.steps.length}
          onPrev={() => goTo(stepIndex - 1)}
          onNext={() => goTo(stepIndex + 1)}
        />

        {imageArea}
        {voiceArea}
      </div>

      {/* ── Desktop layout (3-column, shown on wide screens) ── */}
      <div className="desktop-session dt-session">
        {/* Left col: step display */}
        <div className="dt-session-col" style={{ padding: 24 }}>
          <div className="row between" style={{ marginBottom: 20 }}>
            <span className="dt-eyebrow">{guide.title}</span>
            {forkBtn}
          </div>
          <StepDisplay
            title={step.title}
            content={step.content}
            stepIndex={stepIndex}
            totalSteps={guide.steps.length}
            onPrev={() => goTo(stepIndex - 1)}
            onNext={() => goTo(stepIndex + 1)}
          />
        </div>

        {/* Center col: image */}
        <div className="dt-session-center" style={{ alignItems: 'center', justifyContent: 'center', padding: 32 }}>
          {showImage && step.image_url ? (
            <ImageViewer imageUrl={step.image_url} crop={step.crop} />
          ) : step.image_url ? (
            <button onClick={() => setShowImage(true)} className="btn btn-secondary" style={{ gap: 8 }}>
              <ImageIcon />
              Show image
            </button>
          ) : (
            <div className="col" style={{ alignItems: 'center', gap: 12 }}>
              <div style={{ width: 64, height: 64, borderRadius: 'var(--r-lg)', background: 'var(--surface-2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <ImageIcon />
              </div>
              <span style={{ color: 'var(--muted)', fontSize: 13 }}>No image for this step</span>
            </div>
          )}
        </div>

        {/* Right col: voice + progress */}
        <div className="dt-session-col" style={{ padding: 24 }}>
          <div className="col" style={{ gap: 14, height: '100%' }}>
            <VoiceLoop guide={guide} currentStepIndex={stepIndex} onResponse={handleResponse} />
            <ProgressCheck guide={guide} currentStepIndex={stepIndex} onResult={handleResponse} />
            {speechBubble}
          </div>
        </div>
      </div>
    </>
  )
}
