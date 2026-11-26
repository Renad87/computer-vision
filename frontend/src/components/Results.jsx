import React from 'react'
import {
  ABSTENTION_AR, fix, MODE_AR, msNum, nameOf, REVIEW_STATUS_AR, reviewState, TIER_AR,
} from '../labels.js'
import Khatim, { Rule } from './Khatim.jsx'

export default function Results({ result, names, ready, stale, taxonomy, choices, checkedIds, adjust }) {
  const recs = result.recommendations || {}
  const items = recs.items || []
  const display = result.display || []
  const dev = result.mode === 'development'
  const t = result.timings_ms || {}
  const sel = result.profile || {}
  const w = recs.weights || {}

  return (
    <section className={'results' + (stale ? ' stale' : '')} aria-label="الأبيات المقترحة" aria-busy={stale}>
      {dev && (
        <div className="disclosure" role="note">
          <strong>إفصاح وضع التطوير: </strong>
          {result.disclosure_ar || 'تسميات الأبيات المعروضة مسودات آلية لم يراجعها إنسان بعد، ولا تُعدّ نتائج معتمدة.'}
        </div>
      )}

      <div className="diwan-page">
      <span className="corner tl" aria-hidden="true" /><span className="corner tr" aria-hidden="true" />
      <span className="corner bl" aria-hidden="true" /><span className="corner br" aria-hidden="true" />
      <header className="sarlawh">
        <p className="section-kicker center">الفصل الثالث</p>
        <h2 className="diwan-title">{items.length ? 'من ديوان صورتك' : 'لم نجد بيتًا يليق بعد'}</h2>
        <Rule />
        <p className="diwan-sub">
            {sel.selected_lit_emotion && <>الإحساس الأدبي: <strong>{nameOf(names, sel.selected_lit_emotion)}</strong></>}
            {sel.secondary_lit_emotion && <> ثم {nameOf(names, sel.secondary_lit_emotion)}</>}
            {(sel.confirmed_visual_items || []).length > 0 && (
              <> · العناصر: {sel.confirmed_visual_items.map((x) => nameOf(names, x.id) + (x.user_selection === 'focus' ? ' (تركيز)' : '')).join('، ')}</>
            )}
        </p>
        <p className="diwan-meta">
          <span className={'mode-pill ' + result.mode}>{MODE_AR[result.mode] || result.mode}</span>
          {items.length > 0 && <span className="count">{items.length === 1 ? 'بيت واحد' : items.length === 2 ? 'بيتان' : `${items.length} أبيات`}</span>}
        </p>
      </header>
      <p className="tiny center meta">
        {stale && <span className="updating">جارٍ التحديث… </span>}
        {result.inference_reused ? 'أُعيد استخدام تحليل الصورة دون تشغيل النموذج مجددًا' : 'شُغّل النموذج لهذا الطلب'}
        {' · '}الاسترجاع <bdi dir="ltr">{msNum(t.retrieval)}</bdi> · الكلّي <bdi dir="ltr">{msNum(t.total)}</bdi> ملّي ثانية
        {recs.corpus_version && <> · المدوّنة <bdi dir="ltr">{recs.corpus_version}</bdi></>}
      </p>

      {items.length > 0 && <Legend dev={dev} />}

      {recs.status === 'partial' && (
        <p className="note center">عرضنا {items.length} فقط من {recs.k} لأن بقية المرشّحين لم يبلغوا حدّ الملاءمة؛ الأقل الأنسب خير من ملء العدد.</p>
      )}

      {recs.status === 'abstained' && (
        <Abstained result={result} names={names} ready={ready} taxonomy={taxonomy} choices={choices}
          checkedIds={checkedIds} adjust={adjust} />
      )}

      <div className="verses">
        {items.map((it, i) => {
          const d = display[i] && display[i].verse_id === it.verse_id ? display[i] : display.find((x) => x.verse_id === it.verse_id) || {}
          return (
            <React.Fragment key={it.verse_id}>
              {i > 0 && <Rule className="between" />}
              <VerseCard it={it} d={d} names={names} dev={dev} w={w} />
            </React.Fragment>
          )
        })}
      </div>
      </div>
    </section>
  )
}

