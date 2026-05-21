import type { SessionResponse } from '@/lib/types'

export function extractJson(text: string): SessionResponse | null {
  const match = text.match(/\{[\s\S]*?\}/)
  if (!match) return null
  try {
    return JSON.parse(match[0]) as SessionResponse
  } catch {
    return null
  }
}
