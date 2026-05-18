'use client'
import { useState } from 'react'

interface Props {
  onCapture: (images: string[]) => void
}

export default function PdfUploader({ onCapture }: Props) {
  const [status, setStatus] = useState<'idle' | 'loading' | 'error'>('idle')
  const [pageCount, setPageCount] = useState(0)
  const [current, setCurrent] = useState(0)

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setStatus('loading')
    setCurrent(0)

    try {
      const pdfjsLib = await import('pdfjs-dist')
      pdfjsLib.GlobalWorkerOptions.workerSrc =
        `https://unpkg.com/pdfjs-dist@${pdfjsLib.version}/build/pdf.worker.min.mjs`

      const arrayBuffer = await file.arrayBuffer()
      const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise
      setPageCount(pdf.numPages)

      const images: string[] = []
      for (let i = 1; i <= pdf.numPages; i++) {
        setCurrent(i)
        const page = await pdf.getPage(i)
        const viewport = page.getViewport({ scale: 1.5 })
        const canvas = document.createElement('canvas')
        canvas.width = viewport.width
        canvas.height = viewport.height
        await page.render({ canvasContext: canvas.getContext('2d')!, viewport }).promise
        images.push(canvas.toDataURL('image/png').split(',')[1])
      }

      setStatus('idle')
      onCapture(images)
    } catch (err) {
      console.error('PDF render error:', err)
      setStatus('error')
    }
  }

  return (
    <div className="space-y-2">
      <input
        type="file"
        accept="application/pdf"
        onChange={handleFile}
        disabled={status === 'loading'}
        className="block w-full text-sm text-slate-400
          file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0
          file:bg-blue-600 file:text-white file:font-medium
          hover:file:bg-blue-700 file:cursor-pointer disabled:opacity-50"
      />
      {status === 'loading' && (
        <p className="text-slate-400 text-sm animate-pulse">
          Rendering page {current}{pageCount > 0 ? ` of ${pageCount}` : ''}…
        </p>
      )}
      {status === 'error' && (
        <p className="text-red-400 text-sm">
          Failed to render PDF. Check the browser console for details.
        </p>
      )}
    </div>
  )
}
