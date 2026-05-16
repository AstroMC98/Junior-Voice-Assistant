export class ApiKeyError extends Error {
  constructor() {
    super('API key required')
    this.name = 'ApiKeyError'
  }
}

export async function apiFetch(
  url: string,
  apiKey: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers = new Headers(options.headers as HeadersInit | undefined)
  headers.set('X-Api-Key', apiKey)
  const res = await fetch(url, { ...options, headers })
  if (res.status === 401) throw new ApiKeyError()
  return res
}
