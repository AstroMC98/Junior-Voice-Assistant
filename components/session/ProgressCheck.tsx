'use client'
import { useState } from 'react'
import type { Guide, SessionResponse } from '@/lib/types'

interface Props {
  guide: Guide
  currentStepIndex: number
  onResult: (response: SessionResponse) => void
}

export default function ProgressCheck({ guide, currentStepIndex, onResult }: Props) {
  const [status, setStatus] = useState<'idle' | 'capturing' | 'checking'>('idle')
  const [error, setError] = useState<string | null>(null)

  async function check() {
    setError(null)
    setStatus('capturing')

    let photo: string
    let stream: MediaStream | null = null
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      })
      const video = document.createElement('video')
      video.srcObject = stream
      video.muted = true
      await video.play()
      await new Promise<void>(resolve => {
        if (video.readyState >= 2) { resolve(); return }
        video.onloadedmetadata = () => resolve()
      })
      await new Promise<void>(r => setTimeout(r, 200))

      const canvas = document.createElement('canvas')
      canvas.width = video.videoWidth || 640
      canvas.height = video.videoHeight || 480
      canvas.getContext('2d')!.drawImage(video, 0, 0)
      photo = canvas.toDataURL('image/jpeg', 0.85).split(',')[1]
    } catch {
      setError('Camera access denied.')
      setStatus('idle')
      return
    } finally {
      stream?.getTracks().forEach(t => t.stop())
    }

    setStatus('checking')
    try {
      const res = await fetch('/api/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          guide,
          currentStepIndex,
          transcript: 'Check my progress on this step',
          photo,
        }),
      })
      const result: SessionResponse = await res.json()

      const utt = new SpeechSynthesisUtterance(result.speech)
      utt.rate = 1.05
      speechSynthesis.cancel()
      speechSynthesis.speak(utt)

      onResult(result)
    } catch {
      setError('Check failed. Try again.')
    } finally {
      setStatus('idle')
    }
  }

  return (
    <div className="space-y-2">
      <button
        onClick={check}
        disabled={status !== 'idle'}
        className="w-full py-3 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed text-slate-300 text-sm font-medium transition-colors border border-slate-700"
      >
        {status === 'idle'
          ? 'Check my progress'
          : status === 'capturing'
          ? 'Opening camera...'
          : 'Junior is looking...'}
      </button>
      {error && <p className="text-red-400 text-xs text-center">{error}</p>}
    </div>
  )
}
