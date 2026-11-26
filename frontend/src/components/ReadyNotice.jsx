import React from 'react'

// Model / corpus readiness from GET /api/ready, shown on load.
export default function ReadyNotice({ ready, error, loading, onRetry, taxonomyError }) {
  if (error) {
    return (
      <div className="alert" role="alert">
        <strong>الخادم غير متاح: </strong>
        {error.message}
        <button className="btn ghost inline" onClick={onRetry} disabled={loading}>
          {loading ? 'جارٍ الفحص…' : 'إعادة المحاولة'}
        </button>
      </div>
    )
  }
  if (!ready) return null
  const m = ready.model || {}
  const c = ready.corpus || {}
  const notes = []
  if (!m.loaded) {
    notes.push(
      <p key="m">
        <strong>نموذج الرؤية غير جاهز</strong>؛ رفع الصور معطَّل حتى يُحمَّل.
        {m.error && <span className="muted small"> ({m.error})</span>}
      </p>
    )
  }
  if (!c.loaded) {
    notes.push(
      <p key="c">
        <strong>مدوّنة الأبيات غير جاهزة</strong>؛ يمكن تحليل الصورة لكن لا يمكن اقتراح أبيات الآن.
        {c.error && <span className="muted small"> ({c.error})</span>}
      </p>
    )
  }
  if (taxonomyError) {
    notes.push(<p key="t">تعذّر تحميل أسماء التصنيفات ({taxonomyError.message})؛ ستظهر المعرّفات بدل الأسماء العربية.</p>)
  }
  if (!notes.length) return null
  return (
    <div className="note warn block" role="status">
      {notes}
      <button className="btn ghost inline" onClick={onRetry} disabled={loading}>
        {loading ? 'جارٍ الفحص…' : 'إعادة الفحص'}
      </button>
    </div>
  )
}
