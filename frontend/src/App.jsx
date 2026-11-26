import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { analyzeImage, getReady, getTaxonomy, recommend } from './api.js'
import { buildNames, MODE_AR } from './labels.js'
import Khatim, { Logo, Rule } from './components/Khatim.jsx'
import Uploader from './components/Uploader.jsx'
import AnalysisPanel from './components/AnalysisPanel.jsx'
import ConfirmPanel from './components/ConfirmPanel.jsx'
import Results from './components/Results.jsx'
import ReadyNotice from './components/ReadyNotice.jsx'

const emptyChoices = {
  litEmotion: null,
  secondary: null,
  items: {}, // id -> true (checked)
  focusId: null,
  symbolic: false,
  emotionOnly: false,
}

export default function App() {
  const [ready, setReady] = useState(null) // /api/ready body
  const [readyError, setReadyError] = useState(null)
  const [readyLoading, setReadyLoading] = useState(true)
  const [taxonomy, setTaxonomy] = useState(null)
  const [taxonomyError, setTaxonomyError] = useState(null)

  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState(null)
  const [analyzeError, setAnalyzeError] = useState(null)

  const [choices, setChoices] = useState(emptyChoices)
  const [mode, setMode] = useState('production')

  const [requested, setRequested] = useState(false) // after the first request, changes re-run automatically
  const [recLoading, setRecLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [recError, setRecError] = useState(null)
  const [expired, setExpired] = useState(false)
  const reqSeq = useRef(0)
  const resultsRef = useRef(null)
  const modeInit = useRef(false) // the default mode from /api/ready is applied once, never over a user choice

  const loadReady = useCallback(async () => {
    setReadyLoading(true)
    try {
      const r = await getReady()
      setReady(r)
      setReadyError(null)
      if (!modeInit.current && r.default_mode && (r.modes || []).includes(r.default_mode)) {
        modeInit.current = true
        setMode(r.default_mode)
      }
    } catch (e) {
      setReady(null)
      setReadyError(e)
    } finally {
      setReadyLoading(false)
    }
    try {
      const t = await getTaxonomy()
      setTaxonomy(t)
      setTaxonomyError(null)
    } catch (e) {
      setTaxonomyError(e)
    }
  }, [])
  useEffect(() => {
    loadReady()
  }, [loadReady])

  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])

  const names = useMemo(() => buildNames(taxonomy), [taxonomy])
  const modelLoaded = !!ready?.model?.loaded
  const corpusLoaded = !!ready?.corpus?.loaded

  const resetResults = () => {
    reqSeq.current += 1
    setRequested(false)
    setResult(null)
    setRecError(null)
    setRecLoading(false)
    setExpired(false)
  }

  const runAnalysis = async (f) => {
    setAnalysis(null)
    setAnalyzeError(null)
    resetResults()
    setChoices(emptyChoices)
    setAnalyzing(true)
    try {
      const a = await analyzeImage(f)
      setAnalysis(a)
      const sugg = a.suggestion || {}
      const items = {}
      for (const v of sugg.visual_items || []) items[v.id] = true
      const lit = null // never preselected: the literary emotion is the user's choice (suggestions are only marked)
      setChoices({
        ...emptyChoices,
        litEmotion: lit,
        items,
        emotionOnly: Object.keys(items).length === 0,
      })
    } catch (e) {
      setAnalyzeError(e)
      if (e.code === 'model_not_ready') loadReady()
    } finally {
      setAnalyzing(false)
    }
  }

  const onFile = (f) => {
    if (!f) return
    if (preview) URL.revokeObjectURL(preview)
    setFile(f)
    setPreview(URL.createObjectURL(f))
    runAnalysis(f)
  }

  const reset = () => {
    if (preview) URL.revokeObjectURL(preview)
    setFile(null)
    setPreview(null)
    setAnalysis(null)
    setAnalyzeError(null)
    setChoices(emptyChoices)
    resetResults()
  }

  const checkedIds = Object.keys(choices.items).filter((id) => choices.items[id])
  const payload = useMemo(() => {
    if (!analysis || !choices.litEmotion) return null
    const ids = Object.keys(choices.items).filter((id) => choices.items[id])
    const focus = ids.includes(choices.focusId) ? choices.focusId : null
    return {
      analysis_id: analysis.analysis_id,
      selected_lit_emotion: choices.litEmotion,
      secondary_lit_emotion:
        choices.secondary && choices.secondary !== choices.litEmotion ? choices.secondary : null,
      confirmed_visual_items: ids.map((id) => ({ id, user_selection: id === focus ? 'focus' : 'primary' })),
      symbolic_allowed: !!choices.symbolic,
      // the contract requires emotion-only when no visual item is confirmed
      emotion_only_allowed: ids.length === 0 ? true : !!choices.emotionOnly,
      mode,
    }
  }, [analysis, choices, mode])
  const payloadKey = payload ? JSON.stringify(payload) : ''

  const doRecommend = useCallback(async (p) => {
    if (!p) return
    const seq = ++reqSeq.current
    setRecLoading(true)
    setRecError(null)
    try {
      const r = await recommend(p)
      if (seq !== reqSeq.current) return
      setResult(r)
      setExpired(false)
    } catch (e) {
      if (seq !== reqSeq.current) return
      if (e.status === 404 || e.code === 'analysis_not_found') {
        setExpired(e)
        setResult(null)
      } else {
        setRecError(e)
        if (e.code === 'corpus_not_ready') loadReady()
      }
    } finally {
      if (seq === reqSeq.current) setRecLoading(false)
    }
  }, [loadReady])

  // re-run with the same analysis_id whenever a choice or the mode changes after the first request
  useEffect(() => {
    if (!requested || expired || !payload) return
    const t = setTimeout(() => doRecommend(payload), 250)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [payloadKey, requested])

  const onSubmit = () => {
    if (!payload) return
    if (requested) {
      doRecommend(payload)
    } else {
      setRequested(true) // the effect above sends the first request
    }
    setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80)
  }

  const reanalyzeSame = () => {
    if (file) runAnalysis(file)
  }

  // one-click adjustments offered by the empty / abstained state; each re-runs /api/recommend via the effect above
  const adjust = {
    pickLit: (id) => setChoices((c) => ({ ...c, litEmotion: id, secondary: c.secondary === id ? null : c.secondary })),
    clearFocus: () => setChoices((c) => ({ ...c, focusId: null })),
    allowEmotionOnly: () => setChoices((c) => ({ ...c, emotionOnly: true })),
    allowSymbolic: () => setChoices((c) => ({ ...c, symbolic: true })),
    showDevelopment: () => setMode('development'), // explicit user click only
  }

  const statusPill = (() => {
    if (readyLoading && !ready) return { cls: '', text: 'جارٍ فحص الخادم…' }
    if (readyError) return { cls: 'warn', text: 'الخادم غير متصل' }
    if (ready?.ready) return { cls: 'ok', text: 'النظام جاهز' }
    return { cls: 'warn', text: 'بعض المكوّنات غير جاهزة' }
  })()

  const uploadDisabledReason = readyError
    ? 'الخادم غير متصل؛ لا يمكن تحليل الصور الآن.'
    : ready && !modelLoaded
      ? 'نموذج الرؤية غير محمَّل بعد؛ الرفع معطَّل.'
      : readyLoading && !ready
        ? 'جارٍ فحص جاهزية النموذج…'
        : null

  const brand = (
    <a className="brand" href="/" onClick={(e) => { e.preventDefault(); reset() }} aria-label="رؤية الشعر: البداية">
      <Logo />
      <span className="brand-text">
        <span className="brand-name">رؤية الشعر</span>
        <span className="brand-latin" dir="ltr">POETRY · VISION</span>
      </span>
    </a>
  )
  const statusEl = (
    <span className={'status ' + statusPill.cls}><span className="dot" aria-hidden="true" />{statusPill.text}</span>
  )

  if (!preview) {
    return (
      <div className="app is-home">
        <section className="hero" aria-label="البداية">
          <div className="hero-art" aria-hidden="true"><img src="/hero-dunes.svg" alt="" /></div>
          <div className="hero-veil" aria-hidden="true" />
          <nav className="hero-nav">
            {brand}
            {statusEl}
          </nav>
          <div className="hero-body">
            <div className="hero-copy">
              <p className="hero-kicker"><Khatim className="kicker-mark" /> من الصورة إلى بيتٍ أصيل</p>
              <h1 className="hero-title">لكلِّ صورةٍ قصيدة</h1>
              <p className="hero-lede">
                ارفع صورة، فيتأمّل النموذج مشهدها وجوّها، وتختار أنت الإحساس، فنهديك أبياتًا عربية أصيلة كما وردت في دواوينها،
                مع سبب اختيار كل بيت.
              </p>
              <p className="hero-path" aria-label="الخطوات">
                <span>صورة</span><span className="arrow" aria-hidden="true">←</span>
                <span>إحساس</span><span className="arrow" aria-hidden="true">←</span>
                <span>بيت من الشعر</span>
              </p>
            </div>
            <Uploader onFile={onFile} preview={null} busy={analyzing} analysis={null}
              onReset={reset} disabled={!modelLoaded} disabledReason={uploadDisabledReason} />
          </div>
          <div className="hero-notice">
            <ReadyNotice ready={ready} error={readyError} loading={readyLoading} onRetry={loadReady}
              taxonomyError={taxonomyError} />
          </div>
        </section>
        <Footer ready={ready} />
      </div>
    )
  }

  return (
    <div className="app is-reading">
      <header className="topbar">
        {brand}
        <div className="topbar-side">
          {statusEl}
          <span className={'mode-pill ' + mode}>{MODE_AR[mode] || mode}</span>
        </div>
      </header>

      <main className="paper">
        <ReadyNotice ready={ready} error={readyError} loading={readyLoading} onRetry={loadReady}
          taxonomyError={taxonomyError} />

        <section className="reading reveal" aria-label="قراءة الصورة">
          <div className="reading-media">
            <Uploader onFile={onFile} preview={preview} busy={analyzing} analysis={analysis}
              onReset={reset} disabled={!modelLoaded} disabledReason={uploadDisabledReason} variant="side" />
          </div>
          <div className="reading-text">
            <p className="section-kicker">الفصل الأول</p>
            <h2 className="section-title">قراءة الصورة</h2>
            {analyzeError && (
              <div className="alert" role="alert">
                <strong>تعذّر تحليل الصورة: </strong>
                {analyzeError.message}
              </div>
            )}
            {analyzing && <Loading text="يتأمّل النموذج الصورة مرّة واحدة…" />}
            {analysis && <AnalysisPanel analysis={analysis} names={names} />}
          </div>
        </section>

        {analysis && (
          <section className="choosing reveal" aria-label="اختيارك">
            <Rule />
            <p className="section-kicker center">الفصل الثاني</p>
            <h2 className="section-title center">بأيِّ إحساسٍ تريد القصيدة؟</h2>
            <ConfirmPanel
              analysis={analysis}
              taxonomy={taxonomy}
              names={names}
              choices={choices}
              setChoices={setChoices}
              checkedIds={checkedIds}
              mode={mode}
              setMode={setMode}
              modes={ready?.modes || ['production', 'development']}
              ready={ready}
              corpusLoaded={corpusLoaded}
              onSubmit={onSubmit}
              busy={recLoading}
              requested={requested}
              canSubmit={!!payload && corpusLoaded && !expired}
            />
          </section>
        )}

        <div ref={resultsRef} className="results-anchor">
          {expired && (
            <div className="state-page" role="alert">
              <Khatim className="state-mark" />
              <h2>انتهت صلاحية التحليل</h2>
              <p>{expired.message || 'انتهت صلاحية تحليل الصورة؛ ارفع الصورة مرة أخرى.'}</p>
              <p className="tiny">لم يعد الخادم يحتفظ بتحليل هذه الصورة. بعد إعادة التحليل تعود الاقتراحات الافتراضية، فراجع اختياراتك من جديد.</p>
              <div className="row-actions center">
                {file && <button className="btn primary" onClick={reanalyzeSame} disabled={analyzing || !modelLoaded}>أعد تحليل الصورة نفسها</button>}
                <button className="btn ghost" onClick={reset}>ارفع صورة أخرى</button>
              </div>
            </div>
          )}
          {recError && (
            <div className="alert" role="alert">
              <strong>تعذّر اقتراح الأبيات: </strong>
              {recError.message}
              {Array.isArray(recError.issues) && recError.issues.length > 0 && (
                <ul className="issues">
                  {recError.issues.map((it, i) => (
                    <li key={i}>{typeof it === 'string' ? it : it.message_ar || it.message || it.code || JSON.stringify(it)}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {recLoading && !result && <Loading text="نقلّب صفحات المدوّنة ونرتّب الأبيات…" />}
          {result && !expired && (
            <Results result={result} names={names} ready={ready} stale={recLoading} taxonomy={taxonomy}
              choices={choices} checkedIds={checkedIds} adjust={adjust} />
          )}
        </div>
      </main>
      <Footer ready={ready} />
    </div>
  )
}

function Footer({ ready }) {
  return (
    <footer className="footer">
      <Rule className="faint" />
      <p>
        الأبيات من مدوّنة APCD بنصّها وتشكيلها كما وردت. نموذج رؤية واحد يقترح ولا يقرّر؛ أنت من يختار الإحساس.
        «إحساس الصورة» تقدير آلي، و«إحساس القصيدة» اختيارك أنت، والتفسيرات جمل ثابتة لا يكتبها نموذج لغوي.
      </p>
      {ready && (
        <p className="credits">
          النموذج <bdi dir="ltr">{ready.model?.model_id || '—'} {ready.model?.model_version || ''}</bdi>
          {' · '}المدوّنة <bdi dir="ltr">{ready.corpus?.version || '—'}</bdi>
          {' · '}المحرّك <bdi dir="ltr">{ready.engine_version || '—'}</bdi>
        </p>
      )}
    </footer>
  )
}

function Loading({ text }) {
  return (
    <div className="loading" role="status" aria-live="polite">
      <span className="ink-dots" aria-hidden="true"><span /><span /><span /></span>
      <span>{text}</span>
    </div>
  )
}
