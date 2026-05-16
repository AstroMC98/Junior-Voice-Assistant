jest.mock('@vercel/blob', () => ({
  put: jest.fn(),
}))

import { uploadImage } from '@/lib/blob'
import { put } from '@vercel/blob'

const mockPut = put as jest.Mock

describe('uploadImage', () => {
  it('calls put with filename, buffer, and public access; returns URL', async () => {
    mockPut.mockResolvedValue({ url: 'https://blob.vercel-storage.com/abc.png' })
    const buf = Buffer.from('fake-image')
    const url = await uploadImage('abc.png', buf)
    expect(mockPut).toHaveBeenCalledWith('abc.png', buf, { access: 'public' })
    expect(url).toBe('https://blob.vercel-storage.com/abc.png')
  })
})
