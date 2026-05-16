export type Step = {
  index: number
  title: string
  content: string
  image_url?: string
  image_index?: number
  crop?: {
    x: number
    y: number
    w: number
    h: number
  }
}

export type Guide = {
  id: string
  title: string
  source: 'pdf' | 'url' | 'camera'
  steps: Step[]
  fork_of?: string
  created_at: number
}

export type SessionResponse = {
  speech: string
  action: 'show_image' | 'advance' | null
  step: number | null
}
