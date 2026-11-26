import React from 'react'
import { LIT_GLOSS, MODE_AR, MODE_HELP, nameOf, pct } from '../labels.js'

// The user's confirmation step. Everything here is a user selection, not a model score.
export default function ConfirmPanel({ analysis, taxonomy, names, choices, setChoices, checkedIds, mode, setMode, modes,
  ready, corpusLoaded, onSubmit, busy, requested, canSubmit }) {
  const sugg = analysis.suggestion || {}
  const suggestedItems = sugg.visual_items || []
  const suggestedIds = new Set(suggestedItems.map((v) => v.id))
  const suggestedLit = new Map((sugg.lit_emotions || []).map((l) => [l.id, l]))
  const userOnly = new Set(taxonomy?.user_only_lit_emotions || [])
  const pilotLit = new Set(taxonomy?.pilot?.lit_emotions || [])

  const litList = taxonomy?.lit_emotions?.length
    ? taxonomy.lit_emotions
    : (sugg.lit_emotions || []).map((l) => ({ id: l.id, name_ar: l.name_ar }))

  const otherGroups = (taxonomy?.scene_groups || []).filter((l) => !suggestedIds.has(l.id))
  const otherTags = (taxonomy?.exposed_tags || []).filter((l) => !suggestedIds.has(l.id))
  const labelOf = (id) => suggestedItems.find((v) => v.id === id)?.name_ar || nameOf(names, id)

  const set = (patch) => setChoices((c) => ({ ...c, ...patch }))
  const toggleItem = (id) =>
    setChoices((c) => {
      const items = { ...c.items, [id]: !c.items[id] }
      const anyChecked = Object.values(items).some(Boolean)
      return {
        ...c,
        items,
        focusId: items[c.focusId] ? c.focusId : null,
        emotionOnly: anyChecked ? c.emotionOnly : true,
      }
    })
  const setLit = (id) =>
    setChoices((c) => ({ ...c, litEmotion: id, secondary: c.secondary === id ? null : c.secondary }))

  const noItems = checkedIds.length === 0
  const sceneUnsupported = analysis.inference?.scene?.status === 'unsupported'
  const prodCount = ready?.corpus?.displayable?.production
  const devCount = ready?.corpus?.displayable?.development
  const extraChecked = [...otherGroups, ...otherTags].filter((l) => choices.items[l.id]).length
  const focusValid = checkedIds.includes(choices.focusId)
  const suggestedFrom = [...suggestedLit.values()]

  return (
    <>
      <section className="choose-block" aria-label="إحساس القصيدة">
        <p className="voice human-voice center"><span className="voice-mark" aria-hidden="true" />اختيارك أنت، بلا درجات</p>
        <p className="lede center">
          هذا هو الإحساس الذي تريده في البيت، وقد يختلف عمّا قدّره النموذج للصورة
          {suggestedFrom.length > 0 && <> (قدّر النموذج: «{suggestedFrom.map((x) => nameOf(names, x.from_img_emotion)).join('، ')}»)</>}.
        </p>

        <div className="lit-grid" role="radiogroup" aria-label="الإحساس الأدبي">
          {litList.map((l) => {
            const s = suggestedLit.get(l.id)
            const on = choices.litEmotion === l.id
            return (
              <button key={l.id} type="button" role="radio" aria-checked={on}
                className={'lit-card' + (on ? ' on' : '') + (s ? ' suggested' : '')} onClick={() => setLit(l.id)}>
                <span className="lit-name">{l.name_ar || nameOf(names, l.id)}</span>
                {LIT_GLOSS[l.id] && <span className="lit-gloss">{LIT_GLOSS[l.id]}</span>}
                <span className="lit-tags">
                  {s && <span className="mini gold">مقترح من جدول ربط ثابت</span>}
                  {userOnly.has(l.id) && <span className="mini">باختيارك فقط</span>}
                  {pilotLit.size > 0 && !pilotLit.has(l.id) && !userOnly.has(l.id) && <span className="mini">خارج التجربة</span>}
                </span>
              </button>
            )
          })}
        </div>
        {!choices.litEmotion && <p className="note center">اختر إحساس القصيدة بنفسك للمتابعة؛ لا نختاره عنك.</p>}
        {suggestedFrom.length > 0 && (
          <p className="tiny center">
            علامة «مقترح» مأخوذة من جدول ربط ثابت انطلاقًا من إحساس الصورة، وليست درجة نموذج؛ والاختيار لك.
          </p>
        )}

        <div className="secondary">
          <label htmlFor="secondary-lit" className="field-label">ومعه إحساس ثانٍ <span className="tiny">(اختياري)</span></label>
          <select id="secondary-lit" className="select" value={choices.secondary || ''}
            onChange={(e) => set({ secondary: e.target.value || null })}>
            <option value="">دون إحساس ثانوي</option>
            {litList.filter((l) => l.id !== choices.litEmotion).map((l) => (
              <option key={l.id} value={l.id}>{l.name_ar || nameOf(names, l.id)}</option>
            ))}
          </select>
        </div>
      </section>

      <section className="choose-block" aria-label="العناصر البصرية">
        <h3 className="block-title">ما الذي تراه في الصورة؟</h3>
        <p className="tiny center">أكّد ما يصدق من اقتراح النموذج، أو أضف من «عناصر أخرى».</p>
        {sceneUnsupported && (
          <p className="note warn">المشهد غير مدعوم؛ لم يُقترح عنصر بثقة كافية، لكن يمكنك اختيار ما تراه في الصورة بنفسك.</p>
        )}
        {suggestedItems.length > 0 ? (
          <div className="chips">
            {suggestedItems.map((v) => (
              <ToggleChip key={v.id} on={!!choices.items[v.id]} onClick={() => toggleItem(v.id)}>
                {v.name_ar || nameOf(names, v.id)}
                <small>{v.source === 'tag' ? 'وسم' : 'مشهد'}{typeof v.score === 'number' ? ' · ' : ''}
                  {typeof v.score === 'number' && <bdi dir="ltr">{pct(v.score)}</bdi>}</small>
                <small className="sugg">مقترح</small>
              </ToggleChip>
            ))}
          </div>
        ) : (
          <p className="tiny center">لم يقترح النموذج عناصر بصرية لهذه الصورة.</p>
        )}

        <details className="more" open={extraChecked > 0 || undefined}>
          <summary>عناصر أخرى{extraChecked ? ` · مختار ${extraChecked}` : ''}</summary>
          {otherGroups.length > 0 && (
            <>
              <h4 className="sub">مجموعات المشهد</h4>
              <div className="chips">
                {otherGroups.map((l) => (
                  <ToggleChip key={l.id} on={!!choices.items[l.id]} onClick={() => toggleItem(l.id)}>
                    {l.name_ar || nameOf(names, l.id)}
                  </ToggleChip>
                ))}
              </div>
            </>
          )}
          {otherTags.length > 0 && (
            <>
              <h4 className="sub">الوسوم</h4>
              <div className="chips">
                {otherTags.map((l) => (
                  <ToggleChip key={l.id} on={!!choices.items[l.id]} onClick={() => toggleItem(l.id)}>
                    {l.name_ar || nameOf(names, l.id)}
                  </ToggleChip>
                ))}
              </div>
            </>
          )}
        </details>

        <div className="focus-row">
          <span className="field-label">وأيّها محور القصيدة؟ <span className="tiny">(تركيز اختياري)</span></span>
          {noItems ? (
            <p className="tiny">لا عناصر مؤكَّدة، فلا تركيز.</p>
          ) : (
            <div className="segmented wrap" role="radiogroup" aria-label="عنصر التركيز">
              <button type="button" role="radio" aria-checked={!focusValid} className={!focusValid ? 'on' : ''}
                onClick={() => set({ focusId: null })}>دون تركيز</button>
              {checkedIds.map((id) => (
                <button key={id} type="button" role="radio" aria-checked={choices.focusId === id}
                  className={choices.focusId === id ? 'on' : ''} onClick={() => set({ focusId: id })}>
                  {labelOf(id)}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="choose-block" aria-label="الوضع وخيارات المطابقة">
        <h3 className="block-title">من أيِّ مدوّنة نختار؟</h3>

        <div className="mode-switch" role="radiogroup" aria-label="الوضع">
          {modes.map((m) => (
            <button key={m} type="button" role="radio" aria-checked={mode === m}
              className={'mode-opt ' + m + (mode === m ? ' on' : '')} onClick={() => setMode(m)}>
              <span className="mode-name">{MODE_AR[m] || m}</span>
              <span className="mode-help">{MODE_HELP[m] || ''}</span>
            </button>
          ))}
        </div>
        {mode === 'production' && typeof prodCount === 'number' && (
          <p className={'note' + (prodCount === 0 ? ' warn' : '')}>
            {prodCount === 0
              ? `لا يوجد بعد أي بيت مراجَع بشريًا في المدوّنة، لذا سيمتنع وضع الإنتاج عن الاقتراح. يمكنك اختيار وضع التطوير بنفسك${typeof devCount === 'number' ? ` (${devCount} بيتًا بتسميات آلية)` : ''}، مع إفصاح بأنها غير مراجَعة.`
              : `في المدوّنة الآن ${prodCount} بيتًا مراجَعًا قابلًا للعرض في هذا الوضع، فقد لا تتوفّر أبيات لبعض المزائج.`}
          </p>
        )}
        {mode === 'development' && (
          <p className="note warn">وضع التطوير يعرض أبياتًا بتسميات آلية لم يراجعها إنسان بعد، وليست نتائج معتمدة.</p>
        )}

        <div className="checks">
          <label className="check-line">
            <input type="checkbox" checked={choices.symbolic} onChange={(e) => set({ symbolic: e.target.checked })} />
            <span>اسمح بالصلة الرمزية <span className="tiny">(البيت يذكر العنصر رمزًا لا وصفًا)</span></span>
          </label>
          <label className="check-line">
            <input type="checkbox" checked={noItems ? true : choices.emotionOnly} disabled={noItems}
              onChange={(e) => set({ emotionOnly: e.target.checked })} />
            <span>اسمح ببيت يطابق الإحساس وحده <span className="tiny">(دون عنصر بصري)</span></span>
          </label>
          {noItems && <p className="tiny">لا عناصر بصرية مؤكَّدة، فالمطابقة ستكون بالإحساس وحده.</p>}
        </div>

        {!corpusLoaded && <p className="note warn">مدوّنة الأبيات غير جاهزة في الخادم؛ لا يمكن الاقتراح الآن.</p>}
        <button className="btn primary cta" onClick={onSubmit} disabled={busy || !canSubmit}>
          {busy ? 'نقلّب الصفحات…' : requested ? 'أعد الاقتراح' : 'اقترح أبياتًا'}
        </button>
        {requested && <p className="tiny center">أي تغيير في اختياراتك يعيد الاقتراح تلقائيًا بالتحليل نفسه، دون إعادة تشغيل النموذج.</p>}
      </section>
    </>
  )
}

function ToggleChip({ on, onClick, children }) {
  return (
    <button type="button" role="checkbox" aria-checked={!!on} className={'chip' + (on ? ' on' : '')} onClick={onClick}>
      <span className="tick" aria-hidden="true" />
      {children}
    </button>
  )
}
