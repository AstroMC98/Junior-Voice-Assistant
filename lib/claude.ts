import Anthropic from '@anthropic-ai/sdk'
import type { Guide, Step, SessionResponse } from './types'

let _anthropic: Anthropic | null = null

function getClient(): Anthropic {
  if (!_anthropic) {
    _anthropic = new Anthropic()
  }
  return _anthropic
}

function extractJSON<T>(text: string): T {
  const clean = text
    .replace(/^```(?:json)?\s*/m, '')
    .replace(/\s*```\s*$/m, '')
    .trim()
  return JSON.parse(clean) as T
}

export async function processGuide(
  source: 'pdf' | 'url' | 'camera',
  content: { text?: string; images?: string[] }
): Promise<Step[]> {
  const userContent: Anthropic.ContentBlockParam[] = []

  if (content.images && content.images.length > 0) {
    content.images.forEach((img, i) => {
      userContent.push({
        type: 'image',
        source: { type: 'base64', media_type: 'image/png', data: img },
      } as unknown as Anthropic.ContentBlockParam)
      userContent.push({ type: 'text', text: `[Page ${i}]` })
    })
    userContent.push({
      type: 'text',
      text: 'Extract all ordered steps from this guide. For steps associated with an image, set image_index to that [Page N] number.',
    })
  } else {
    userContent.push({ type: 'text', text: content.text ?? '' })
  }

  const response = await getClient().messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    system: `Extract ordered steps from this guide document.
Return ONLY a valid JSON array. Each element must follow this shape exactly:
{ "index": number, "title": string, "content": string, "image_index"?: number, "crop"?: { "x": number, "y": number, "w": number, "h": number } }
image_index refers to which [Page N] label the step's image appears on.
crop is the relevant region of that page image as percentage of image dimensions (0-100).
No markdown, no prose — JSON array only.`,
    messages: [{ role: 'user', content: userContent }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '[]'
  return extractJSON<Step[]>(text)
}

export async function sessionTurn(
  guide: Guide,
  currentStepIndex: number,
  transcript: string,
  photo?: string
): Promise<SessionResponse> {
  const step = guide.steps[currentStepIndex]
  const userContent: Anthropic.ContentBlockParam[] = []

  if (photo) {
    userContent.push({
      type: 'image',
      source: { type: 'base64', media_type: 'image/jpeg', data: photo },
    } as unknown as Anthropic.ContentBlockParam)
  }
  userContent.push({ type: 'text', text: transcript })

  const stepsContext = guide.steps
    .map(s => `Step ${s.index + 1}: ${s.title} — ${s.content}`)
    .join('\n')

  const response = await getClient().messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 512,
    system: `You are Junior, a hands-free guide assistant.
Guide: "${guide.title}"
All steps:
${stepsContext}

Current step: ${step.index + 1} of ${guide.steps.length} — ${step.title}: ${step.content}

Rules:
- Respond in 1-2 sentences, naturally spoken
- If the user says "next", "done", or "continue": set action to "advance", step to the next 0-based step index (current + 1)
- If the user says "go back", "back", or "previous": set action to "advance", step to the previous 0-based index (current - 1, minimum 0)
- If the user asks to see something visually ("show me", "what does it look like"): set action to "show_image", step to current 0-based index
- On a camera photo: assess whether it matches the current step; give clear go/no-go feedback
- Always respond as valid JSON only — no prose outside the JSON:
  { "speech": "...", "action": "show_image" | "advance" | null, "step": <0-based number or null> }`,
    messages: [{ role: 'user', content: userContent }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return extractJSON<SessionResponse>(text)
}
