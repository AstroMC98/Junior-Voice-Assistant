'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import type { ReactNode } from 'react'

interface Props {
  title: string
  backHref?: string
  rightSlot?: ReactNode
  fillHeight?: boolean
  children: ReactNode
}

function HomeIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  )
}

function BookIcon({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
      <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
    </svg>
  )
}

function SearchIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  )
}

function ChevronLeft({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="15 18 9 12 15 6" />
    </svg>
  )
}

const NAV_ITEMS = [
  { label: 'Discover', href: '/', icon: HomeIcon },
  { label: 'My Guides', href: '/', icon: BookIcon },
]

export default function AppShell({ title, backHref, rightSlot, fillHeight, children }: Props) {
  const pathname = usePathname()

  return (
    <>
      {/* ── Mobile shell ─────────────────────────────────────── */}
      <div className="shell-mobile app">
        <header className="app-header">
          <div className="col" style={{ gap: 2, flex: 1 }}>
            {backHref ? (
              <Link href={backHref} className="row" style={{ color: 'var(--muted)', fontSize: 13, gap: 4, marginBottom: 4 }}>
                <ChevronLeft size={16} />
                Junior
              </Link>
            ) : null}
            <h1 style={{ margin: 0, fontSize: backHref ? 20 : 28, fontWeight: 600, letterSpacing: '-0.02em', lineHeight: 1.1 }}>
              {backHref ? title : 'Junior'}
            </h1>
            {!backHref && (
              <p className="h-sub">Load a guide. Speak freely. Keep your hands free.</p>
            )}
          </div>
          {rightSlot && <div className="row" style={{ flexShrink: 0 }}>{rightSlot}</div>}
        </header>

        <div className="app-scroll">
          <div style={{ padding: '8px 20px 24px' }}>
            {children}
          </div>
        </div>

        <nav className="tabbar">
          {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
            const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
            return (
              <Link key={label} href={href} className={`tab${active ? ' active' : ''}`}>
                <span className="tab-ico"><Icon size={22} /></span>
                {label}
              </Link>
            )
          })}
        </nav>
      </div>

      {/* ── Desktop shell ────────────────────────────────────── */}
      <div className="shell-desktop dt-app dt">
        {/* Sidebar */}
        <aside className="dt-side">
          <div className="dt-logo">
            <div className="dt-logo-mark">J</div>
            <div className="col" style={{ gap: 1 }}>
              <span className="dt-logo-name">Junior</span>
              <span className="dt-logo-sub">GUIDE ASSISTANT</span>
            </div>
          </div>

          <span className="dt-side-label">Navigate</span>

          {NAV_ITEMS.map(({ label, href, icon: Icon }) => {
            const active = href === '/' ? pathname === '/' : pathname.startsWith(href)
            return (
              <Link key={label} href={href} className={`dt-nav-item${active ? ' active' : ''}`}>
                <Icon size={18} />
                {label}
              </Link>
            )
          })}

          <div style={{ flex: 1 }} />

          <div className="row" style={{ padding: '12px 10px', borderTop: '1px solid var(--border)' }}>
            <div className="avatar" style={{ background: 'var(--accent)', color: '#0E0C09' }}>J</div>
            <div className="col" style={{ gap: 1 }}>
              <span style={{ fontSize: 13, fontWeight: 600 }}>You</span>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>Local session</span>
            </div>
          </div>
        </aside>

        {/* Top bar */}
        <header className="dt-top">
          <div className="dt-search">
            <SearchIcon size={14} />
            <input type="text" placeholder="Search guides..." readOnly />
          </div>
          <div style={{ flex: 1 }} />
          {rightSlot && <div className="dt-row">{rightSlot}</div>}
          <div className="avatar">{title.charAt(0).toUpperCase()}</div>
        </header>

        {/* Main */}
        <main className="dt-main">
          {fillHeight ? (
            children
          ) : (
            <div className="dt-main-pad">
              {backHref ? (
                <div style={{ marginBottom: 20 }}>
                  <Link href={backHref} className="row" style={{ color: 'var(--muted)', fontSize: 13, gap: 4, marginBottom: 8, display: 'inline-flex' }}>
                    <ChevronLeft size={14} />
                    Back
                  </Link>
                  <h1 className="dt-h1">{title}</h1>
                </div>
              ) : (
                <div style={{ marginBottom: 28 }}>
                  <h1 className="dt-h1">Discover</h1>
                  <p style={{ color: 'var(--muted)', fontSize: 15, marginTop: 4 }}>Load a guide. Speak freely. Keep your hands free.</p>
                </div>
              )}
              {children}
            </div>
          )}
        </main>
      </div>
    </>
  )
}
