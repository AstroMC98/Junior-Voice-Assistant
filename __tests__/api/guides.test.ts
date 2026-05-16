jest.mock('@/lib/claude', () => ({ processGuide: jest.fn() }))
jest.mock('@/lib/kv', () => ({ getGuide: jest.fn(), saveGuide: jest.fn() }))
jest.mock('@/lib/blob', () => ({ uploadImage: jest.fn() }))
jest.mock('@/lib/nanoid', () => ({ generateId: jest.fn() }))

import { POST as createGuide } from '@/app/api/guides/route'
import { GET as getGuideById, POST as forkGuide } from '@/app/api/guides/[id]/route'
import { NextRequest } from 'next/server'
import { processGuide } from '@/lib/claude'
import { getGuide, saveGuide } from '@/lib/kv'
import { uploadImage } from '@/lib/blob'
import { generateId } from '@/lib/nanoid'

describe('POST /api/guides', () => {
  beforeEach(() => jest.clearAllMocks())

  it('creates a guide from URL text, saves to KV, returns 201', async () => {
    ;(processGuide as jest.Mock).mockResolvedValue([
      { index: 0, title: 'Step 1', content: 'Do this' },
    ])
    ;(generateId as jest.Mock).mockReturnValue('guide-id-1')
    ;(saveGuide as jest.Mock).mockResolvedValue(undefined)

    const req = new NextRequest('http://localhost/api/guides', {
      method: 'POST',
      body: JSON.stringify({ source: 'url', title: 'My Guide', text: 'Some text' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await createGuide(req)
    const body = await res.json()

    expect(res.status).toBe(201)
    expect(body.id).toBe('guide-id-1')
    expect(body.title).toBe('My Guide')
    expect(body.source).toBe('url')
    expect(body.steps).toHaveLength(1)
    expect(saveGuide).toHaveBeenCalledWith(expect.objectContaining({ id: 'guide-id-1' }))
  })

  it('uploads page images to Blob and attaches URLs to steps', async () => {
    ;(processGuide as jest.Mock).mockResolvedValue([
      { index: 0, title: 'Step 1', content: 'Do this', image_index: 0 },
    ])
    ;(generateId as jest.Mock)
      .mockReturnValueOnce('img-id-1')
      .mockReturnValueOnce('guide-id-2')
    ;(uploadImage as jest.Mock).mockResolvedValue('https://blob.example.com/img-id-1.png')
    ;(saveGuide as jest.Mock).mockResolvedValue(undefined)

    const req = new NextRequest('http://localhost/api/guides', {
      method: 'POST',
      body: JSON.stringify({ source: 'pdf', title: 'PDF Guide', images: ['base64data'] }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await createGuide(req)
    const body = await res.json()

    expect(uploadImage).toHaveBeenCalledWith('img-id-1.png', expect.any(Buffer))
    expect(body.steps[0].image_url).toBe('https://blob.example.com/img-id-1.png')
  })
})

describe('GET /api/guides/[id]', () => {
  beforeEach(() => jest.clearAllMocks())

  it('returns the guide when found', async () => {
    const mockGuide = { id: 'abc', title: 'G', source: 'url', steps: [], created_at: 0 }
    ;(getGuide as jest.Mock).mockResolvedValue(mockGuide)

    const req = new NextRequest('http://localhost/api/guides/abc')
    const res = await getGuideById(req, { params: { id: 'abc' } })
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body).toEqual(mockGuide)
  })

  it('returns 404 when guide is not found', async () => {
    ;(getGuide as jest.Mock).mockResolvedValue(null)
    const req = new NextRequest('http://localhost/api/guides/nope')
    const res = await getGuideById(req, { params: { id: 'nope' } })
    expect(res.status).toBe(404)
  })
})

describe('POST /api/guides/[id] (fork)', () => {
  beforeEach(() => jest.clearAllMocks())

  it('creates a fork with a new ID and fork_of set to original', async () => {
    const original = {
      id: 'orig',
      title: 'Original',
      source: 'url',
      steps: [{ index: 0, title: 'S', content: 'C' }],
      created_at: 100,
    }
    ;(getGuide as jest.Mock).mockResolvedValue(original)
    ;(generateId as jest.Mock).mockReturnValue('fork-id')
    ;(saveGuide as jest.Mock).mockResolvedValue(undefined)

    const req = new NextRequest('http://localhost/api/guides/orig', { method: 'POST' })
    const res = await forkGuide(req, { params: { id: 'orig' } })
    const body = await res.json()

    expect(res.status).toBe(201)
    expect(body.id).toBe('fork-id')
    expect(body.fork_of).toBe('orig')
    expect(body.title).toBe('Original')
    expect(body.steps).toHaveLength(1)
  })

  it('returns 404 if original guide is not found', async () => {
    ;(getGuide as jest.Mock).mockResolvedValue(null)
    const req = new NextRequest('http://localhost/api/guides/nope', { method: 'POST' })
    const res = await forkGuide(req, { params: { id: 'nope' } })
    expect(res.status).toBe(404)
  })
})
