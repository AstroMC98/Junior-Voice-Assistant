jest.mock('@vercel/kv', () => ({
  kv: {
    get: jest.fn(),
    set: jest.fn(),
  },
}))

import { getGuide, saveGuide } from '@/lib/kv'
import { kv } from '@vercel/kv'
import type { Guide } from '@/lib/types'

const mockGet = kv.get as jest.Mock
const mockSet = kv.set as jest.Mock

const mockGuide: Guide = {
  id: 'test123',
  title: 'Test Guide',
  source: 'url',
  steps: [{ index: 0, title: 'Step 1', content: 'Do this' }],
  created_at: 1700000000000,
}

describe('kv helpers', () => {
  beforeEach(() => jest.clearAllMocks())

  it('getGuide calls kv.get with prefixed key and returns guide', async () => {
    mockGet.mockResolvedValue(mockGuide)
    const result = await getGuide('test123')
    expect(mockGet).toHaveBeenCalledWith('guide:test123')
    expect(result).toEqual(mockGuide)
  })

  it('getGuide returns null when key not found', async () => {
    mockGet.mockResolvedValue(null)
    const result = await getGuide('missing')
    expect(result).toBeNull()
  })

  it('saveGuide calls kv.set with prefixed key and guide value', async () => {
    mockSet.mockResolvedValue('OK')
    await saveGuide(mockGuide)
    expect(mockSet).toHaveBeenCalledWith('guide:test123', mockGuide)
  })
})
