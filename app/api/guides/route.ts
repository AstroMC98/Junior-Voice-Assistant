import { NextRequest, NextResponse } from 'next/server'
import { processGuide } from '@/lib/claude'
import { saveGuide } from '@/lib/kv'
import { uploadImage } from '@/lib/blob'
import { generateId } from '@/lib/nanoid'
import type { Guide, Step } from '@/lib/types'

const VALID_SOURCES = ['pdf', 'url', 'camera'] as const

export async function POST(req: NextRequest) {
  let body: { source: string; title: string; text?: string; images?: string[] }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  const { source, title, text, images } = body

  if (!title || typeof title !== 'string' || !title.trim()) {
    return NextResponse.json({ error: 'title is required' }, { status: 400 })
  }
  if (!source || !VALID_SOURCES.includes(source as typeof VALID_SOURCES[number])) {
    return NextResponse.json({ error: 'source must be pdf, url, or camera' }, { status: 400 })
  }

  try {
    // Upload page images to Blob first so image_index values can be resolved to URLs
    const imageUrls: string[] = []
    if (images && images.length > 0) {
      for (const img of images) {
        const buf = Buffer.from(img, 'base64')
        const url = await uploadImage(`${generateId()}.png`, buf)
        imageUrls.push(url)
      }
    }

    const rawSteps = await processGuide(source as typeof VALID_SOURCES[number], { text, images })

    const steps: Step[] = rawSteps.map(step => ({
      ...step,
      image_url:
        step.image_index !== undefined ? imageUrls[step.image_index] : undefined,
    }))

    const guide: Guide = {
      id: generateId(),
      title: title.trim(),
      source: source as typeof VALID_SOURCES[number],
      steps,
      created_at: Date.now(),
    }

    await saveGuide(guide)
    return NextResponse.json(guide, { status: 201 })
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Guide creation failed'
    return NextResponse.json({ error: message }, { status: 500 })
  }
}
