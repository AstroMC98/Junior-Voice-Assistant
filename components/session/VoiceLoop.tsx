'use client'
import { useState, useCallback, useRef } from 'react'
import type { Guide, SessionResponse } from '@/lib/types'

interface Props {
  guide: Guide
  currentStepIndex: number
  onResponse: (response: SessionResponse) => void
}

declare global {
  interface Window {
    SpeechRecognition: typeof SpeechRecognition
    webkitSpeechRecognition: typeof SpeechRecognition
  }
}

export default function VoiceLoop({ guide, currentStepIndex, onResponse }: Props) {
  const [status, setStatus] = useState<'idle' | 'listening' | 'thinking'>('idle')
  const currentStepRef = useRef(currentStepIndex)
  currentStepRef.current = currentStepIndex

  const startListening = useCallback(() => {
    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition
    if (!SR) {
      alert('Speech recognition is not available in this browser. Use Chrome or Edge.')
      return
    }

    const rec = new SR()
    rec.lang = 'en-US'
    rec.interimResults = false
    rec.maxAlternatives = 1
    setStatus('listening')

    rec.onresult = async (event: SpeechRecognitionEvent) => {
      const transcript = event.results[0][0].transcript
      setStatus('thinking')

      try {
        const res = await fetch('/api/session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            guide,
            currentStepIndex: currentStepRef.current,
            transcript,
          }),
        })
        const response: SessionResponse = await res.json()

        const utt = new SpeechSynthesisUtterance(response.speech)
        utt.rate = 1.05
        utt.onend = () => setStatus('idle')
        speechSynthesis.cancel()
        speechSynthesis.speak(utt)

        onResponse(response)
      } catch {
        setStatus('idle')
      }
    }

    rec.onerror = () => setStatus('idle')
    rec.onend = () => setStatus('idle')

    rec.start()
  }, [guide, onResponse])

  const label = status === 'idle' ? 'Tap to Speak' : status === 'listening' ? 'Listening...' : 'Thinking...'

  return (
    <button
      onClick={startListening}
      disabled={status !== 'idle'}
      className={`w-full py-5 rounded-2xl font-semibold text-lg transition-all select-none ${
        status === 'idle'
          ? 'bg-blue-600 hover:bg-blue-700 active:scale-95 text-white shadow-lg shadow-blue-900/30'
          : status === 'listening'
          ? 'bg-red-500 text-white animate-pulse cursor-default'
          : 'bg-slate-700 text-slate-400 cursor-default'
      }`}
    >
      {label}
    </button>
  )
}
