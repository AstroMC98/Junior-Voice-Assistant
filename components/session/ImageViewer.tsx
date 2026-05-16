'use client'
import { useRef, useEffect } from 'react'

interface Props {
  imageUrl: string
  crop?: { x: number; y: number; w: number; h: number }
}

export default function ImageViewer({ imageUrl, crop }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!crop || !canvasRef.current) return
    const canvas = canvasRef.current
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => {
      canvas.width = img.naturalWidth
      canvas.height = img.naturalHeight
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(img, 0, 0)

      const px = (crop.x / 100) * img.naturalWidth
      const py = (crop.y / 100) * img.naturalHeight
      const pw = (crop.w / 100) * img.naturalWidth
      const ph = (crop.h / 100) * img.naturalHeight

      ctx.fillStyle = 'rgba(96, 165, 250, 0.15)'
      ctx.fillRect(px, py, pw, ph)
      ctx.strokeStyle = 'rgba(96, 165, 250, 0.9)'
      ctx.lineWidth = Math.max(3, img.naturalWidth * 0.004)
      ctx.strokeRect(px, py, pw, ph)
    }
    img.src = imageUrl
  }, [imageUrl, crop])

  if (crop) {
    return (
      <canvas
        ref={canvasRef}
        className="w-full rounded-xl object-contain"
        style={{ maxHeight: '28rem' }}
      />
    )
  }

  return (
    <img
      src={imageUrl}
      alt="Step reference image"
      className="w-full rounded-xl object-contain"
      style={{ maxHeight: '28rem' }}
    />
  )
}
