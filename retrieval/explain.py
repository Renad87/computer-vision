"""Deterministic Arabic explanations and abstention messages (RETRIEVAL_METHOD.md section 8).

Every sentence comes from a fixed template filled only from taxonomy names and record fields (evidence spans,
justifications, meaning_ar, attribution). Nothing is generated: no LLM, no free text."""
from .labels import LITERAL, RELATION_ORDER, SCENE_ASSOCIATION, SYMBOLIC, SELECTION_WEIGHTS, emotion_entry

TIER_DISCLOSURE = {
    2: "اقتراح رمزي لا يطابق مشهد الصورة حرفيًا.",
    3: "اقتراح بالإحساس وحده دون مطابقة بصرية.",
}
ATTRIBUTION_VERIFIED = "النسبة موثقة بأدلة من قاعدة المعرفة التاريخية."
ATTRIBUTION_APCD = "النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل."
DRAFT_DISCLOSURE = "تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير)."
REVIEWED_STATUSES = {"reviewed", "double_reviewed", "adjudicated"}

_TRAILING = " .،؛:"


def _clean(text):
    return (text or "").strip().rstrip(_TRAILING)


def _name(taxonomy, label_id):
    return (taxonomy.labels.get(label_id) or {}).get("name_ar", label_id)


def _copy_span(span):
    return {"start": span["start"], "end": span["end"], "text": span["text"]}


def _visual_choice(candidate, profile):
    """The single visual relation the explanation describes: strongest relation first (literal, association,
    symbolic), then the item's user weight (focus, primary, secondary), then profile order."""
    weights = {x["id"]: SELECTION_WEIGHTS[x["user_selection"]] for x in profile.get("confirmed_visual_items") or []}
    order = {x["id"]: i for i, x in enumerate(profile.get("confirmed_visual_items") or [])}
    pairs = [(t, r) for t, r in zip(candidate["matched_targets"], candidate["matched_relations"]) if r in RELATION_ORDER]
    if candidate["natural_tier"] in (1, 2):  # describe an anchor relation when the tier rests on one
        anchored = [(t, r) for t, r in pairs if t in candidate["anchors"]]
        pairs = anchored or pairs
    if not pairs:
        return None
    return min(pairs, key=lambda p: (RELATION_ORDER[p[1]], -weights.get(p[0], 0), order.get(p[0], 0), p[0]))


def explain(candidate, profile, corpus_mode, taxonomy):
    record = candidate["record"]
    template_ids, sentences, spans = [], [], []

    def add(template_id, sentence, span=None):
        template_ids.append(template_id)
        sentences.append(sentence)
        if span and _copy_span(span) not in spans:
            spans.append(_copy_span(span))

    tier = candidate["natural_tier"]
    if tier in TIER_DISCLOSURE:
        add("T_TIER_DISCLOSURE", TIER_DISCLOSURE[tier])

    choice = _visual_choice(candidate, profile)
    if choice:
        target, relation = choice
        assoc = next(a for a in record.get("visual_associations") or [] if a.get("target") == target)
        name = _name(taxonomy, target)
        span = assoc.get("evidence_span")
        justification = _clean(assoc.get("justification_ar"))
        if relation == LITERAL and span:
            add("T_SCENE_LITERAL", f"تُظهر الصورة {name} (أكّدتَها)، والبيت يذكر «{span['text']}» وصفًا حرفيًا.", span)
        elif relation == SCENE_ASSOCIATION and justification:
            add("T_SCENE_ASSOC", f"البيت لا يسمّي {name}، لكن موقفه يقع فيها: {justification}.", span)
        elif relation == SYMBOLIC and justification:
            add("T_SYMBOLIC", f"يرد {name} في البيت رمزًا أو تشبيهًا: {justification}.", span)

    emotion = profile["selected_lit_emotion"]
    role = candidate["role"]
    entry = emotion_entry(record, emotion, role) or {}
    emotion_name = _name(taxonomy, emotion)
    if role == "primary":
        span = entry.get("evidence_span")
        if span:
            add("T_EMOTION_PRIMARY", f"اخترتَ {emotion_name}، وهو الإحساس الأساسي لهذا البيت، ودليله «{span['text']}».", span)
        else:
            add("T_EMOTION_PRIMARY",
                f"اخترتَ {emotion_name}، وهو الإحساس الأساسي لهذا البيت: {_clean(entry.get('justification_ar'))}.")
    else:
        add("T_EMOTION_SECONDARY", f"اخترتَ {emotion_name}، وهو إحساس ثانوي في هذا البيت.")

    meaning = _clean(record.get("meaning_ar"))
    if meaning:
        add("T_MEANING", f"المعنى: {meaning}.")

    if record.get("attribution_status") == "source_verified":
        add("T_ATTRIBUTION", ATTRIBUTION_VERIFIED)
    else:
        add("T_ATTRIBUTION", ATTRIBUTION_APCD)

    if corpus_mode == "development" or (record.get("review") or {}).get("status") not in REVIEWED_STATUSES:
        add("T_DRAFT_DISCLOSURE", DRAFT_DISCLOSURE)

    return {"template_ids": template_ids, "sentences_ar": sentences, "evidence_spans": spans}


def abstention_message(reason, targets, emotion, taxonomy):
    names = "، ".join(_name(taxonomy, t) for t in targets)
    emotion_name = _name(taxonomy, emotion)
    if reason == "empty_corpus":
        return "لا توجد في وضع المدونة الحالي أبيات مسموح بعرضها، فلا اقتراح."
    if reason == "no_emotion_match":
        return f"لا يوجد في المدونة الحالية بيت يحمل إحساس {emotion_name}."
    if reason == "cell_not_covered":
        if names:
            return f"لا يوجد في المدونة الحالية بيت يرتبط بـ{names}."
        return "لم يُحدَّد عنصر بصري، ووضع «الإحساس فقط» غير متاح لهذا الطلب."
    if reason == "no_visual_match_emotion_only_off":
        return (f"لا يوجد في المدونة الحالية بيت يحمل إحساس {emotion_name} ويرتبط بـ{names}، "
                "ووضع «الإحساس فقط» غير مفعّل.")
    return "حُذفت الأبيات المرشحة كلها بقواعد التنوع ومنع التكرار، فلا اقتراح."
