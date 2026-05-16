'use client'
import { useState } from 'react'

interface Props {
  onFetch: (text: string) => void
}

export default function UrlFetcher({ onFetch }: Props) {
  const [url, setUrl] = useState('')
  const [status, setStatus] = useState<'idle' | 'fetching' | 'error'>('idle')

  async function handleFetch() {
    if (!url.trim()) return
    setStatus('fetching')
    try {
      const res = await fetch(`/api/fetch-url?url=${encodeURIComponent(url.trim())}`)
      if (!res.ok) throw new Error()
      const { text } = await res.json()
      setStatus('idle')
      onFetch(text)
    } catch {
      setStatus('error')
    }
  }

  return (
    <div className="space-y-3">
      <input
        type="url"
        value={url}
        onChange={e => setUrl(e.target.value)}
        onKeyDown={e => e.key === 'Enter' && handleFetch()}
        placeholder="https://example.com/recipe"
        className="w-full bg-slate-800 border border-slate-700 rounded-lg px-4 py-2.5 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500 transition-colors"
      />
      <button
        onClick={handleFetch}
        disabled={status === 'fetching' || !url.trim()}
        className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded-lg py-2.5 font-medium transition-colors"
      >
        {status === 'fetching' ? 'Fetching page...' : 'Fetch Guide'}
      </button>
      {status === 'error' && (
        <p className="text-red-400 text-sm">
          Could not fetch that URL. Try a different one, or paste the text manually.
        </p>
      )}
    </div>
  )
}
