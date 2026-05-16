const mockCreate = jest.fn()

jest.mock('@anthropic-ai/sdk', () => ({
  __esModule: true,
  default: jest.fn().mockImplementation(() => ({
    messages: { create: mockCreate },
  })),
}))

import { processGuide, sessionTurn } from '@/lib/claude'
import type { Guide } from '@/lib/types'

describe('processGuide', () => {
  beforeEach(() => jest.clearAllMocks())

  it('extracts steps from text content', async () => {
    mockCreate.mockResolvedValue({
      content: [{
        type: 'text',
        text: JSON.stringify([
          { index: 0, title: 'Step 1', content: 'Do thing 1' },
          { index: 1, title: 'Step 2', content: 'Do thing 2' },
        ]),
      }],
    })

    const steps = await processGuide('url', { text: 'Some guide text' })

    expect(steps).toHaveLength(2)
    expect(steps[0].title).toBe('Step 1')
    expect(steps[1].index).toBe(1)
    expect(mockCreate).toHaveBeenCalledWith(
      expect.objectContaining({ model: 'claude-sonnet-4-6', max_tokens: 4096 })
    )
  })

  it('strips markdown code fences from Claude response', async () => {
    mockCreate.mockResolvedValue({
      content: [{
        type: 'text',
        text: '```json\n[{"index":0,"title":"T","content":"C"}]\n```',
      }],
    })

    const steps = await processGuide('url', { text: 'text' })
    expect(steps).toHaveLength(1)
    expect(steps[0].title).toBe('T')
  })

  it('sends images as vision blocks when provided', async () => {
    mockCreate.mockResolvedValue({
      content: [{ type: 'text', text: '[]' }],
    })

    await processGuide('pdf', { images: ['base64img1', 'base64img2'] })

    const callArgs = mockCreate.mock.calls[0][0]
    const userContent = callArgs.messages[0].content
    const imageBlocks = userContent.filter((b: { type: string }) => b.type === 'image')
    expect(imageBlocks).toHaveLength(2)
    expect(imageBlocks[0].source.data).toBe('base64img1')
  })
})

describe('sessionTurn', () => {
  const guide: Guide = {
    id: 'abc',
    title: 'Test Guide',
    source: 'url',
    steps: [
      { index: 0, title: 'Step 1', content: 'First step' },
      { index: 1, title: 'Step 2', content: 'Second step' },
    ],
    created_at: 0,
  }

  beforeEach(() => jest.clearAllMocks())

  it('returns a structured SessionResponse', async () => {
    mockCreate.mockResolvedValue({
      content: [{
        type: 'text',
        text: JSON.stringify({ speech: 'Moving to step 2', action: 'advance', step: 1 }),
      }],
    })

    const result = await sessionTurn(guide, 0, 'next')

    expect(result.speech).toBe('Moving to step 2')
    expect(result.action).toBe('advance')
    expect(result.step).toBe(1)
  })

  it('includes photo as a vision block when provided', async () => {
    mockCreate.mockResolvedValue({
      content: [{ type: 'text', text: JSON.stringify({ speech: 'Looks good!', action: null, step: null }) }],
    })

    await sessionTurn(guide, 0, 'Check my progress', 'base64photodata')

    const callArgs = mockCreate.mock.calls[0][0]
    const userContent = callArgs.messages[0].content
    expect(userContent[0].type).toBe('image')
    expect(userContent[0].source.data).toBe('base64photodata')
  })
})
