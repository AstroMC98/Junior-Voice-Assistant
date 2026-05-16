'use client'
import { useState, useCallback, useRef } from 'react'
import type { Guide, SessionResponse } from '@/lib/types'
import { API_BASE } from '@/lib/types'

interface Props {
  guide: Guide
  currentStepIndex: number
  onResponse: (response: SessionResponse) => void
}

interface SpeechRecognitionResult {
  readonly length: number
  [index: number]: { transcript: string; confidence: number }
}
interface SpeechRecognitionResultList {
  readonly length: number
  [index: number]: SpeechRecognitionResult
}
interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList
}
interface SpeechRecognitionInstance extends EventTarget {
  lang: string
  interimResults: boolean
  maxAlternatives: number
  onresult: ((event: SpeechRecognitionEvent) => void) | null
  onerror: ((event: Event) => void) | null
  onend: ((event: Event) => void) | null
  start(): void
}

declare global {
  interface Window {
    SpeechRecognition: new () => SpeechRecognitionInstance
    webkitSpeechRecognition: new () => SpeechRecognitionInstance
  }
}

function MicIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
      <line x1="8" y1="23" x2="16" y2="23" />
    </svg>
  )
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
        const res = await fetch(`${API_BASE}/api/session`, {
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
    rec.onend = () => setStatus(prev => prev === 'listening' ? 'idle' : prev)

    rec.start()
  }, [guide, onResponse])

  const isListening = status === 'listening'
  const isThinking = status === 'thinking'

  return (
    <button
      onClick={startListening}
      disabled={status !== 'idle'}
      className={[
        'btn btn-lg btn-block',
        isListening ? 'btn-primary pulse' : '',
        isThinking ? 'btn-secondary' : '',
        !isListening && !isThinking ? 'btn-primary' : '',
      ].filter(Boolean).join(' ')}
      style={{ gap: 10, cursor: status !== 'idle' ? 'default' : 'pointer' }}
    >
      <MicIcon />
      {status === 'idle' ? 'Tap to Speak' : status === 'listening' ? 'Listening…' : 'Thinking…'}
    </button>
  )
}
