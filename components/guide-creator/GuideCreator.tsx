'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import PdfUploader from './PdfUploader'
import UrlFetcher from './UrlFetcher'
import CameraCapture from './CameraCapture'
import type { Guide } from '@/lib/types'

type Source = 'pdf' | 'url' | 'camera'

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
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-1.5">Guide title</label>
        <input
          type="text"
          value={title}
          onChange={e => setTitle(e.target.value)}
          placeholder="e.g. KTANE Wires Module"
          className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-400 mb-1.5">Source</label>
        <div className="flex gap-2">
          {(['pdf', 'url', 'camera'] as Source[]).map(s => (
            <button
              key={s}
              onClick={() => setSource(s)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                source === s
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              {s.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {source === 'pdf' && <PdfUploader onCapture={images => createGuide({ images })} />}
      {source === 'url' && <UrlFetcher onFetch={text => createGuide({ text })} />}
      {source === 'camera' && <CameraCapture onCapture={image => createGuide({ images: [image] })} />}

      {status === 'processing' && (
        <p className="text-blue-400 text-sm animate-pulse">
          Processing guide with Claude — this takes 10-30 seconds...
        </p>
      )}

      {status === 'error' && (
        <p className="text-red-400 text-sm">
          Processing failed. Check your API keys in .env.local and try again.
        </p>
      )}

      {status === 'done' && guideId && (
        <div className="bg-slate-800 rounded-xl p-5 space-y-4">
          <p className="text-green-400 font-medium">Guide ready!</p>
          <div>
            <p className="text-xs text-slate-500 mb-1">Share link</p>
            <code className="text-blue-400 text-sm break-all">
              {typeof window !== 'undefined' ? `${window.location.origin}/g/${guideId}` : `/g/${guideId}`}
            </code>
          </div>
          <button
            onClick={() => router.push(`/g/${guideId}`)}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 font-medium transition-colors"
          >
            Start Session
          </button>
        </div>
      )}
    </div>
  )
}