function Legend({ dev }) {
  return (
    <div className="legend" aria-label="دليل حالة المراجعة">
      <span className="legend-title">دليل المراجعة:</span>
      <span className="rbadge ok">مراجَع بشريًا</span>
      <span className="rbadge draft">مسودة آلية غير مراجَعة</span>
      <span className="tiny">
        {dev
          ? 'في وضع التطوير قد تكون تسميات البيت كلها مسودات آلية.'
          : 'يبيّن كل بيت ما راجعه إنسان منه: الإحساس، والصلة البصرية بالمشهد.'}
      </span>
    </div>
  )
}

function Abstained({ result, names, ready, taxonomy, choices, checkedIds, adjust }) {
  const recs = result.recommendations || {}
  const abst = recs.abstention || {}
  const prodEmpty = result.mode === 'production' && (abst.reason_code === 'empty_corpus' || ready?.corpus?.displayable?.production === 0)
  const lits = (taxonomy?.lit_emotions || []).filter((l) => l.id !== choices.litEmotion)
  const hasFocus = checkedIds.includes(choices.focusId)
  const canEmotionOnly = checkedIds.length > 0 && !choices.emotionOnly
  const gap = abst.coverage_gap
  return (
    <div className="abstain">
      <Khatim className="state-mark" />
      <h3>آثر المحرّك الصمت على بيتٍ لا يناسب</h3>
      {abst.message_ar && <p className="lead">{abst.message_ar}</p>}
      {abst.reason_code && (
        <p className="tiny">
          السبب: {ABSTENTION_AR[abst.reason_code] || abst.reason_code} <bdi dir="ltr" className="code">{abst.reason_code}</bdi>
        </p>
      )}
      {gap && (
        <p className="gap">
          <span className="tiny">فجوة التغطية:</span>{' '}
          {(gap.visual_targets || []).map((id) => <span key={id} className="tag-chip">{nameOf(names, id)}</span>)}
          {(gap.visual_targets || []).length === 0 && <span className="tag-chip">دون عنصر بصري</span>}
          <span className="tiny"> مع </span>
          <span className="tag-chip gold">{nameOf(names, gap.lit_emotion)}</span>
        </p>
      )}
      {prodEmpty && (
        <p>وضع الإنتاج لا يعرض إلا الأبيات التي راجعها إنسان، ولا يوجد في المدوّنة بعدُ بيت مراجَع قابل للعرض.</p>
      )}

      <div className="adjust">
        <h4>جرّب تعديلًا بنقرة واحدة</h4>
        {lits.length > 0 && (
          <div className="adjust-row">
            <span className="tiny">إحساس آخر للقصيدة:</span>
            <div className="chips">
              {lits.map((l) => (
                <button key={l.id} type="button" className="chip" onClick={() => adjust.pickLit(l.id)}>{l.name_ar}</button>
              ))}
            </div>
          </div>
        )}
        <div className="row-actions center">
          {hasFocus && <button className="btn ghost" onClick={adjust.clearFocus}>أزل عنصر التركيز</button>}
          {canEmotionOnly && <button className="btn ghost" onClick={adjust.allowEmotionOnly}>اسمح بالمطابقة بالإحساس وحده</button>}
          {!choices.symbolic && checkedIds.length > 0 && <button className="btn ghost" onClick={adjust.allowSymbolic}>اسمح بالصلة الرمزية</button>}
          {result.mode === 'production' && (
            <button className="btn draft" onClick={adjust.showDevelopment}>عرض المسودات في وضع التطوير (غير مراجَعة)</button>
          )}
        </div>
      </div>
    </div>
  )
}

