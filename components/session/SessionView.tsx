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

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <a href="/" className="text-slate-500 text-sm hover:text-slate-300 transition-colors">
            ← Junior
          </a>
          <h1 className="text-xl font-bold text-slate-100 mt-1 leading-tight">
            {guide.title}
          </h1>
        </div>
        <button
          onClick={fork}
          className="shrink-0 text-sm text-slate-500 hover:text-blue-400 transition-colors pt-5"
        >
          Fork
        </button>
      </div>

      <StepDisplay
        title={step.title}
        content={step.content}
        stepIndex={stepIndex}
        totalSteps={guide.steps.length}
        onPrev={() => goTo(stepIndex - 1)}
        onNext={() => goTo(stepIndex + 1)}
      />

      {showImage && step.image_url && (
        <ImageViewer imageUrl={step.image_url} crop={step.crop} />
      )}

      {!showImage && step.image_url && (
        <button
          onClick={() => setShowImage(true)}
          className="w-full py-2 rounded-lg border border-slate-700 text-slate-400 text-sm hover:border-slate-500 hover:text-slate-300 transition-colors"
        >
          Show image for this step
        </button>
      )}

      {lastSpeech && (
        <div className="bg-slate-800/50 rounded-lg px-4 py-3 text-slate-400 text-sm italic border border-slate-700/50">
          &ldquo;{lastSpeech}&rdquo;
        </div>
      )}

      <VoiceLoop
        guide={guide}
        currentStepIndex={stepIndex}
        onResponse={handleResponse}
      />

      <ProgressCheck
        guide={guide}
        currentStepIndex={stepIndex}
        onResult={handleResponse}
      />
    </div>
  )
}
