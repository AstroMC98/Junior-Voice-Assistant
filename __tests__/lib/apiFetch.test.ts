import { apiFetch, ApiKeyError } from '@/lib/apiFetch'

global.fetch = jest.fn()

describe('apiFetch', () => {
  beforeEach(() => jest.clearAllMocks())

  it('injects X-Api-Key header', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({ status: 200, ok: true })

    await apiFetch('http://test/api/guides', 'sk-test-key')

    const [, options] = (global.fetch as jest.Mock).mock.calls[0]
    const headers = new Headers(options.headers as HeadersInit)
    expect(headers.get('X-Api-Key')).toBe('sk-test-key')
  })

  it('throws ApiKeyError on 401', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({ status: 401, ok: false })

    await expect(apiFetch('http://test/api/guides', 'bad-key'))
      .rejects.toBeInstanceOf(ApiKeyError)
  })

  it('returns response on success', async () => {
    const mockResponse = { status: 200, ok: true }
    ;(global.fetch as jest.Mock).mockResolvedValue(mockResponse)

    const result = await apiFetch('http://test/api/guides', 'sk-test-key')
    expect(result).toBe(mockResponse)
  })

  it('merges existing headers with X-Api-Key', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({ status: 200, ok: true })

    await apiFetch('http://test/api/guides', 'sk-test-key', {
      headers: { 'Content-Type': 'application/json' },
    })

    const [, options] = (global.fetch as jest.Mock).mock.calls[0]
    const headers = new Headers(options.headers as HeadersInit)
    expect(headers.get('X-Api-Key')).toBe('sk-test-key')
    expect(headers.get('Content-Type')).toBe('application/json')
  })
})
