// Thin client for the final backend (docs/API.md). Every error carries an Arabic message.
const BASE = import.meta.env.VITE_API_BASE || ''

export class ApiError extends Error {
  constructor(message, { code = null, status = 0, issues = null } = {}) {
    super(message)
    this.code = code
    this.status = status
    this.issues = issues
  }
}

async function call(url, opts) {
  let res
  try {
    res = await fetch(BASE + url, opts)
  } catch {
    throw new ApiError('تعذّر الاتصال بالخادم. تأكّد من تشغيل الواجهة الخلفية.', { code: 'network' })
  }
  let body = null
  try {
    body = await res.json()
  } catch {
    body = null
  }
  if (!res.ok) {
    const e = body?.error || {}
    throw new ApiError(e.message_ar || `حدث خطأ غير متوقّع في الخادم (${res.status}).`, {
      code: e.code || null,
      status: res.status,
      issues: e.issues || body?.issues || null,
    })
  }
  if (body == null) throw new ApiError('ردّ الخادم غير صالح.', { code: 'bad_response', status: res.status })
  return body
}

export const getHealth = () => call('/api/health')
export const getReady = () => call('/api/ready')
export const getTaxonomy = () => call('/api/taxonomy')

export function analyzeImage(file) {
  const fd = new FormData()
  fd.append('image', file)
  return call('/api/analyze', { method: 'POST', body: fd })
}

export function recommend(payload) {
  return call('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
