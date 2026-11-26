import React from 'react'
import { fix, nameOf, pct, SCENE_STATUS } from '../labels.js'

const byScore = (a, b) => (b.score ?? 0) - (a.score ?? 0)
const byMargin = (a, b) => b.decision_score - b.threshold - (a.decision_score - a.threshold)

// What the single CLIP model estimated. Model scores only, shown as returned; nothing here is a user choice.
export default function AnalysisPanel({ analysis, names }) {
  const inf = analysis.inference || {}

  if (inf.status === 'error') {
    return (
      <section className="machine">
        <p className="alert">{inf.error?.message_ar || 'حدث خطأ أثناء تحليل الصورة.'}</p>
      </section>
    )
  }

  const scene = inf.scene || {}
  const scenes = [...(scene.predictions || [])].sort(byScore).slice(0, 3)
  const groups = [...(inf.scene_groups || [])].sort(byScore)
  const emo = inf.emotion || {}
  const emotions = [...(emo.predictions || [])].sort(byScore).slice(0, 3)
  const tags = inf.tags || []
  const present = tags.filter((t) => t.present).sort(byMargin)
  const absent = tags.filter((t) => !t.present).sort(byMargin)
  const st = SCENE_STATUS[scene.status] || { label: scene.status || '—', cls: 'soft' }
  const ambiguous = emo.status === 'ambiguous'
  const topScene = scenes[0]
  const topEmo = emotions[0]
  const rel = analysis.suggestion?.emotion_reliability || {}

  return (
    <section className="machine" aria-label="تقدير النموذج">
      <p className="voice machine-voice"><span className="voice-mark" aria-hidden="true" />تقدير آلي، بدرجات النموذج كما هي</p>

      <dl className="facts">
        <div className="fact">
          <dt>المشهد</dt>
          <dd>
            <span className="fact-value">{topScene ? nameOf(names, topScene.id) : '—'}</span>
            <span className="fact-meta">
              {topScene && <bdi dir="ltr" className="num">{pct(topScene.score)}</bdi>}
              <span className={'badge ' + st.cls}>{st.label}</span>
            </span>
          </dd>
        </div>
        <div className="fact">
          <dt>إحساس الصورة</dt>
          <dd>
            {rel.uncertain ? (
              <span className="fact-value small muted-v">غير موثوق لهذه الصورة</span>
            ) : (
              <span className="fact-value">{topEmo ? nameOf(names, topEmo.id) : '—'}</span>
            )}
            <span className="fact-meta">
              {!rel.uncertain && topEmo && <bdi dir="ltr" className="num">{pct(topEmo.score)}</bdi>}
              <span className={'badge ' + (rel.uncertain || ambiguous ? 'warn' : '')}>
                {rel.uncertain ? 'تقدير غير موثوق' : ambiguous ? 'ملتبس' : 'واضح'}
              </span>
            </span>
            <span className="top3">
              {emotions.map((e) => (
                <span key={e.id}>{nameOf(names, e.id)} <bdi dir="ltr" className="num">{pct(e.score)}</bdi></span>
              ))}
            </span>
          </dd>
        </div>
        <div className="fact">
          <dt>ما يظهر فيها</dt>
          <dd>
            {present.length ? (
              <span className="fact-value small">{present.map((t) => nameOf(names, t.id)).join(' · ')}</span>
            ) : (
              <span className="fact-value small muted-v">لا عنصر تجاوز حدّه</span>
            )}
          </dd>
        </div>
      </dl>

      {scene.status === 'unsupported' && (
        <p className="note warn">
          المشهد خارج ما يدعمه النموذج بثقة كافية (أعلى درجة <bdi dir="ltr">{pct(scene.top1_score)}</bdi> أقل من حدّ الدعم
          {' '}<bdi dir="ltr">{pct(scene.supported_threshold)}</bdi>). يمكنك مع ذلك اختيار العناصر البصرية بنفسك.
        </p>
      )}
      {scene.status === 'uncertain' && (
        <p className="note">النموذج غير متأكّد من المشهد (الفارق بين أول اقتراحين <bdi dir="ltr">{pct(scene.margin)}</bdi>)؛ راجع العناصر قبل البحث.</p>
      )}
      {ambiguous && (
        <p className="note">
          الصورة تحتمل أكثر من إحساس (الفارق <bdi dir="ltr">{pct(emo.margin)}</bdi> أقل من{' '}
          <bdi dir="ltr">{pct(emo.ambiguity_margin)}</bdi>)؛ الثقة منخفضة، فاختر إحساس القصيدة بنفسك.
        </p>
      )}
      {rel.uncertain && (
        <p className="note">
          تقدير الإحساس غير موثوق لهذه الصورة (احتمالات متقاربة أو منخفضة)، فلم نقترح إحساسًا للقصيدة. اختره أنت.
        </p>
      )}
      <aside className="marginal">
        <strong>للأمانة:</strong>{' '}
        {rel.landscape_awe
          ? 'هذا منظر طبيعي، وبيانات تدريب النموذج (EmoSet) تسمّي أغلب المناظر الطبيعية «رهبة» (66% منها في عيّنة التدريب)، لذلك يقدّر «الرهبة» لمعظم صور الطبيعة وبثقة عالية. هذا عُرف البيانات لا شعورك.'
          : 'إحساس الصورة تقدير آلي لجوّها تعلّمه النموذج من بيانات EmoSet، ويميل إلى «الرهبة» في صور الطبيعة.'}
        {' '}هو لا يقرّر إحساس القصيدة؛ أنت تختاره.
      </aside>

      <details className="fold">
        <summary>التفاصيل الكاملة للتقدير</summary>
        <div className="detail-grid">
          <div>
            <h3>المشهد (أعلى ثلاثة)</h3>
            <Bars list={scenes} names={names} />
            <p className="tiny">
              {scene.calibrated ? 'درجات معايَرة' : 'درجات غير معايَرة'} · حدّ الدعم <bdi dir="ltr">{pct(scene.supported_threshold)}</bdi>
            </p>
            <h3>مجموعات المشهد</h3>
            <Bars list={groups} names={names} />
          </div>
          <div>
            <h3>إحساس الصورة (أعلى ثلاثة)</h3>
            <Bars list={emotions} names={names} emo />
            <p className="tiny">{emo.calibrated ? 'درجات معايَرة' : 'درجات غير معايَرة'}</p>
            <h3>الوسوم: درجة القرار مقابل الحدّ</h3>
            <ul className="tag-list">
              {present.map((t) => <TagRow key={t.id} t={t} names={names} />)}
              {absent.map((t) => <TagRow key={t.id} t={t} names={names} />)}
            </ul>
          </div>
        </div>
      </details>
    </section>
  )
}

function Bars({ list, names, emo }) {
  if (!list.length) return <p className="tiny">لا توجد تنبؤات.</p>
  return (
    <ul className="bars">
      {list.map((s) => (
        <li key={s.id}>
          <span>{nameOf(names, s.id)}</span>
          <span className={'bar' + (emo ? ' emo' : '')}><span style={{ width: pct(s.score) }} /></span>
          <span className="num" dir="ltr">{pct(s.score)}</span>
        </li>
      ))}
    </ul>
  )
}

function TagRow({ t, names }) {
  return (
    <li className={t.present ? 'on' : ''}>
      <span>{nameOf(names, t.id)}</span>
      <span className="num" dir="ltr" title="درجة القرار / الحدّ">
        {fix(t.decision_score)} {t.present ? '≥' : '<'} {fix(t.threshold)}
      </span>
    </li>
  )
}
