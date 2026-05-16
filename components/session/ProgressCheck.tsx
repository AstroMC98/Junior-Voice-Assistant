'use client'
import { useState } from 'react'
import type { Guide, SessionResponse } from '@/lib/types'
import { API_BASE } from '@/lib/types'
import { useApiKey } from '@/lib/ApiKeyContext'
import { apiFetch, ApiKeyError } from '@/lib/apiFetch'

interface Props {
  guide: Guide
  currentStepIndex: number
  onResult: (response: SessionResponse) => void
}

function CameraIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z" />
      <circle cx="12" cy="13" r="4" />
    </svg>
  )
}

export default function ProgressCheck({ guide, currentStepIndex, onResult }: Props) {
  const [status, setStatus] = useState<'idle' | 'capturing' | 'checking'>('idle')
  const [error, setError] = useState<string | null>(null)
  const { apiKey, openModal } = useApiKey()

  async function check() {
    if (!apiKey) {
      openModal()
      return
    }
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
      const res = await apiFetch(`${API_BASE}/api/session`, apiKey, {
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
    } catch (err) {
      if (err instanceof ApiKeyError) {
        openModal()
      } else {
        setError('Check failed. Try again.')
      }
    } finally {
      setStatus('idle')
    }
  }

  const label = status === 'idle'
    ? 'Check my progress'
    : status === 'capturing'
    ? 'Opening camera…'
    : 'Junior is looking…'

  return (
    <div className="col" style={{ gap: 8 }}>
      <button
        onClick={check}
        disabled={status !== 'idle'}
        className="btn btn-secondary btn-block"
        style={{ gap: 8, opacity: status !== 'idle' ? 0.6 : 1, cursor: status !== 'idle' ? 'default' : 'pointer' }}
      >
        <CameraIcon />
        {label}
      </button>
      {error && (
        <p style={{ margin: 0, color: 'var(--muted)', fontSize: 12, textAlign: 'center' }}>
          <span className="tag tag-live" style={{ marginRight: 6 }}>Error</span>
          {error}
        </p>
      )}
    </div>
  )
}