function VerseCard({ it, d, names, dev, w }) {
  const s = it.scores || {}
  const ex = it.explanation || {}
  const h = d.hemistichs
  const src = d.source || {}
  const rv = reviewState(it, d)
  const visualTargets = it.matched?.visual_targets || []
  const hasVisual = visualTargets.length > 0
  const formula = [
    typeof w.emotion === 'number' && `${fix(w.emotion)}·E`,
    typeof w.visual === 'number' && `${fix(w.visual)}·V`,
    typeof w.text === 'number' && `${fix(w.text)}·T`,
    typeof w.semantic === 'number' && w.semantic > 0 && `${fix(w.semantic)}·S`,
  ].filter(Boolean).join(' + ')

  return (
    <article className="verse">
      <div className="verse-head">
        <span className="rank" title="الترتيب"><bdi>{it.rank}</bdi></span>
        <span className="tier">{TIER_AR[it.tier] || ''}</span>
      </div>

      <blockquote className="bayt" lang="ar">
        {h && h.shatr_right && h.shatr_left ? (
          <>
            <span className="shatr">{h.shatr_right}</span>
            <span className="shatr-gap" aria-hidden="true">✦</span>
            <span className="shatr">{h.shatr_left}</span>
          </>
        ) : (
          <span className="shatr whole">{it.text_original}</span>
        )}
      </blockquote>
      {d.text_note && <p className="tiny center">ملاحظة على النص: {d.text_note}</p>}

      <p className="attribution">
        <span className="poet">{it.poet_name_apcd || d.poet_name_apcd}</span>
        <span className="era">{it.era_apcd || d.era_apcd}</span>
      </p>
      <p className="provenance">
        {src.meter_apcd && <>بحر {src.meter_apcd}</>}
        {src.diwan_apcd && <>{src.meter_apcd ? ' · ' : ''}{src.diwan_apcd}</>}
        {' · '}{src.dataset || 'APCD'}، الصف <bdi dir="ltr">{it.apcd_row}</bdi>
      </p>

      <p className="seals">
        <span className={'rbadge ' + (rv.emotion ? 'ok' : 'draft')}>الإحساس: {rv.emotion ? 'مراجَع بشريًا' : 'مسودة آلية غير مراجَعة'}</span>
        {hasVisual && (
          <span className={'rbadge ' + (rv.visual ? 'ok' : 'draft')}>الصلة البصرية: {rv.visual ? 'مراجَعة بشريًا' : 'مسودة آلية غير مراجَعة'}</span>
        )}
      </p>
      {d.review_scope_note_ar && <p className="scope-note" role="note">{d.review_scope_note_ar}</p>}
      {dev && !rv.emotion && !d.review_scope_note_ar && (
        <p className="scope-note draft" role="note">مسودة آلية غير مراجَعة: تسميات هذا البيت لم يراجعها إنسان بعد.</p>
      )}

      <div className="verse-body">
        {d.meaning_ar && (
          <div className="meaning">
            <h4>المعنى</h4>
            <p>{d.meaning_ar}</p>
          </div>
        )}
        <div className="why">
          <h4>لماذا هذا البيت؟</h4>
          <ul>{(ex.sentences_ar || []).map((x, i) => <li key={i}>{x}</li>)}</ul>
        </div>
      </div>

      <details className="fold scores">
        <summary>تفاصيل الترتيب · الدرجة النهائية <bdi dir="ltr">{fix(s.final, 3)}</bdi></summary>
        <table>
          <tbody>
            <Row k="الإحساس (E)" v={s.emotion} />
            <Row k="الصلة البصرية (V)" v={s.visual} />
            <Row k="النص (T)" v={s.text} />
            {s.semantic != null && <Row k="الدلالة (S)" v={s.semantic} />}
            <Row k="الدرجة النهائية" v={s.final} strong />
          </tbody>
        </table>
        {formula && (
          <p className="tiny">
            الصيغة: <bdi dir="ltr" className="code">final = {formula}</bdi>، وتُسقط المكوّنات غير المتاحة ويُعاد توزيع أوزانها.
          </p>
        )}
        {it.matched && (
          <p className="tiny">
            طابق: {nameOf(names, it.matched.lit_emotion)} ({it.matched.emotion_role === 'primary' ? 'إحساس أساسي للبيت' : 'إحساس ثانوي للبيت'})
            {hasVisual && <> · {visualTargets.map((v) => nameOf(names, v)).join('، ')}</>}
          </p>
        )}
        <p className="tiny">
          حالة المراجعة في السجل: {REVIEW_STATUS_AR[rv.status] || rv.status}
          {d.annotation_method && <> · طريقة التعليم <bdi dir="ltr">{d.annotation_method}</bdi></>}
          {rv.dims && <> · الأبعاد المراجَعة: <bdi dir="ltr">{rv.dims.join(', ') || '—'}</bdi></>}
        </p>
      </details>
    </article>
  )
}

function Row({ k, v, strong }) {
  return (
    <tr className={strong ? 'strong' : ''}>
      <td>{k}</td>
      <td className="num">{v == null ? 'غير متاح' : fix(v, 3)}</td>
    </tr>
  )
}
