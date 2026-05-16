import { nanoid } from 'nanoid'

export function generateId(size = 10): string {
  return nanoid(size)
}
