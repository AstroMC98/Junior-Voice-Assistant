'use client'
import { useState, useCallback, useRef, useEffect } from 'react'
import { GoogleGenAI } from '@google/genai'
import type { Guide, SessionResponse } from '@/lib/types'
import { API_BASE } from '@/lib/types'
import { useApiKey } from '@/lib/ApiKeyContext'
import { extractJson } from '@/lib/extractJson'

const GEMINI_MODEL = 'gemini-2.0-flash-exp'
const GEMINI_SYSTEM_INSTRUCTION =
  'You are a step-by-step guide assistant. When given a user question and context, ' +
  'respond ONLY with a JSON object: {"speech": "...", "action": null, "step": null}. ' +
  'Use "advance" action only when the user has clearly completed the current step. ' +
  'Keep speech concise and conversational.'

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

function blobToBase64(blob: Blob): Promise<string> {
  return blob.arrayBuffer().then(buffer => {
    const bytes = new Uint8Array(buffer)
    let binary = ''
    for (let i = 0; i < bytes.length; i += 8192) {
      binary += String.fromCharCode(...Array.from(bytes.subarray(i, i + 8192)))
    }
    return btoa(binary)
  })
}

async function fetchContext(guide: Guide, stepIndex: number, transcript: string): Promise<string> {
  const formData = new FormData()
  formData.append('guide', JSON.stringify(guide))
  formData.append('currentStepIndex', String(stepIndex))
  formData.append('transcript', transcript)
  try {
    const res = await fetch(`${API_BASE}/api/retrieve`, { method: 'POST', body: formData })
    if (res.ok) return (await res.json()).context ?? ''
  } catch { /* fall through */ }
  return ''
}

async function runGeminiTurn(
  audioBlob: Blob,
  guide: Guide,
  stepIndex: number,
  apiKey: string,
): Promise<SessionResponse> {
  const base64Audio = await blobToBase64(audioBlob)

  let resolveTranscript!: (t: string) => void
  let rejectSession!: (e: unknown) => void
  let resolveResponse!: (r: string) => void
  const transcriptPromise = new Promise<string>((res, rej) => {
    resolveTranscript = res
    rejectSession = rej
  })
  let rejectResponse!: (e: unknown) => void
  const responsePromise = new Promise<string>((res, rej) => {
    resolveResponse = res
    rejectResponse = rej
  })

  let phase: 'transcript' | 'response' = 'transcript'
  const transcriptParts: string[] = []
  const responseParts: string[] = []

  const ai = new GoogleGenAI({ apiKey })
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const session = await (ai.live as any).connect({
    model: GEMINI_MODEL,
    config: {
      responseModalities: ['TEXT'],
      systemInstruction: { parts: [{ text: GEMINI_SYSTEM_INSTRUCTION }] },
    },
    callbacks: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onmessage: (msg: any) => {
        if (phase === 'transcript') {
          const t = msg.serverContent?.inputAudioTranscription
          if (typeof t === 'string' && t) transcriptParts.push(t)
          else if (t?.text) transcriptParts.push(t.text)
          if (msg.serverContent?.turnComplete) resolveTranscript(transcriptParts.join(''))
        } else {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const parts: any[] = msg.serverContent?.modelTurn?.parts ?? []
          for (const p of parts) { if (p.text) responseParts.push(p.text) }
          if (msg.serverContent?.turnComplete) resolveResponse(responseParts.join(''))
        }
      },
      onerror: (e: unknown) => { rejectSession(e); rejectResponse(e) },
      onclose: () => {
        resolveTranscript(transcriptParts.join(''))
        resolveResponse(responseParts.join(''))
      },
    },
  })

  try {
    // Phase 1: send audio, await transcript
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (session as any).sendRealtimeInput({
      mediaChunks: [{ data: base64Audio, mimeType: 'audio/webm' }],
    })
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (session as any).sendRealtimeInput({ audioStreamEnd: true })

    const transcript = await transcriptPromise

    // Phase 2: fetch context, inject, await response
    const context = await fetchContext(guide, stepIndex, transcript)
    phase = 'response'
    const contextPrompt = context
      ? `[Context: ${context}]\n\nUser said: ${transcript}`
      : transcript

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await (session as any).sendClientContent({
      turns: [{ role: 'user', parts: [{ text: contextPrompt }] }],
      turnComplete: true,
    })

    const responseText = await responsePromise
    return (
      extractJson(responseText) ?? {
        speech: responseText || "Sorry, I couldn't process that.",
        action: null,
        step: null,
      }
    )
  } finally {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    ;(session as any).close()
  }
}

export default function GeminiVoiceLoop({ guide, currentStepIndex, onResponse }: Props) {
  const [status, setStatus] = useState<'idle' | 'listening' | 'thinking'>('idle')
  const currentStepRef = useRef(currentStepIndex)
  currentStepRef.current = currentStepIndex
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const isRecordingRef = useRef(false)
  const mountedRef = useRef(true)
  const { geminiKey, openModal } = useApiKey()

  useEffect(() => () => { mountedRef.current = false }, [])

  const stopListening = useCallback(() => {
    mediaRecorderRef.current?.stop()
  }, [])

  const startListening = useCallback(async () => {
    if (isRecordingRef.current) return
    isRecordingRef.current = true

    if (!geminiKey) { isRecordingRef.current = false; openModal(); return }

    if (!window.MediaRecorder) {
      isRecordingRef.current = false
      alert('Audio recording is not available in this browser. Use Chrome, Edge, or Firefox.')
      return
    }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      isRecordingRef.current = false
      alert('Microphone access denied. Please allow microphone access and try again.')
      return
    }

    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : 'audio/webm'

    let recorder: MediaRecorder
    try {
      recorder = new MediaRecorder(stream, { mimeType })
    } catch {
      isRecordingRef.current = false
      stream.getTracks().forEach(t => t.stop())
      alert('Audio recording failed to start.')
      return
    }

    mediaRecorderRef.current = recorder
    audioChunksRef.current = []
    recorder.ondataavailable = e => { if (e.data.size > 0) audioChunksRef.current.push(e.data) }

    recorder.onstop = async () => {
      isRecordingRef.current = false
      stream.getTracks().forEach(t => t.stop())
      if (!mountedRef.current) return

      const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
      setStatus('thinking')

      try {
        const parsed = await runGeminiTurn(audioBlob, guide, currentStepRef.current, geminiKey)
        if (!mountedRef.current) return

        const utt = new SpeechSynthesisUtterance(parsed.speech)
        utt.rate = 1.05
        utt.onend = () => { if (mountedRef.current) setStatus('idle') }
        speechSynthesis.cancel()
        speechSynthesis.speak(utt)

        if (!mountedRef.current) return
        onResponse(parsed)
      } catch {
        if (!mountedRef.current) return
        setStatus('idle')
      }
    }

    recorder.start()
    setStatus('listening')
  }, [guide, onResponse, geminiKey, openModal])

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
