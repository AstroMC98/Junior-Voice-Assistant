import { NextRequest, NextResponse } from 'next/server'

export async function GET(req: NextRequest) {
  const url = req.nextUrl.searchParams.get('url')
  if (!url) return NextResponse.json({ error: 'Missing url param' }, { status: 400 })

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
