'use client'
import { useRef, useState } from 'react'

interface Props {
  onCapture: (image: string) => void
}

export default function CameraCapture({ onCapture }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [streaming, setStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function startCamera() {
    setError(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      })
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setStreaming(true)
    } catch {
      setError('Camera access denied. Check your browser permissions.')
    }
  }

  function capture() {
    if (!videoRef.current) return
    const canvas = document.createElement('canvas')
    canvas.width = videoRef.current.videoWidth
    canvas.height = videoRef.current.videoHeight
    canvas.getContext('2d')!.drawImage(videoRef.current, 0, 0)
    const base64 = canvas.toDataURL('image/png').split(',')[1]
    ;(videoRef.current.srcObject as MediaStream).getTracks().forEach(t => t.stop())
    setStreaming(false)
    onCapture(base64)
  }

  return (
    <div className="space-y-3">
      {error && <p className="text-red-400 text-sm">{error}</p>}
      {!streaming ? (
        <button
          onClick={startCamera}
          className="w-full bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg py-3 font-medium transition-colors"
        >
          Open Camera
        </button>
      ) : (
        <div className="space-y-3">
          <video
            ref={videoRef}
            className="w-full rounded-lg"
            autoPlay
            playsInline
            muted
          />
          <button
            onClick={capture}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 font-medium transition-colors"
          >
            Capture Photo
          </button>
        </div>
      )}
    </div>
  )
}
