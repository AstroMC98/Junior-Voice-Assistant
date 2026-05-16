'use client'
import { useEffect, useState } from 'react'
import { notFound, useParams } from 'next/navigation'
import AppShell from '@/components/layout/AppShell'
import SessionView from '@/components/session/SessionView'
import type { Guide } from '@/lib/types'
import { API_BASE } from '@/lib/types'

export default function GuidePage() {
  const { id } = useParams<{ id: string }>()
  const [guide, setGuide] = useState<Guide | null>(null)
  const [status, setStatus] = useState<'loading' | 'not_found' | 'error' | 'ready'>('loading')

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`${API_BASE}/api/guides/${id}`)
        if (res.status === 404) { setStatus('not_found'); return }
        if (!res.ok) { setStatus('error'); return }
        setGuide(await res.json())
        setStatus('ready')
      } catch {
        setStatus('error')
      }
    }
    load()
  }, [id])

  if (status === 'not_found') return notFound()

  if (status === 'loading') {
    return (
      <AppShell title="Junior" backHref="/" fillHeight>
        <div style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center', padding: 40 }}>
          Loading guide…
        </div>
      </AppShell>
    )
  }

  if (status === 'error') {
    return (
      <AppShell title="Junior" backHref="/" fillHeight>
        <div style={{ color: 'var(--muted)', fontSize: 14, textAlign: 'center', padding: 40 }}>
          Failed to load guide.
        </div>
      </AppShell>
    )
  }

  return (
    <AppShell title={guide!.title} backHref="/" fillHeight>
      <SessionView guide={guide!} />
    </AppShell>
  )
}
