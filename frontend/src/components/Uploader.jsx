import React, { useEffect, useRef, useState } from 'react'
import { msNum } from '../labels.js'

const ACCEPT = 'image/jpeg,image/png,image/webp,image/bmp'

// The upload is an arched window: empty, it invites a photo; filled, it frames the photo while the model reads it.
export default function Uploader({ onFile, preview, busy, analysis, onReset, disabled, disabledReason, variant = 'hero' }) {
  const input = useRef(null)
  const [drag, setDrag] = useState(false)
  const [reading, setReading] = useState(false)
  const [broken, setBroken] = useState(false)
  const blocked = disabled || busy

  useEffect(() => {
    setReading(!!preview)
    setBroken(false)
  }, [preview])

  const open = () => {
    if (!blocked) input.current?.click()
  }
  const pick = (f) => {
    if (f && !blocked) onFile(f)
  }
  const dragProps = {
    onDragOver: (e) => { e.preventDefault(); if (!blocked) setDrag(true) },
    onDragLeave: () => setDrag(false),
    onDrop: (e) => { e.preventDefault(); setDrag(false); pick(e.dataTransfer.files?.[0]) },
  }
  const fileInput = (
    <input ref={input} type="file" accept={ACCEPT} hidden
      onChange={(e) => { pick(e.target.files?.[0]); e.target.value = '' }} />
  )

  if (!preview) {
    return (
      <div className={'window-wrap ' + variant}>
        <div
          className={'window empty' + (drag ? ' drag' : '') + (blocked ? ' disabled' : '')}
          onClick={open}
          {...dragProps}
          role="button"
          tabIndex={blocked ? -1 : 0}
          aria-disabled={blocked}
          onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); open() } }}
          aria-label="ارفع صورة"
        >
          <span className="window-glass" aria-hidden="true" />
          <span className="window-inner">
            <svg className="window-icon" viewBox="0 0 48 48" aria-hidden="true">
              <path d="M24 33V15M16 22l8-8 8 8" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
              <path d="M10 36h28" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity=".7" />
            </svg>
            <span className="window-title">{drag ? 'أفلِت الصورة هنا' : 'ضع صورتك في هذه النافذة'}</span>
            <span className="window-sub">اسحبها إلى هنا، أو <u>اخترها من جهازك</u></span>
            <span className="window-hint">JPEG · PNG · WebP</span>
            {disabled && disabledReason && <span className="window-hint warn-text">{disabledReason}</span>}
          </span>
        </div>
        {fileInput}
      </div>
    )
  }

  const t = analysis?.timings_ms
  return (
    <figure className={'window-wrap framed' + (drag ? ' drag' : '')} {...dragProps}>
      <div className="window filled">
        {!broken ? (
          <img src={preview} alt="الصورة المرفوعة" onLoad={() => setReading(false)}
            onError={() => { setReading(false); setBroken(true) }} />
        ) : (
          <div className="img-broken">تعذّر عرض هذه الصورة في المتصفح.</div>
        )}
        {(busy || reading) && (
          <div className="window-state" role="status" aria-live="polite">
            <span className="shimmer" aria-hidden="true" />
            <span className="window-state-text">{reading ? 'نقرأ الصورة…' : 'يتأمّل النموذج الصورة…'}</span>
          </div>
        )}
        {drag && <div className="window-drop">أفلِت الصورة لاستبدالها</div>}
      </div>
      <figcaption className="window-caption">
        <span className="row-actions">
          <button className="link-btn" onClick={open} disabled={blocked}>صورة أخرى</button>
          <span className="dot-sep" aria-hidden="true">·</span>
          <button className="link-btn" onClick={onReset} disabled={busy}>البدء من جديد</button>
        </span>
        {t && (
          <span className="tiny" title="زمن التحليل في الخادم">
            قرأها النموذج في <bdi dir="ltr">{msNum(t.inference)}</bdi> ملّي ثانية
          </span>
        )}
      </figcaption>
      {disabled && disabledReason && <p className="tiny warn-text">{disabledReason}</p>}
      {fileInput}
    </figure>
  )
}
