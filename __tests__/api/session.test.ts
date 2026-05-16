jest.mock('@/lib/claude', () => ({ sessionTurn: jest.fn() }))

import { POST as sessionPost } from '@/app/api/session/route'
import { NextRequest } from 'next/server'
import { sessionTurn } from '@/lib/claude'

const mockGuide = {
  id: 'g1',
  title: 'Test',
  source: 'url' as const,
  steps: [{ index: 0, title: 'S1', content: 'C1' }],
  created_at: 0,
}

describe('POST /api/session', () => {
  beforeEach(() => jest.clearAllMocks())

  it('calls sessionTurn and returns the result', async () => {
    ;(sessionTurn as jest.Mock).mockResolvedValue({
      speech: 'Got it!',
      action: null,
      step: null,
    })

    const req = new NextRequest('http://localhost/api/session', {
      method: 'POST',
      body: JSON.stringify({ guide: mockGuide, currentStepIndex: 0, transcript: 'hello' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await sessionPost(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.speech).toBe('Got it!')
    expect(sessionTurn).toHaveBeenCalledWith(mockGuide, 0, 'hello', undefined)
  })

  it('passes photo through to sessionTurn when provided', async () => {
    ;(sessionTurn as jest.Mock).mockResolvedValue({
      speech: 'Looks correct!',
      action: null,
      step: null,
    })

    const req = new NextRequest('http://localhost/api/session', {
      method: 'POST',
      body: JSON.stringify({
        guide: mockGuide,
        currentStepIndex: 0,
        transcript: 'Check my progress',
        photo: 'base64photo',
      }),
      headers: { 'Content-Type': 'application/json' },
    })

    await sessionPost(req)
    expect(sessionTurn).toHaveBeenCalledWith(mockGuide, 0, 'Check my progress', 'base64photo')
  })

  it('returns 400 when required fields are missing', async () => {
    const req = new NextRequest('http://localhost/api/session', {
      method: 'POST',
      body: JSON.stringify({ guide: mockGuide }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await sessionPost(req)
    expect(res.status).toBe(400)
  })
})
