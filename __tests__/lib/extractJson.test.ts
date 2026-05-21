import { extractJson } from '@/lib/extractJson'

describe('extractJson', () => {
  it('extracts a valid JSON object from plain text', () => {
    const text = '{"speech": "hello", "action": null, "step": null}'
    expect(extractJson(text)).toEqual({ speech: 'hello', action: null, step: null })
  })

  it('extracts JSON embedded in surrounding prose', () => {
    const text = 'Here is my response: {"speech": "done", "action": "advance", "step": 2} end.'
    expect(extractJson(text)).toEqual({ speech: 'done', action: 'advance', step: 2 })
  })

  it('returns null for plain text with no JSON', () => {
    expect(extractJson('just some words')).toBeNull()
  })

  it('returns null for malformed JSON', () => {
    expect(extractJson('{broken json')).toBeNull()
  })

  it('returns null for empty string', () => {
    expect(extractJson('')).toBeNull()
  })
})
