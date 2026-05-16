'use client'
import { useState } from 'react'
import { useApiKey } from '@/lib/ApiKeyContext'

export default function ApiKeyModal() {
  const { modalOpen, closeModal, setApiKey, apiKey } = useApiKey()
  const [draft, setDraft] = useState(apiKey)

  if (!modalOpen) return null

  function save() {
    setApiKey(draft.trim())
    closeModal()
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(0,0,0,0.6)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
      }}
      onClick={e => { if (e.target === e.currentTarget) closeModal() }}
    >
      <div className="card card-pad col" style={{ gap: 16, maxWidth: 420, width: '100%' }}>
        <div className="col" style={{ gap: 4 }}>
          <span style={{ fontWeight: 600, fontSize: 16 }}>Anthropic API Key</span>
          <span style={{ color: 'var(--muted)', fontSize: 13 }}>
            Sent over HTTPS only. Never stored or logged.{' '}
            <a
              href="https://console.anthropic.com"
              target="_blank"
              rel="noreferrer"
              style={{ color: 'var(--accent)' }}
            >
              Get a key →
            </a>
          </span>
        </div>

        <div className="field">
          <input
            type="password"
            value={draft}
            onChange={e => setDraft(e.target.value)}
            placeholder="sk-ant-..."
            autoFocus
            onKeyDown={e => e.key === 'Enter' && draft.trim() && save()}
          />
        </div>

        <div className="row" style={{ gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost btn-sm" onClick={closeModal}>
            Cancel
          </button>
          <button
            className="btn btn-primary btn-sm"
            onClick={save}
            disabled={!draft.trim()}
          >
            Save for session
          </button>
        </div>
      </div>
    </div>
  )
}
