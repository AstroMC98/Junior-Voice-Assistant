import { kv } from '@vercel/kv'
import type { Guide } from './types'

export async function getGuide(id: string): Promise<Guide | null> {
  return kv.get<Guide>(`guide:${id}`)
}

export async function saveGuide(guide: Guide): Promise<void> {
  await kv.set(`guide:${guide.id}`, guide)
}
