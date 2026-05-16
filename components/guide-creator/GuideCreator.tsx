'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import PdfUploader from './PdfUploader'
import UrlFetcher from './UrlFetcher'
import CameraCapture from './CameraCapture'
import type { Guide } from '@/lib/types'

type Source = 'pdf' | 'url' | 'camera'

const SOURCE_LABELS: Record<Source, string> = {
  pdf: 'PDF',
  url: 'URL',
  camera: 'Camera',
}

export default function GuideCreator() {
  const [source, setSource] = useState<Source>('pdf')
  const [title, setTitle] = useState('')
  const [status, setStatus] = useState<'idle' | 'processing' | 'done' | 'error'>('idle')
  const [guideId, setGuideId] = useState<string | null>(null)
  const router = useRouter()

  async function createGuide(payload: { text?: string; images?: string[] }) {
    if (!title.trim()) {
      alert('Enter a guide title first.')
      return
    }
    setStatus('processing')
    try {
      const res = await fetch('/api/guides', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, title: title.trim(), ...payload }),
      })
      if (!res.ok) throw new Error('Processing failed')
      const guide: Guide = await res.json()

      const stored = JSON.parse(localStorage.getItem('junior_guides') ?? '[]') as string[]
      localStorage.setItem(
        'junior_guides',
        JSON.stringify([guide.id, ...stored.filter(id => id !== guide.id)].slice(0, 20))
      )
      setGuideId(guide.id)
      setStatus('done')
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="col" style={{ gap: 16 }}>
      <div className="field field-lg">
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="Guide title — e.g. KTANE Wires Module"
        />
      </div>

      <div className="row" style={{ gap: 8 }}>
        <div className="seg">
          {(['pdf', 'url', 'camera'] as Source[]).map(s => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={source === s ? 'on' : ''}
            >
              {SOURCE_LABELS[s]}
            </button>
          ))}
        </div>
      </div>

      {source === 'pdf' && <PdfUploader onCapture={images => createGuide({ images })} />}
      {source === 'url' && <UrlFetcher onFetch={text => createGuide({ text })} />}
      {source === 'camera' && <CameraCapture onCapture={image => createGuide({ images: [image] })} />}

      {status === 'processing' && (
        <div className="row" style={{ gap: 8 }}>
          <span className="tag tag-accent" style={{ animation: 'fadeInUp 0.3s ease' }}>Processing</span>
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>Claude is reading your guide — 10–30 seconds</span>
        </div>
      )}

      {status === 'error' && (
        <div className="row" style={{ gap: 8 }}>
          <span className="tag tag-live">Error</span>
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>Processing failed. Check API keys in .env.local.</span>
        </div>
      )}

      {status === 'done' && guideId && (
        <div className="card card-pad col" style={{ gap: 16 }}>
          <div className="row" style={{ gap: 8 }}>
            <span className="tag tag-accent">Ready</span>
            <span style={{ color: 'var(--ink)', fontSize: 14, fontWeight: 600 }}>Guide created</span>
          </div>
          <div className="col" style={{ gap: 4 }}>
            <span style={{ color: 'var(--muted)', fontSize: 11, textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-mono)' }}>Share link</span>
            <code className="mono" style={{ fontSize: 13, color: 'var(--accent)', wordBreak: 'break-all' }}>
              {typeof window !== 'undefined' ? `${window.location.origin}/g/${guideId}` : `/g/${guideId}`}
            </code>
          </div>
          <button
            onClick={() => router.push(`/g/${guideId}`)}
            className="btn btn-primary btn-block btn-lg"
          >
            Start Session
          </button>
        </div>
      )}
    </div>
  )
}
