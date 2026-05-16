import { NextRequest, NextResponse } from 'next/server'
import { getGuide, saveGuide } from '@/lib/kv'
import { generateId } from '@/lib/nanoid'
import type { Guide } from '@/lib/types'

type Params = { params: { id: string } }

export async function GET(_req: NextRequest, { params }: Params) {
  const guide = await getGuide(params.id)
  if (!guide) return NextResponse.json({ error: 'Not found' }, { status: 404 })
  return NextResponse.json(guide)
}

export async function POST(_req: NextRequest, { params }: Params) {
  const original = await getGuide(params.id)
  if (!original) return NextResponse.json({ error: 'Not found' }, { status: 404 })

  const fork: Guide = {
    ...original,
    id: generateId(),
    fork_of: original.id,
    created_at: Date.now(),
  }

  await saveGuide(fork)
  return NextResponse.json(fork, { status: 201 })
}
