import type { Metadata } from 'next'
import localFont from 'next/font/local'
import './globals.css'

const geistSans = localFont({
  src: './fonts/GeistVF.woff',
  variable: '--font-geist-sans',
  weight: '100 900',
  display: 'swap',
})

const geistMono = localFont({
  src: './fonts/GeistMonoVF.woff',
  variable: '--font-geist-mono',
  weight: '100 900',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Junior — Hands-Free Guide Assistant',
  description: 'Load any guide and run a hands-free voice session against it.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`theme-dark accent-amber ${geistSans.variable} ${geistMono.variable}`}
    >
      <body style={{ fontFamily: 'var(--font-geist-sans, var(--font-sans))' }}>
        {children}
      </body>
    </html>
  )
}
