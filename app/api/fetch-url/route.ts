import { NextRequest, NextResponse } from 'next/server'

const BLOCKED_HOST_RE = /^(localhost|127\.|10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|169\.254\.|::1$|0\.0\.0\.0)/i

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url')
  if (!url) return NextResponse.json({ error: 'Missing url param' }, { status: 400 })

  let parsed: URL
  try {
    parsed = new URL(url)
  } catch {
    return NextResponse.json({ error: 'Invalid URL' }, { status: 400 })
  }

  if (!['http:', 'https:'].includes(parsed.protocol)) {
    return NextResponse.json({ error: 'Only http/https allowed' }, { status: 403 })
  }
  if (BLOCKED_HOST_RE.test(parsed.hostname)) {
    return NextResponse.json({ error: 'Forbidden URL' }, { status: 403 })
  }

  let res: Response
  try {
    res = await fetch(url, { headers: { 'User-Agent': 'Junior-Bot/1.0' } })
  } catch {
    return NextResponse.json({ error: 'Fetch failed' }, { status: 502 })
  }

  if (!res.ok) return NextResponse.json({ error: `Upstream ${res.status}` }, { status: 502 })

  const html = await res.text()
  const text = html
    .replace(/<style[^>]*>[\s\S]*?<\/style>/gi, '')
    .replace(/<script[^>]*>[\s\S]*?<\/script>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 50_000)

  return NextResponse.json({ text })
}
