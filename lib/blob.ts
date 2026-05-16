import { put } from '@vercel/blob'

export async function uploadImage(filename: string, data: Buffer): Promise<string> {
  const { url } = await put(filename, data, { access: 'public' })
  return url
}
