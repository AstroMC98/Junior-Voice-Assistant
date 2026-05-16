import { NextRequest, NextResponse } from 'next/server'
import { sessionTurn } from '@/lib/claude'
import type { Guide } from '@/lib/types'

export async function POST(req: NextRequest) {
  const body = await req.json() as {
    guide: Guide
    currentStepIndex: number
    transcript: string
    photo?: string
  }

  const { guide, currentStepIndex, transcript, photo } = body

  if (!guide || currentStepIndex === undefined || !transcript) {
    return NextResponse.json({ error: 'Missing required fields' }, { status: 400 })
  }

  if (
    !Array.isArray(guide.steps) ||
    currentStepIndex < 0 ||
    currentStepIndex >= guide.steps.length
  ) {
    return NextResponse.json({ error: 'Step index out of range' }, { status: 400 })
  }

  const result = await sessionTurn(guide, currentStepIndex, transcript, photo)
  return NextResponse.json(result)
}
