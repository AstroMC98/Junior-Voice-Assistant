jest.mock('nanoid', () => ({
  nanoid: jest.fn((size = 10) => 'a'.repeat(size)),
}))

import { generateId } from '@/lib/nanoid'
import { nanoid } from 'nanoid'

const mockNanoid = nanoid as jest.Mock

describe('generateId', () => {
  afterEach(() => {
    jest.clearAllMocks()
  })

  it('returns a string of length 10 by default', () => {
    mockNanoid.mockImplementation((size = 10) => 'a'.repeat(size))
    const id = generateId()
    expect(typeof id).toBe('string')
    expect(id).toHaveLength(10)
    expect(mockNanoid).toHaveBeenCalledWith(10)
  })

  it('returns a string of a custom length', () => {
    mockNanoid.mockImplementation((size = 10) => 'b'.repeat(size))
    const id = generateId(6)
    expect(id).toHaveLength(6)
    expect(mockNanoid).toHaveBeenCalledWith(6)
  })

  it('generates unique values', () => {
    let callCount = 0
    mockNanoid.mockImplementation((size = 10) => {
      return String(callCount++).padStart(size, 'a')
    })
    const ids = new Set(Array.from({ length: 200 }, () => generateId()))
    expect(ids.size).toBe(200)
  })
})
