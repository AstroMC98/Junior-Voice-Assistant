'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'

function ChevronRight({ size = 14 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="9 18 15 12 9 6" />
    </svg>
  )
}

export default function RecentGuides() {
  const [guideIds, setGuideIds] = useState<string[]>([])

  useEffect(() => {
    try {
      const stored = JSON.parse(localStorage.getItem('junior_guides') ?? '[]')
      if (Array.isArray(stored)) setGuideIds(stored.slice(0, 10))
    } catch {
      // ignore corrupt localStorage
    }
  }, [])

  if (guideIds.length === 0) return null

  return (
    <div style={{ marginTop: 28 }}>
      <div className="sec-title" style={{ padding: 0, marginBottom: 10 }}>
        <h2>My Guides</h2>
      </div>
      <div className="col" style={{ gap: 6 }}>
        {guideIds.map(id => (
          <Link key={id} href={`/g/${id}`} style={{ textDecoration: 'none' }}>
            <div className="card card-pad row between" style={{ transition: 'background 0.12s' }}>
              <span className="mono" style={{ fontSize: 13, color: 'var(--ink-2)' }}>/g/{id}</span>
              <span style={{ color: 'var(--muted)' }}><ChevronRight /></span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
