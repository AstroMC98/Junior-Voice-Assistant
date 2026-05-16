import { NextRequest, NextResponse } from 'next/server'
import { processGuide } from '@/lib/claude'
import { saveGuide } from '@/lib/kv'
import { uploadImage } from '@/lib/blob'
import { generateId } from '@/lib/nanoid'
import type { Guide, Step } from '@/lib/types'

export async function POST(req: NextRequest) {
  const body = await req.json() as {
    source: 'pdf' | 'url' | 'camera'
    title: string
    text?: string
    images?: string[]
  }
  const { source, title, text, images } = body

  // Upload page images to Blob first so image_index values can be resolved to URLs
  const imageUrls: string[] = []
  if (images && images.length > 0) {
    for (const img of images) {
      const buf = Buffer.from(img, 'base64')
      const url = await uploadImage(`${generateId()}.png`, buf)
      imageUrls.push(url)
    }
  }

  const rawSteps = await processGuide(source, { text, images })

  const steps: Step[] = rawSteps.map(step => ({
    ...step,
    image_url:
      step.image_index !== undefined ? imageUrls[step.image_index] : undefined,
  }))

  const guide: Guide = {
    id: generateId(),
    title,
    source,
    steps,
    created_at: Date.now(),
  }

  await saveGuide(guide)
  return NextResponse.json(guide, { status: 201 })
}
