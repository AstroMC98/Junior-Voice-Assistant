interface Props {
  imageUrl: string
  crop?: { x: number; y: number; w: number; h: number }
}

export default function ImageViewer({ imageUrl, crop }: Props) {
  if (crop) {
    return (
      <div className="placeholder-img" style={{ borderRadius: 'var(--r-md)' }}>
        {/* No objectFit/maxHeight here — image fills container width at natural ratio
            so that percentage-based crop coordinates align with actual image content. */}
        <img
          src={imageUrl}
          alt="Step reference image"
          style={{ width: '100%', display: 'block', height: 'auto' }}
        />
        <div
          className="crop-box"
          style={{
            left: `${crop.x}%`,
            top: `${crop.y}%`,
            width: `${crop.w}%`,
            height: `${crop.h}%`,
          }}
        >
          <span className="crop-label">Focus</span>
        </div>
      </div>
    )
  }

  return (
    <div style={{ borderRadius: 'var(--r-md)', overflow: 'hidden' }}>
      <img
        src={imageUrl}
        alt="Step reference image"
        style={{ width: '100%', display: 'block', maxHeight: '28rem', objectFit: 'contain' }}
      />
    </div>
  )
}
