'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'

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
    <div className="mt-10">
      <h2 className="text-sm font-medium text-slate-500 uppercase tracking-wider mb-3">
        Your guides
      </h2>
      <ul className="space-y-2">
        {guideIds.map(id => (
          <li key={id}>
            <Link
              href={`/g/${id}`}
              className="block px-4 py-2.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-sm transition-colors border border-slate-700"
            >
              /g/{id}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}
