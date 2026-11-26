// Arabic names come from /api/taxonomy at runtime; these helpers only look them up.
export function buildNames(tax) {
  const names = new Map()
  if (!tax) return names
  for (const key of ['scene_groups', 'scenes', 'img_emotions', 'lit_emotions', 'exposed_tags']) {
    const list = Array.isArray(tax[key]) ? tax[key] : []
    for (const l of list) if (l && l.id) names.set(l.id, l.name_ar || l.name_en || l.id)
  }
  return names
}

export const nameOf = (names, id) => (id ? names.get(id) || id : '')

// Floored, never rounded up: 0.998 shows as 99%, never as 100%.
export const pct = (x) => (typeof x === 'number' ? `${Math.floor(x * 100)}%` : '—')
export const fix = (x, d = 2) => (typeof x === 'number' ? x.toFixed(d) : '—')
export const msNum = (x) => (typeof x !== 'number' ? '—' : x < 10 ? x.toFixed(1) : String(Math.round(x)))

export const SCENE_STATUS = {
  confident: { label: 'مشهد واضح', cls: '' },
  uncertain: { label: 'مشهد غير مؤكّد', cls: 'soft' },
  unsupported: { label: 'مشهد غير مدعوم', cls: 'warn' },
}

export const REVIEWED = new Set(['reviewed', 'double_reviewed', 'adjudicated'])

export const REVIEW_STATUS_AR = {
  not_reviewed: 'غير مراجَع',
  reviewed: 'مراجَع بشريًا',
  double_reviewed: 'مراجَع مرتين',
  adjudicated: 'محسوم بالتحكيم',
  disputed: 'متنازَع عليه',
  synthetic_fixture: 'بيانات اختبار',
}

export const TIER_AR = {
  1: 'تطابق الإحساس والعنصر البصري',
  2: 'تطابق بالدلالة أو الرمز',
  3: 'تطابق الإحساس وحده',
}

export const ABSTENTION_AR = {
  cell_not_covered: 'لا توجد أبيات معلَّمة لهذا المزيج من العنصر البصري والإحساس.',
  diversity_exhausted: 'استُبعدت المرشّحات المتبقية لقواعد التنويع (بيت واحد لكل قصيدة أو شاعر).',
  empty_corpus: 'لا توجد أبيات قابلة للعرض في هذا الوضع.',
  no_emotion_match: 'لا يوجد بيت معلَّم بالإحساس المختار.',
  no_visual_match_emotion_only_off: 'لا يطابق أي بيت العناصر المختارة، والاقتراح بالإحساس وحده غير مسموح.',
}

export const MODE_AR = { production: 'الإنتاج (أبيات مراجَعة فقط)', development: 'التطوير (مسودات آلية)' }

// One-line generic glosses for the literary emotions (UI help text only; says nothing about the corpus).
export const LIT_GLOSS = {
  'lit_emotion.sadness': 'أسى الفقد والألم وما يبقى بعد الغياب',
  'lit_emotion.longing': 'شوق إلى غائب، وحنين إلى ديار وأيام مضت',
  'lit_emotion.loneliness': 'بعد عن الأهل والوطن وإحساس بالانفراد',
  'lit_emotion.awe': 'دهشة أمام عظمة المشهد وجلاله',
  'lit_emotion.serenity': 'هدوء النفس وصفاؤها واطمئنانها',
  'lit_emotion.joy': 'فرح وانشراح وبهجة بالجمال',
  'lit_emotion.pride': 'اعتزاز بالنفس والقوم وحماسة للمجد',
  'lit_emotion.fear': 'رهبة وخوف من المجهول أو الخطر',
}

export const MODE_HELP = {
  production: 'الافتراضي: يعرض فقط الأبيات التي راجع إنسان تسمياتها، وقد تقتصر المراجعة على الإحساس.',
  development: 'يضيف مسودات آلية لم يراجعها إنسان، مع إفصاح دائم بأنها غير معتمدة.',
}

// Which dimensions of a displayed verse were reviewed by a human.
// Uses display.reviewed_dimensions when present; otherwise falls back to the record-level review status.
export function reviewState(item, display) {
  const status = item.review_status || display.review_status
  const dims = Array.isArray(display.reviewed_dimensions) ? display.reviewed_dimensions : null
  const has = (d) => (dims ? dims.includes(d) || dims.includes('all') : REVIEWED.has(status))
  return { status, emotion: has('emotion'), visual: has('visual'), dims }
}
