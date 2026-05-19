'use client'
import { useState, useCallback, useRef } from 'react'
import type { Guide, SessionResponse } from '@/lib/types'
import { API_BASE } from '@/lib/types'
import { useApiKey } from '@/lib/ApiKeyContext'
import { apiFetch, ApiKeyError } from '@/lib/apiFetch'

interface Props {
  guide: Guide
  currentStepIndex: number
  onResponse: (response: SessionResponse) => void
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
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const { apiKey, openModal } = useApiKey()

  const stopListening = useCallback(() => {
    mediaRecorderRef.current?.stop()
  }, [])

  const startListening = useCallback(async () => {
    if (!apiKey) { openModal(); return }

    if (!window.MediaRecorder) {
      alert('Audio recording is not available in this browser. Use Chrome, Edge, or Firefox.')
      return
    }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      alert('Microphone access denied. Please allow microphone access and try again.')
      return
    }

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'

    const recorder = new MediaRecorder(stream, { mimeType })
    mediaRecorderRef.current = recorder
    audioChunksRef.current = []

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunksRef.current.push(e.data)
    }

    recorder.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop())

      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      setStatus('thinking')

      const formData = new FormData()
      formData.append('audio', audioBlob, 'audio.webm')
      formData.append('guide', JSON.stringify(guide))
      formData.append('currentStepIndex', String(currentStepRef.current))

      try {
        // No Content-Type header — browser sets multipart/form-data with boundary automatically
        const res = await apiFetch(`${API_BASE}/api/session`, apiKey, {
          method: 'POST',
          body: formData,
        })
        const response: SessionResponse = await res.json()

        const utt = new SpeechSynthesisUtterance(response.speech)
        utt.rate = 1.05
        utt.onend = () => setStatus('idle')
        speechSynthesis.cancel()
        speechSynthesis.speak(utt)

        onResponse(response)
      } catch (err) {
        if (err instanceof ApiKeyError) openModal()
        setStatus('idle')
      }
    }

    recorder.start()
    setStatus('listening')
  }, [guide, onResponse, apiKey, openModal])

  const handleClick = useCallback(() => {
    if (status === 'idle') startListening()
    else if (status === 'listening') stopListening()
  }, [status, startListening, stopListening])

  const isListening = status === 'listening'
  const isThinking = status === 'thinking'

  return (
    <button
      onClick={handleClick}
      disabled={isThinking}
      className={[
        'btn btn-lg btn-block',
        isListening ? 'btn-primary pulse' : '',
        isThinking ? 'btn-secondary' : '',
        !isListening && !isThinking ? 'btn-primary' : '',
      ].filter(Boolean).join(' ')}
      style={{ gap: 10, cursor: isThinking ? 'default' : 'pointer' }}
    >
      <MicIcon />
      {status === 'idle' ? 'Tap to Speak' : status === 'listening' ? 'Tap to Stop' : 'Thinking…'}
    </button>
  )
}
