"""Label audit v2 and the priority_v2 human-review list (Python standard library only).

    python3 poetry_corpus/review_packages/priority_v2/build_priority_v2.py

Reads (never writes): poetry_corpus/exports/corpus_all_v2.jsonl, the taxonomy, and
poetry_corpus/review_packages/priority_v1/priority_v1_manifest.json.
Writes only:
    poetry_corpus/reports/label_audit_v2.md, poetry_corpus/reports/label_audit_v2.json
    poetry_corpus/review_packages/priority_v2/review_sheet_priority_v2.csv   (UTF-8 BOM, empty decision cells)
    poetry_corpus/review_packages/priority_v2/priority_v1_order.csv        (ranking of the existing 56, no decisions)
    poetry_corpus/review_packages/priority_v2/priority_v2_manifest.json

Every label in the corpus is an AI draft unless review.decisions says otherwise (35 emotion accepts by
human:renad, 0 visual decisions). The heuristics and the triage score below are transparent rules for ordering
human review; they are not accuracy measurements and they record no decision. Verse text is copied from
text_original programmatically and never retyped.
"""
import collections
import csv
import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, ROOT)

from contracts.taxonomy import load_taxonomy  # noqa: E402
from contracts.validate import display_allowed, load_jsonl  # noqa: E402
from poetry_corpus.tools import coverage  # noqa: E402
from poetry_corpus.tools.build_batch import folded, shared_hemistichs, verse_number  # noqa: E402
from poetry_corpus.tools.export_corpus import copyright_status  # noqa: E402
from poetry_corpus.tools.find_candidates import EXTRA_SCENE_TERMS, fold, variants  # noqa: E402

CORPUS = os.path.join(ROOT, "poetry_corpus", "exports", "corpus_all_v2.jsonl")
OMAR_MANIFEST = os.path.join(ROOT, "poetry_corpus", "review_packages", "priority_v1", "priority_v1_manifest.json")
REPORTS = os.path.join(ROOT, "poetry_corpus", "reports")
OUT_DIR = os.path.join(ROOT, "poetry_corpus", "review_packages", "priority_v2")
PENDING_IDS = {"pv:verse:000005", "pv:verse:000007", "pv:verse:000018", "pv:verse:000024", "pv:verse:000031"}
TIER1 = coverage.TIER1_RELATIONS
RELATIONS = ["relation.literal", "relation.scene_association", "relation.symbolic", "relation.negated",
             "relation.hypothetical", "relation.ambiguous"]
STRONG_THRESHOLD = 11      # triage total (of 14) at or above which a row counts as a "strong" candidate
CELL_TARGET = 3            # strong distinct poems per pilot cell that priority_v2 tries to reach with priority_v1
SHORT_LETTERS = 30         # folded letters (no spaces/diacritics); about the 1st percentile of the corpus

WORD = re.compile(r"[ء-ي]+")
NEGATION = {"لا", "لم", "ما", "ليس", "لن", "بلا", "غير", "ولا", "ولم", "وما", "فلا", "فما", "فلم", "ولن", "فلن",
            "وليس", "فليس", "لات"}
WISH = {"ليت", "وليت", "فليت", "ياليت", "لو", "ولو", "فلو", "لعل", "ولعل", "فلعل", "ليتني", "ليتها", "ليته"}
SIMILE = {"كان", "كانه", "كانها", "كانهم", "كانما", "وكان", "فكان", "مثل", "كمثل", "شبه"}
# كان after folding is كأن (simile) and also كان (verb "was"): counted as a weak cue only, see the report.
LEAD_STRONG = {"ثم", "حتي", "اذ", "فاذا", "واذ", "حين", "لكن", "بل"}
PRONOUN_LEAD = {"هو", "هي", "هم", "هن", "هما", "ذلك", "تلك", "هذا", "هذه", "ذاك", "اولئك", "الذي", "التي",
                "الذين", "وهو", "وهي", "وهم", "فهو", "فهي", "فهم", "وذلك", "وتلك", "وهذا", "وهذه"}
CONTEXT_MARKERS = ["القصيدة", "البيت السابق", "الأبيات السابقة", "السابق", "ما قبله", "ما بعده", "يكمل",
                   "اللاحق", "البيت التالي", "تتمة", "السياق"]
# «في سياق ...» ("in a context of complaint") names a genre, not another verse: removed before matching.
LOVE_PRAISE_MARKERS = ["ممدوح", "يمدح", "مدح", "المحبوب", "محبوبت", "الحبيب", "حبيبت", "العشق", "الغزل",
                       "الخمر", "يتغزل"]
GENERIC_JUSTIFICATION = ["مشهد", "يوحي", "يستحضر", "جو", "صورة", "إطار", "فضاء", "عالم", "بيئة"]
STOP = {"في", "من", "علي", "الي", "عن", "ما", "لا", "قد", "كل", "ان", "او", "ثم", "هذا", "هذه", "التي", "الذي",
        "مع", "بين", "حتي", "اذا", "لم", "لن", "هو", "هي"}


def tokens(text):
    return WORD.findall(fold(text or ""))


STEM_PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف", "ب", "ل", "ك")


def stem(token):
    """Strip one leading conjunction/preposition and the article, keeping at least 3 letters."""
    for _ in range(2):
        for p in STEM_PREFIXES:
            if token.startswith(p) and len(token) - len(p) >= 3:
                token = token[len(p):]
                break
    return token


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


class Terms:
    """Surface forms of the taxonomy query_terms_ar of a scene group (plus its member tags) or a tag."""

    def __init__(self, taxonomy):
        self.tax = taxonomy
        self.strict, self.extended = {}, {}
        for layer in ("scene_group", "tag"):
            for label in taxonomy.ids(layer):
                terms = list(taxonomy.labels[label].get("query_terms_ar") or [])
                if layer == "scene_group":
                    for tag in taxonomy.group_members(label)[1]:
                        terms += taxonomy.labels[tag].get("query_terms_ar") or []
                if terms:
                    self.strict[label] = variants(terms)
                    extra = EXTRA_SCENE_TERMS.get(label, "").split() if layer == "scene_group" else []
                    self.extended[label] = variants(terms + extra)

    def has(self, label):
        return label in self.strict

    def hit(self, label, text, extended=False):
        table = (self.extended if extended else self.strict).get(label, {})
        return [t for t in tokens(text) if t in table]


def span_context(record, span, width=2):
    """Folded tokens immediately before the span inside the same hemistich (span may cross into the second)."""
    text = record["text_original"]
    before = text[:span["start"]]
    left = (record.get("hemistichs") or {}).get("shatr_right") or ""
    if len(before) > len(left):  # span in the second hemistich: only look inside it
        before = before[len(left):]
    return tokens(before)[-width:], tokens(before)


def audit_record(r, tax, terms, renad_accepted, omar_ids):
    flags = []  # (code, strength, detail)
    text = r["text_original"]
    meaning = r.get("meaning_ar") or ""
    toks = tokens(text)
    first = toks[0] if toks else ""
    # --- standalone-ness
    meaning_ctx = meaning.replace("في سياق", "")
    for marker in CONTEXT_MARKERS:
        if marker in meaning_ctx:
            flags.append(("context_in_meaning", "strong", f"المعنى يذكر «{marker}»"))
            break
    justifications = [a.get("justification_ar") or "" for a in r["visual_associations"]]
    justifications += [e.get("justification_ar") or "" for slot in ("primary", "secondary") for e in r["emotions"][slot]]
    justifications = [j.replace("في سياق", "") for j in justifications]
    for marker in CONTEXT_MARKERS:
        if any(marker in j for j in justifications):
            flags.append(("context_in_justification", "strong", f"مبرر يذكر «{marker}»"))
            break
    if first in LEAD_STRONG:
        flags.append(("lead_connective", "strong", f"يبدأ بـ«{first}»"))
    elif first in PRONOUN_LEAD:
        flags.append(("lead_pronoun", "strong", f"يبدأ بضمير/إشارة «{first}» بلا مرجع في البيت"))
    elif first[:1] in ("و", "ف") and len(first) > 3:
        flags.append(("lead_wa_fa", "weak", f"يبدأ بـ«{first[:1]}» (قد تكون عاطفة أو حرفًا أصليًا)"))
    letters = len(folded(text))
    if letters < SHORT_LETTERS:
        flags.append(("short_verse", "strong", f"{letters} حرفًا فقط"))
    if not all((r.get("hemistichs") or {}).values()):
        flags.append(("missing_hemistich", "strong", "شطر فارغ"))
    if r.get("text_note"):
        flags.append(("apcd_text_note", "strong", f"ملاحظة نص: {r['text_note']}"))
    # --- emotion
    if any(m in meaning for m in LOVE_PRAISE_MARKERS):
        hit = next(m for m in LOVE_PRAISE_MARKERS if m in meaning)
        flags.append(("love_or_praise_in_meaning", "weak", f"المعنى يذكر «{hit}» (غزل/مدح قد يغلب)"))
    # --- visual associations
    assoc_rows = []
    for a in r["visual_associations"]:
        target, rel = a["target"], a["relation"]
        span = a.get("evidence_span")
        info = {"target": target, "relation": rel, "span": (span or {}).get("text"),
                "justification": a.get("justification_ar"), "issues": []}
        if span and terms.has(target):
            if not terms.hit(target, span["text"]):
                ext = terms.hit(target, span["text"], extended=True)
                info["issues"].append("span_no_query_term_extra_only" if ext else "span_no_query_term")
        if span and rel == "relation.literal":
            near, allb = span_context(r, span)
            span_toks = tokens(span["text"])
            if set(near) & NEGATION or (span_toks and span_toks[0] in NEGATION):
                info["issues"].append("literal_after_negation")
            if set(allb) & WISH or set(span_toks) & WISH:
                info["issues"].append("literal_in_wish_or_condition")
            if set(near) & SIMILE:
                info["issues"].append("literal_after_simile_particle")
        if rel == "relation.scene_association":
            j = a.get("justification_ar") or ""
            jt = set(tokens(j))
            concrete = terms.hit(target, j, extended=True) if terms.has(target) else []
            shared = {stem(t) for t in jt if t not in STOP} & {stem(t) for t in toks if t not in STOP}
            shared = {t for t in shared if len(t) >= 3}
            if not concrete and not shared:
                info["issues"].append("scene_association_generic")
        if target == "scene_group.city":
            info["issues"].append("city_label_check_heritage")
        assoc_rows.append(info)
    for info in assoc_rows:
        for issue in info["issues"]:
            flags.append((issue, "weak" if issue in ("span_no_query_term_extra_only", "city_label_check_heritage",
                                                     "literal_after_simile_particle") else "strong",
                          f"{info['target']} / {info['relation']}"))
    return flags, assoc_rows


def component_scores(r, flags, assoc_rows, group, renad_ok):
    """0-2 per component for the record relative to one scene group (None = best over all groups)."""
    codes = {c for c, _, _ in flags}
    strong_standalone = codes & {"context_in_meaning", "context_in_justification", "lead_connective", "lead_pronoun", "short_verse",
                                 "missing_hemistich"}
    meaning = r.get("meaning_ar") or ""
    s = {}
    if not meaning:
        s["meaning"] = 0
    elif "context_in_meaning" in codes or len(meaning.split()) < 10:
        s["meaning"] = 1
    else:
        s["meaning"] = 2
    s["standalone"] = 0 if strong_standalone else (1 if "lead_wa_fa" in codes else 2)

    def assoc_scores(info):
        iss = set(info["issues"])
        if info["relation"] == "relation.literal":
            ev = 1 if iss & {"span_no_query_term", "span_no_query_term_extra_only"} else 2
            link = 0 if iss & {"literal_after_negation", "literal_in_wish_or_condition"} else (
                1 if "literal_after_simile_particle" in iss or "city_label_check_heritage" in iss else 2)
        elif info["relation"] == "relation.scene_association":
            ev = 0 if "scene_association_generic" in iss else 1
            link = 0 if "scene_association_generic" in iss else 1
        else:
            ev, link = 0, 0
        return ev, link

    cands = [i for i in assoc_rows if i["target"].startswith("scene_group.") and i["relation"] in TIER1
             and (group is None or i["target"] == group)]
    best = max((assoc_scores(i) for i in cands), default=(0, 0), key=lambda x: (x[0] + x[1], x[1]))
    s["evidence"], s["scene_link"] = best
    if renad_ok:
        s["emotion_link"] = 2
    else:
        primary = r["emotions"]["primary"]
        base = 2 if any(e["basis"] == "expressed" and e.get("evidence_span") for e in primary) else 1
        unc = r["annotator_uncertainty"]
        base -= {"low": 0, "medium": 1, "high": 2}[unc]
        if "love_or_praise_in_meaning" in codes:
            base -= 1
        s["emotion_link"] = max(0, base)
    if r["attribution_status"] == "disputed" or r.get("text_note"):
        s["text_attribution"] = 0
    else:
        s["text_attribution"] = 2 if r["attribution_status"] == "source_verified" else 1
    s["rights"] = 2 if copyright_status(r).startswith("public_domain") else 0
    s["total"] = sum(v for k, v in s.items())
    return s


def name_ar(tax, label):
    return tax.labels[label]["name_ar"]


def main():
    tax = load_taxonomy()
    terms = Terms(tax)
    loaded, issues = load_jsonl(CORPUS)
    if issues:
        raise SystemExit(f"{CORPUS}: {issues[:3]}")
    recs = [r for _, r in loaded]
    by_id = {r["verse_id"]: r for r in recs}
    omar = json.load(open(OMAR_MANIFEST, encoding="utf-8"))
    omar_rows = {row["verse_id"]: row for row in omar["rows"]}
    prod = [r for r in recs if display_allowed(r, "production")]
    renad_ok = {r["verse_id"] for r in recs
                if any(d["dimension"] in ("emotion", "all") and d["decision"] == "accept" for d in r["review"]["decisions"])}
    visual_reviewed = {r["verse_id"] for r in recs if any(d["dimension"] in ("visual", "all")
                                                          for d in r["review"]["decisions"])}
    pilot = coverage.pilot_cells(tax)
    groups = tax.ids("scene_group")
    emotions = tax.ids("lit_emotion")

    # ---------------- 1. pools
    def matrix(pool, mode, reviewed_visual_only=False):
        members = coverage.cell_members([r for r in pool if not reviewed_visual_only or r["verse_id"] in visual_reviewed],
                                        tax, mode)
        out = {}
        for g in groups:
            for e in emotions:
                block = members.get((g, e)) or {"tier1": [], "secondary": [], "symbolic": []}
                out[f"{g}|{e}"] = {"tier1_records": len(block["tier1"]),
                                   "tier1_poems": len({coverage.poem_key(x) for x in block["tier1"]}),
                                   "secondary_records": len(block["secondary"]),
                                   "symbolic_records": len(block["symbolic"])}
        return out

    pools = {"production": prod, "development": recs}
    mats = {"production_ai_visual": matrix(prod, "production"),
            "production_reviewed_visual": matrix(prod, "production", True),
            "development": matrix(recs, "development")}

    def pool_stats(pool):
        rel = collections.defaultdict(collections.Counter)
        span_by_rel = collections.defaultdict(collections.Counter)
        for r in pool:
            for a in r["visual_associations"]:
                rel[a["target"]][a["relation"]] += 1
                span_by_rel[a["relation"]]["with_span" if a.get("evidence_span") else "no_span"] += 1
        basis = collections.Counter()
        emo_span = collections.Counter()
        for r in pool:
            for slot in ("primary", "secondary"):
                for e in r["emotions"][slot]:
                    basis[f"{slot}:{e['basis']}"] += 1
                    emo_span[f"{slot}:{'with_span' if e.get('evidence_span') else 'no_span'}"] += 1
        return {
            "records": len(pool),
            "relations_by_target": {t: dict(c) for t, c in sorted(rel.items())},
            "relations_total": dict(sum(rel.values(), collections.Counter())),
            "visual_span_by_relation": {k: dict(v) for k, v in span_by_rel.items()},
            "records_without_scene_group_tier1": sum(1 for r in pool if not any(
                a["target"].startswith("scene_group.") and a["relation"] in TIER1 for a in r["visual_associations"])),
            "records_without_any_visual": sum(1 for r in pool if not r["visual_associations"]),
            "emotion_basis": dict(basis), "emotion_span": dict(emo_span),
            "meaning_ar_present": sum(1 for r in pool if r.get("meaning_ar")),
            "attribution_status": dict(collections.Counter(r["attribution_status"] for r in pool)),
            "copyright_class": dict(collections.Counter(copyright_status(r) for r in pool)),
            "annotator_uncertainty": dict(collections.Counter(r["annotator_uncertainty"] for r in pool)),
            "review_status": dict(collections.Counter(r["review"]["status"] for r in pool)),
            "text_note_present": sum(1 for r in pool if r.get("text_note")),
            "distinct_poets": len({r["poet"]["name_apcd"] for r in pool}),
            "distinct_poems": len({coverage.poem_key(r) for r in pool}),
        }

    stats = {k: pool_stats(v) for k, v in pools.items()}

    # ---------------- 2. heuristics
    audit = {}
    for r in recs:
        flags, assoc_rows = audit_record(r, tax, terms, renad_ok, omar_rows)
        audit[r["verse_id"]] = (flags, assoc_rows)
    flag_counts = {"development": collections.Counter(), "production": collections.Counter()}
    flag_records = {"development": collections.Counter(), "production": collections.Counter()}
    prod_ids = {r["verse_id"] for r in prod}
    for vid, (flags, _) in audit.items():
        seen = set()
        for code, _, _ in flags:
            for pool in (["development"] + (["production"] if vid in prod_ids else [])):
                flag_counts[pool][code] += 1
                if code not in seen:
                    flag_records[pool][code] += 1
            seen.add(code)
    dup_pairs = shared_hemistichs(recs, recs)
    dup_pairs = sorted({tuple(sorted(p)) for p in dup_pairs})
    poets = collections.Counter(r["poet"]["name_apcd"] for r in recs)
    poems = collections.Counter(coverage.poem_key(r) for r in recs)
    dev_members = coverage.cell_members(recs, tax, "development")
    cell_concentration = {}
    for g, e in pilot:
        t1 = (dev_members.get((g, e)) or {}).get("tier1", [])
        if t1:
            top_poet, n = collections.Counter(x["poet"]["name_apcd"] for x in t1).most_common(1)[0]
            cell_concentration[f"{g}|{e}"] = {"tier1_records": len(t1), "top_poet": top_poet, "top_poet_records": n,
                                              "share": round(n / len(t1), 2)}

    # ---------------- 3. scores
    scores = {}
    for r in recs:
        flags, assoc_rows = audit[r["verse_id"]]
        scores[r["verse_id"]] = component_scores(r, flags, assoc_rows, None, r["verse_id"] in renad_ok)
    hist = collections.Counter(s["total"] for s in scores.values())

    # ---------------- 4. priority_v2
    def covers(r):
        return coverage_cells(r, tax, pilot)

    omar_cell_poems = collections.defaultdict(set)
    omar_cell_strong = collections.defaultdict(set)
    omar_order = []
    for vid, row in omar_rows.items():
        r = by_id[vid]
        cell_scores = []
        for g, e in covers(r):
            sc = component_scores(r, *audit[vid], g, vid in renad_ok)
            key = coverage.poem_key(r)
            omar_cell_poems[(g, e)].add(key)
            if is_strong(sc):
                omar_cell_strong[(g, e)].add(key)
            cell_scores.append(((g, e), sc))
        best = max((sc["total"] for _, sc in cell_scores), default=scores[vid]["total"])
        omar_order.append((vid, row, best, cell_scores))
    omar_order.sort(key=lambda x: (x[1]["priority"] != "V", -x[2], verse_number(x[0])))

    dev_poems = {c: {coverage.poem_key(x) for x in (dev_members.get(c) or {}).get("tier1", [])} for c in pilot}
    # candidates: never in omar, never pending, not already visually reviewed
    selected = []  # (record, scope, cells, cell scores)
    need = {c: max(0, CELL_TARGET - len(omar_cell_strong[c])) for c in pilot}
    filled = {c: set(omar_cell_strong[c]) for c in pilot}
    pool = [r for r in recs if r["verse_id"] not in omar_rows and r["verse_id"] not in PENDING_IDS
            and r["verse_id"] not in visual_reviewed]
    used = set()
    while True:
        best = None
        for r in pool:
            if r["verse_id"] in used:
                continue
            key = coverage.poem_key(r)
            gains = []
            for c in covers(r):
                if need[c] <= 0 or key in filled[c] or key in omar_cell_poems[c]:
                    continue
                sc = component_scores(r, *audit[r["verse_id"]], c[0], r["verse_id"] in renad_ok)
                if is_strong(sc):
                    gains.append((c, sc))
            if not gains:
                continue
            rank = (r["verse_id"] in renad_ok, len(gains), max(sc["total"] for _, sc in gains),
                    -{"low": 0, "medium": 1, "high": 2}[r["annotator_uncertainty"]], -verse_number(r["verse_id"]))
            if best is None or rank > best[0]:
                best = (rank, r, gains)
        if best is None:
            break
        _, r, gains = best
        used.add(r["verse_id"])
        for c, _ in gains:
            need[c] -= 1
            filled[c].add(coverage.poem_key(r))
        selected.append((r, "visual_only" if r["verse_id"] in renad_ok else "emotion_and_visual", "G", gains))
    # Renad-accepted records outside omar with a tier-1 scene group outside the pilot: visual confirmation only
    for r in sorted(prod, key=lambda x: verse_number(x["verse_id"])):
        if r["verse_id"] in omar_rows or r["verse_id"] in used or r["verse_id"] in visual_reviewed:
            continue
        groups_r = [a["target"] for a in r["visual_associations"]
                    if a["target"].startswith("scene_group.") and a["relation"] in TIER1]
        if not groups_r:
            continue
        cells = [(g, e["id"]) for g in groups_r for e in r["emotions"]["primary"]]
        gains = [(c, component_scores(r, *audit[r["verse_id"]], c[0], True)) for c in cells]
        used.add(r["verse_id"])
        selected.append((r, "visual_only", "V2", gains))
    order = {"G": 0, "V2": 1}
    selected.sort(key=lambda x: (x[1] != "visual_only", order[x[2]], -max(sc["total"] for _, sc in x[3]),
                                 verse_number(x[0]["verse_id"])))
    cells_after = {f"{g}|{e}": {"dev_tier1_poems": len(dev_poems[(g, e)]),
                                "omar_poems": len(omar_cell_poems[(g, e)]),
                                "omar_strong_poems": len(omar_cell_strong[(g, e)]),
                                "priority_v2_added": sum(1 for s in selected if s[2] == "G" and any(c == (g, e) for c, _ in s[3])),
                                "strong_after": len(filled[(g, e)]),
                                "production_ai_visual_poems": mats["production_ai_visual"][f"{g}|{e}"]["tier1_poems"]}
                   for g, e in pilot}

    write_outputs(tax, recs, by_id, prod, stats, mats, audit, flag_counts, flag_records, dup_pairs, poets, poems,
                  cell_concentration, scores, hist, omar, omar_order, selected, cells_after, renad_ok, pilot,
                  groups, emotions)


def coverage_cells(r, tax, cells):
    out = []
    prim = [e["id"] for e in r["emotions"]["primary"]]
    for a in r["visual_associations"]:
        if a["relation"] in TIER1 and a["target"].startswith("scene_group."):
            for e in prim:
                if (a["target"], e) in cells and (a["target"], e) not in out:
                    out.append((a["target"], e))
    return out


def is_strong(sc):
    return (sc["total"] >= STRONG_THRESHOLD and sc["evidence"] >= 1 and sc["scene_link"] >= 1
            and sc["standalone"] >= 1 and sc["rights"] == 2 and sc["text_attribution"] >= 1)


FLAG_AR = {
    "context_in_meaning": "المعنى المقترح يحيل إلى سياق القصيدة",
    "context_in_justification": "مبرر الوسم أو الإحساس يحيل إلى سياق القصيدة (كما في البيت السابق/السياق)",
    "lead_connective": "يبدأ بأداة ربط تفترض ما قبله (ثم/حتى/إذ...)",
    "lead_pronoun": "يبدأ بضمير أو اسم إشارة بلا مرجع",
    "lead_wa_fa": "يبدأ بالواو أو الفاء (قد تكون عاطفة)",
    "short_verse": "بيت قصير جدًا",
    "missing_hemistich": "شطر فارغ",
    "apcd_text_note": "ملاحظة على نص APCD",
    "love_or_praise_in_meaning": "المعنى يذكر ممدوحًا أو محبوبًا (قد يغلب الغزل/المدح)",
    "span_no_query_term": "دليل الوسم البصري لا يحوي أي لفظ من ألفاظ المشهد في التصنيف",
    "span_no_query_term_extra_only": "دليل الوسم البصري لا يحوي لفظًا من التصنيف (يحوي لفظًا من قائمة البحث الإضافية فقط)",
    "literal_after_negation": "وسم حرفي بعد أداة نفي (قد يكون منفيًا)",
    "literal_in_wish_or_condition": "وسم حرفي في سياق تمنٍّ أو شرط (ليت/لو/لعل)",
    "literal_after_simile_particle": "وسم حرفي بعد أداة تشبيه محتملة (كأن/مثل)",
    "scene_association_generic": "مبرر الارتباط المشهدي عام لا يذكر لفظًا من المشهد ولا من البيت",
    "city_label_check_heritage": "وسم المدينة الحديثة: تحقق أن المدينة ليست قديمة (التراث)",
}

# Auditor reading of the report examples (written by the AI auditor of this audit, NOT a human decision; it
# only says whether the flag looks like a real label problem or a heuristic false positive).
EXAMPLE_NOTES = {
    "pv:verse:000016": "Lexical gap, label plausible: a mountain described by epithets (أرعن، باذخ) with no taxonomy term; text-match retrieval cannot find it.",
    "pv:verse:000017": "Real standalone problem (production record): the heritage scene rests on a pronoun whose referent (Iwan Kisra) is only in the poem.",
    "pv:verse:000022": "Lexical gap, label plausible: الأراكة (arak tree) is greenery but not in the term list.",
    "pv:verse:000023": "Real: the secondary sadness is justified by the next verse (يكمل البيت التالي); also شمس is not a sky_night term although الأفق is in the verse.",
    "pv:verse:000025": "Borderline: الصحو (clear weather) tagged sky_night literal with no sky or night noun.",
    "pv:verse:000029": "Flag false positive: praise of a land's nature, not of a patron; labels fit.",
    "pv:verse:000013": "Real: the three prisons are listed only in the next verse; no visual label, emotion-only production record.",
    "pv:verse:000054": "Real doubt: the sea appears inside a simile (كأن البحر وسّده); dawn literal is fine. Also us_risk rights class.",
    "pv:verse:000056": "Mild: فإذا continues a previous verse, but the sea scene is literal and clear.",
    "pv:verse:000090": "Mild: the meaning names the palace of the previous verse; the verse itself names قصر.",
    "pv:verse:000124": "Real doubt: trees walking to the Prophet (madih nabawi miracle) is not a greenery scene for image retrieval.",
    "pv:verse:000049": "Flag false positive: لا negates يزيد, not the sea.",
    "pv:verse:000063": "Mostly false positive: double negation inside a remembered scene; literal is acceptable.",
    "pv:verse:000075": "Real: very short, the greenery association is justified by the previous verse; us_risk rights class.",
    "pv:verse:000192": "Real: Baghdad mourning its past glory is a pre-modern city; the QA rule sends it to heritage, it is still city.",
    "pv:verse:000241": "Mild: «هذا» is a transitional formula; the desert scene (فلاة) is clear.",
    "pv:verse:000453": "Real doubt: الساحل is a place name near Mecca, so sea literal is doubtful; the desert association is justified by the context.",
    "pv:verse:000545": "Real: Ghumdan appears only inside a لو clause; relation should probably be hypothetical, not literal.",
    "pv:verse:000732": "Flag partly false positive: the justification is specific (a ruined old mosque); whether a ruined mosque is heritage is a reviewer call.",
    "pv:verse:000831": "Real: the valley and monastery appear only inside a لو clause; hypothetical rather than literal.",
}


def visual_text(tax, assoc_rows):
    parts = []
    for i in assoc_rows:
        basis = f"الدليل: «{i['span']}»" if i["span"] else f"المبرر: {i['justification'] or ''}"
        parts.append(f"{name_ar(tax, i['target'])} — {name_ar(tax, i['relation'])} — {basis}")
    return "؛ ".join(parts) or "لا يوجد"


def breakdown(sc):
    return (f"المعنى {sc['meaning']}، الاستقلال {sc['standalone']}، وضوح الدليل {sc['evidence']}، "
            f"قوة المشهد {sc['scene_link']}، قوة الإحساس {sc['emotion_link']}، النص والنسبة {sc['text_attribution']}، "
            f"الحقوق {sc['rights']}")


CSV_FIELDS = ["rank", "group", "review_scope", "target_cells", "text_original", "meaning_ar", "poet", "era",
              "proposed_primary", "proposed_secondary", "emotion_basis", "evidence_text", "justification_ar",
              "emotion_review", "proposed_visual_labels", "triage_score", "score_breakdown", "triage_reasons",
              "decision", "corrected_primary", "corrected_secondary", "visual_decision", "note",
              "verse_id", "apcd_row", "attribution_status", "copyright_class", "text_note", "annotation_method"]


def sheet_row(n, r, tax, audit, scope, group, gains, renad_ok):
    flags, assoc_rows = audit[r["verse_id"]]
    emo = r["emotions"]
    best = max(gains, key=lambda x: x[1]["total"])[1]
    reasons = ["؛ ".join(sorted({FLAG_AR[c] for c, _, _ in flags}))] if flags else []
    return {
        "rank": n, "group": group, "review_scope": scope,
        "target_cells": "؛ ".join(f"{name_ar(tax, g)} × {name_ar(tax, e)}" for (g, e), _ in gains),
        "text_original": r["text_original"], "meaning_ar": r.get("meaning_ar") or "",
        "poet": r["poet"]["name_apcd"], "era": r["era_apcd"],
        "proposed_primary": "، ".join(name_ar(tax, e["id"]) for e in emo["primary"]),
        "proposed_secondary": "، ".join(name_ar(tax, e["id"]) for e in emo["secondary"]) or "لا يوجد",
        "emotion_basis": "، ".join(f"{name_ar(tax, e['id'])}: {e['basis']}" for e in emo["primary"]),
        "evidence_text": "؛ ".join(e["evidence_span"]["text"] for e in emo["primary"] if e.get("evidence_span")),
        "justification_ar": "؛ ".join(f"{name_ar(tax, e['id'])}: {e['justification_ar']}"
                                      for e in emo["primary"] + emo["secondary"] if e.get("justification_ar")),
        "emotion_review": "مقبول من human:renad (الإحساس فقط)" if r["verse_id"] in renad_ok else "مسودة آلية لم تُراجع",
        "proposed_visual_labels": visual_text(tax, assoc_rows),
        "triage_score": best["total"], "score_breakdown": breakdown(best),
        "triage_reasons": reasons[0] if reasons else "لا تنبيهات آلية",
        "decision": "", "corrected_primary": "", "corrected_secondary": "", "visual_decision": "", "note": "",
        "verse_id": r["verse_id"], "apcd_row": r["apcd_row"], "attribution_status": r["attribution_status"],
        "copyright_class": copyright_status(r), "text_note": r.get("text_note") or "",
        "annotation_method": f"{r['annotation']['method']} / {r['review']['status']}",
    }


def write_csv(path, rows, fields):
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({f: row.get(f, "") for f in fields})


def example_list(recs, audit, renad_ok, omar_ids, prod_ids, tax):
    """Deterministic examples: up to 2 per flag code, production and omar rows first."""
    picked, out = collections.Counter(), []
    order = sorted(recs, key=lambda r: (r["verse_id"] not in prod_ids, r["verse_id"] not in omar_ids,
                                        verse_number(r["verse_id"])))
    quota = {"span_no_query_term": 3, "literal_after_negation": 2, "literal_in_wish_or_condition": 2,
             "scene_association_generic": 2, "context_in_meaning": 2, "context_in_justification": 2, "lead_pronoun": 1, "lead_connective": 1,
             "short_verse": 1, "love_or_praise_in_meaning": 2, "literal_after_simile_particle": 1,
             "city_label_check_heritage": 1}
    used = set()
    for r in order:
        flags, assoc_rows = audit[r["verse_id"]]
        for code, _, detail in flags:
            if code in quota and picked[code] < quota[code] and r["verse_id"] not in used:
                picked[code] += 1
                used.add(r["verse_id"])
                labels = "؛ ".join(f"{i['target']}:{i['relation'].split('.')[1]}" + (f" «{i['span']}»" if i["span"] else
                                   f" ({i['justification']})") for i in assoc_rows) or "-"
                emo = ", ".join(e["id"].split(".")[1] for e in r["emotions"]["primary"])
                out.append({"verse_id": r["verse_id"], "flag": code, "detail": detail, "text": r["text_original"],
                            "visual": labels, "primary": emo, "meaning_ar": r.get("meaning_ar") or "",
                            "in_production": r["verse_id"] in prod_ids, "in_priority_v1": r["verse_id"] in omar_ids})
    return out


def write_outputs(tax, recs, by_id, prod, stats, mats, audit, flag_counts, flag_records, dup_pairs, poets, poems,
                  cell_concentration, scores, hist, omar, omar_order, selected, cells_after, renad_ok, pilot,
                  groups, emotions):
    os.makedirs(OUT_DIR, exist_ok=True)
    prod_ids = {r["verse_id"] for r in prod}
    omar_ids = {row["verse_id"] for row in omar["rows"]}
    rows = [sheet_row(n, r, tax, audit, scope, group, gains, renad_ok)
            for n, (r, scope, group, gains) in enumerate(selected, 1)]
    for row in rows:  # verbatim check: every sheet text equals the record text
        assert row["text_original"] == by_id[row["verse_id"]]["text_original"]
        assert not any(row[f] for f in ("decision", "corrected_primary", "corrected_secondary", "visual_decision", "note"))
    sheet = os.path.join(OUT_DIR, "review_sheet_priority_v2.csv")
    write_csv(sheet, rows, CSV_FIELDS)
    order_rows = []
    for n, (vid, row, best, cell_scores) in enumerate(omar_order, 1):
        r = by_id[vid]
        flags, _ = audit[vid]
        sc = max((s for _, s in cell_scores), key=lambda s: s["total"], default=scores[vid])
        order_rows.append({"suggested_order": n, "verse_id": vid, "priority_v1": row["priority"],
                           "omar_scope": row["scope"], "text_original": r["text_original"],
                           "pilot_cells": "؛ ".join(f"{name_ar(tax, g)} × {name_ar(tax, e)}" for (g, e), _ in cell_scores),
                           "triage_score": sc["total"], "score_breakdown": breakdown(sc),
                           "strong": "نعم" if is_strong(sc) else "لا",
                           "triage_reasons": "؛ ".join(sorted({FLAG_AR[c] for c, _, _ in flags})) or "لا تنبيهات آلية"})
    order_fields = ["suggested_order", "verse_id", "priority_v1", "omar_scope", "text_original", "pilot_cells",
                    "triage_score", "strong", "score_breakdown", "triage_reasons"]
    order_path = os.path.join(OUT_DIR, "priority_v1_order.csv")
    write_csv(order_path, order_rows, order_fields)

    examples = example_list(recs, audit, renad_ok, omar_ids, prod_ids, tax)
    pilot_keys = [f"{g}|{e}" for g, e in pilot]
    gap_prod_ai = [k for k in pilot_keys if mats["production_ai_visual"][k]["tier1_poems"] == 0]
    gap_dev_lt3 = [k for k in pilot_keys if mats["development"][k]["tier1_poems"] < 3]
    all_keys = [f"{g}|{e}" for g in groups for e in emotions]
    omar_strong = sum(1 for o in order_rows if o["strong"] == "نعم")
    per_record = {vid: {"score": s, "flags": sorted({c for c, _, _ in audit[vid][0]})} for vid, s in scores.items()}

    summary = {
        "generated_by": "poetry_corpus/review_packages/priority_v2/build_priority_v2.py",
        "corpus": "poetry_corpus/exports/corpus_all_v2.jsonl", "corpus_sha256": sha256_file(CORPUS),
        "omar_manifest_sha256": sha256_file(OMAR_MANIFEST),
        "note": "AI-draft labels audited with transparent heuristics; no accuracy is claimed and no decision recorded.",
        "pools": stats,
        "coverage": {"pilot_cells": pilot_keys, "matrices": mats,
                     "pilot_cells_zero_production_ai_visual": gap_prod_ai,
                     "pilot_cells_zero_production_reviewed_visual": [k for k in pilot_keys if
                                                                     mats["production_reviewed_visual"][k]["tier1_poems"] == 0],
                     "pilot_cells_dev_below_3_poems": gap_dev_lt3,
                     "all_cells_zero_production_ai_visual": sum(1 for k in all_keys if mats["production_ai_visual"][k]["tier1_poems"] == 0),
                     "all_cells_zero_development": sum(1 for k in all_keys if mats["development"][k]["tier1_poems"] == 0)},
        "heuristics": {"flag_occurrences": {k: dict(v) for k, v in flag_counts.items()},
                       "flag_records": {k: dict(v) for k, v in flag_records.items()},
                       "shared_hemistich_pairs": dup_pairs,
                       "top_poets": poets.most_common(10),
                       "poems_with_more_than_one_verse": sum(1 for v in poems.values() if v > 1),
                       "max_verses_per_poem": max(poems.values()),
                       "pilot_cell_poet_concentration": cell_concentration,
                       "examples": examples},
        "scoring": {"components": ["meaning", "standalone", "evidence", "scene_link", "emotion_link",
                                   "text_attribution", "rights"], "max_total": 14,
                    "strong_threshold": STRONG_THRESHOLD, "histogram_total": dict(sorted(hist.items())),
                    "strong_records_best_group": sum(1 for vid in scores if is_strong(scores[vid]))},
        "priority_v2": {"rows": len(rows), "cell_target_strong_poems": CELL_TARGET,
                        "by_group": dict(collections.Counter(r["group"] for r in rows)),
                        "by_scope": dict(collections.Counter(r["review_scope"] for r in rows)),
                        "overlap_with_priority_v1": sorted({r["verse_id"] for r in rows} & omar_ids),
                        "omar_rows_strong": omar_strong, "omar_rows": len(order_rows),
                        "cells": cells_after,
                        "verse_ids": [r["verse_id"] for r in rows]},
        "per_record": per_record,
    }
    with open(os.path.join(REPORTS, "label_audit_v2.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    manifest = {"package": "priority_v2", "corpus": summary["corpus"], "corpus_sha256": summary["corpus_sha256"],
                "files": {"csv": "review_sheet_priority_v2.csv", "omar_order": "priority_v1_order.csv"},
                "xlsx": "not written: openpyxl is not installed in .venv (instruction: CSV only)",
                "verse_ids": summary["priority_v2"]["verse_ids"],
                "rows": [{"verse_id": r["verse_id"], "group": r["group"], "scope": r["review_scope"],
                          "triage_score": r["triage_score"]} for r in rows],
                "excluded": {"priority_v1_rows": "not duplicated; ranked in priority_v1_order.csv",
                             "pending_renad": sorted(PENDING_IDS)},
                "cells": cells_after, "decision_cells_empty": True,
                "text_verbatim_checked": len(rows)}
    with open(os.path.join(OUT_DIR, "priority_v2_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    write_markdown(tax, summary, mats, pilot, groups, emotions, stats, examples, rows, order_rows, cells_after)
    print(json.dumps({k: summary["priority_v2"][k] for k in ("rows", "by_group", "by_scope", "omar_rows_strong")},
                     ensure_ascii=False))


def fmt_matrix(tax, mat, gs, es, field="tier1_poems"):
    lines = ["| scene_group \\ lit_emotion | " + " | ".join(e.split(".")[1] for e in es) + " |",
             "|---" * (len(es) + 1) + "|"]
    for g in gs:
        lines.append(f"| {g.split('.')[1]} | " + " | ".join(str(mat[f'{g}|{e}'][field]) for e in es) + " |")
    return "\n".join(lines)


def write_markdown(tax, s, mats, pilot, groups, emotions, stats, examples, rows, order_rows, cells_after):
    P, D = stats["production"], stats["development"]
    pg, pe = tax.pilot["scene_groups"], tax.pilot["lit_emotions"]
    h = s["heuristics"]
    fr_d, fr_p = h["flag_records"]["development"], h["flag_records"]["production"]
    L = []
    a = L.append
    a("# Label audit v2: AI-draft labels in corpus_all_v2 (retrieval view)")
    a("")
    a(f"Generated by `{s['generated_by']}` from `{s['corpus']}` (sha256 `{s['corpus_sha256'][:12]}…`). "
      "Machine-readable twin with per-record scores: `label_audit_v2.json`.")
    a("")
    a("**Status of the labels.** All 1,053 records carry AI-draft labels (`claude-opus-5-5`). Human review so far: "
      "35 emotion ACCEPT decisions by `human:renad` (P0), 0 visual decisions, 0 meaning decisions. Every count below "
      "describes AI drafts unless it says otherwise. The heuristics flag *candidates for doubt*; they are not error "
      "counts and no accuracy figure is claimed. The only accuracy-like figure that exists is the earlier automated "
      "QA sample (`exports/qa_audit_report_v1.md`: 144 P2 records audited by AI auditors, 67% ok / 24% fix / 10% "
      "reject), which is itself an AI judgement, not human review.")
    a("")
    a("## 1. Production pool (35) vs development pool (1,053)")
    a("")
    a("| Measure | Production (display_allowed production) | Development |")
    a("|---|---|---|")

    def row(label, k, sub=None):
        pv, dv = P[k], D[k]
        if sub is not None:
            pv, dv = pv.get(sub, 0), dv.get(sub, 0)
        a(f"| {label} | {pv} | {dv} |")
    row("Records", "records")
    row("Distinct poets", "distinct_poets")
    a(f"| Distinct poems (poet, meter, rhyme) | {P['distinct_poems']} | {D['distinct_poems']} |")
    row("meaning_ar present", "meaning_ar_present")
    row("Records with no tier-1 scene-group relation", "records_without_scene_group_tier1")
    row("Records with no visual association at all", "records_without_any_visual")
    for k in ("apcd_only", "source_verified", "disputed"):
        row(f"Attribution `{k}`", "attribution_status", k)
    for k in ("public_domain_classical", "public_domain_all", "us_risk", "unverified"):
        row(f"Copyright class `{k}` (export_corpus.copyright_status)", "copyright_class", k)
    for k in ("low", "medium", "high"):
        row(f"annotator_uncertainty `{k}`", "annotator_uncertainty", k)
    row("APCD text_note present", "text_note_present")
    for k in ("primary:expressed", "primary:evoked", "secondary:expressed", "secondary:evoked"):
        row(f"Emotion basis `{k}`", "emotion_basis", k)
    for k in ("primary:with_span", "primary:no_span"):
        row(f"Emotion evidence span `{k}`", "emotion_span", k)
    a("")
    a("Note: the 35 production records are displayable because their **emotion** was accepted; none of their visual "
      "associations has been reviewed. With the SPEC rule (tier 1 needs a reviewed scene relation), the production "
      "pool currently supports **0 tier-1 results in every cell**.")
    a("")
    a("### Relation types (all targets; visual associations, not records)")
    a("")
    a("| Relation | Production | Development | Development: with evidence span |")
    a("|---|---|---|---|")
    for rel in RELATIONS:
        a(f"| {rel.split('.')[1]} | {P['relations_total'].get(rel, 0)} | {D['relations_total'].get(rel, 0)} | "
          f"{D['visual_span_by_relation'].get(rel, {}).get('with_span', 0)} |")
    a("")
    a("No `negated` or `ambiguous` relation exists anywhere; `hypothetical` only twice. Section 2 shows literal "
      "relations that sit after a negation or inside a wish, so the absence of these relation types is more likely "
      "under-use than a property of the verses.")
    a("")
    a("Per target (development; literal / scene_association / symbolic / hypothetical):")
    a("")
    a("| Target | literal | scene_assoc | symbolic | hypothetical | production literal / scene_assoc |")
    a("|---|---|---|---|---|---|")
    for t, c in D["relations_by_target"].items():
        pc = P["relations_by_target"].get(t, {})
        a(f"| {t} | {c.get('relation.literal', 0)} | {c.get('relation.scene_association', 0)} | "
          f"{c.get('relation.symbolic', 0)} | {c.get('relation.hypothetical', 0)} | "
          f"{pc.get('relation.literal', 0)} / {pc.get('relation.scene_association', 0)} |")
    a("")
    a("### Pilot matrix, tier-1 distinct poems (5 x 5)")
    a("")
    a("Development (all AI drafts):")
    a("")
    a(fmt_matrix(tax, mats["development"], pg, pe))
    a("")
    a("Production, counting the **unreviewed** AI visual associations of the 35 emotion-reviewed records:")
    a("")
    a(fmt_matrix(tax, mats["production_ai_visual"], pg, pe))
    a("")
    a("Production with a human-reviewed visual relation (the SPEC tier-1 rule): **0 in all 25 pilot cells** "
      "(and in all 72 cells).")
    a("")
    cz = s["coverage"]
    a(f"- Pilot cells with 0 production poems even counting AI visual labels: **{len(cz['pilot_cells_zero_production_ai_visual'])}/25**: "
      + ", ".join(f"`{k.replace('scene_group.', '').replace('lit_emotion.', '')}`" for k in cz["pilot_cells_zero_production_ai_visual"]) + ".")
    a(f"- Pilot cells with fewer than 3 development poems (cannot reach 3 even if every draft is accepted): "
      f"{len(cz['pilot_cells_dev_below_3_poems'])}" + (": " + ", ".join(f"`{k}`" for k in cz["pilot_cells_dev_below_3_poems"]) if cz["pilot_cells_dev_below_3_poems"] else "") + ".")
    a(f"- All 72 cells (9 x 8): {cz['all_cells_zero_production_ai_visual']} have 0 production poems (AI visual); "
      f"{cz['all_cells_zero_development']} have 0 development poems.")
    a("")
    a("Full 9 x 8 development matrix:")
    a("")
    a(fmt_matrix(tax, mats["development"], groups, emotions))
    a("")
    a("## 2. Label-quality heuristics")
    a("")
    a("Rules (all on folded text: diacritics removed, hamza/alef/ya/ta-marbuta unified, the same `fold` and "
      "clitic `variants` as `tools/find_candidates.py`):")
    a("")
    a("- **span_no_query_term**: the evidence span of a visual association contains no surface form of the "
      "target's taxonomy `query_terms_ar` (scene group terms plus the terms of its member tags). "
      "`..._extra_only` = the span matches only the extra search terms used by the candidate finder "
      "(`EXTRA_SCENE_TERMS`, not part of the taxonomy), e.g. شمس, ريح.")
    a("- **literal_after_negation**: a literal span preceded (within 2 words, same hemistich) by لا/لم/ما/ليس/لن/غير/بلا; "
      "**literal_in_wish_or_condition**: ليت/لو/لعل earlier in the same hemistich; **literal_after_simile_particle**: "
      "كأن/مثل within 2 words (weak: folded كأن equals كان).")
    a("- **scene_association_generic**: the justification contains neither a scene term of the target nor any "
      "content word (3+ letters) of the verse.")
    a("- **context_in_justification**: a visual or emotion justification mentions «السياق», «البيت السابق» … "
      "(the label rests on a verse the reader will not see).")
    a("- **context_in_meaning**: the AI meaning mentions «القصيدة», «السياق», «السابق», «ما قبله», «يكمل» … («في سياق» alone is ignored: it names a genre, not another verse); "
      "**lead_connective** (ثم/حتى/إذ/فإذا/بل/لكن), **lead_pronoun** (هو/هي/هم/ذلك/تلك/الذي …) as first word; "
      "**lead_wa_fa** (weak: و/ف may be a root letter); **short_verse** < 30 folded letters; **apcd_text_note**.")
    a("- **love_or_praise_in_meaning**: the AI meaning names a ممدوح/محبوب/غزل/خمر (the QA audit's most common "
      "emotion error: ghazal or madih treated as the target emotion).")
    a("- **city_label_check_heritage**: any `scene_group.city` label (QA rule: pre-modern cities belong to heritage).")
    a("")
    a("| Flag | Records (development) | Records (production 35) |")
    a("|---|---|---|")
    for code in FLAG_AR:
        a(f"| {code} | {fr_d.get(code, 0)} | {fr_p.get(code, 0)} |")
    a("")
    a(f"- Shared full hemistichs (folded): {len(h['shared_hemistich_pairs'])} pairs: "
      + ", ".join(f"`{x}`–`{y}`" for x, y in h["shared_hemistich_pairs"]) + " (same as `duplicate_report_v1.md`).")
    a(f"- Concentration: {h['poems_with_more_than_one_verse']} poems have more than one verse (max {h['max_verses_per_poem']}); "
      "top poets: " + ", ".join(f"{p} {n}" for p, n in h["top_poets"][:6]) + ".")
    conc = sorted(h["pilot_cell_poet_concentration"].items(), key=lambda kv: -kv[1]["share"])[:5]
    a("- Highest single-poet share inside a pilot cell (development tier-1 records): "
      + "; ".join(f"`{k}` {v['top_poet']} {v['top_poet_records']}/{v['tier1_records']}" for k, v in conc) + ".")
    a("- Reused from `exports/qa_audit_report_v1.md` (AI QA of 144 P2 records): its error types are emotion taken "
      "from a single word, ghazal/madih accepted as neutral, figurative or wished-for scenes tagged literal, meaning "
      "borrowed from another verse, old cities tagged city. Its patches (30 fixes, 14 rejects, 74 city→heritage, "
      "26 ليت→hypothetical) were applied in the merge; the QA report states that the unsampled records likely carry "
      "the same error types at a similar rate. The flags `literal_in_wish_or_condition`, "
      "`literal_after_simile_particle`, `love_or_praise_in_meaning` and `context_in_meaning` look for exactly those "
      "residual types. Note: the corpus now holds only 2 hypothetical relations, so most of the 26 converted "
      "relations left with their dropped verses; this could not be reconciled further from the exports.")
    a("")
    a("### Concrete examples (verbatim text copied from `text_original`)")
    a("")
    a("Last column: the auditor's reading (AI, not a human decision) of whether the flag is a real label problem "
      "or a heuristic false positive. Of the examples below, about half are real problems and the rest are "
      "lexical gaps or false positives, which is why the flag counts above are upper bounds, not error counts.")
    a("")
    a("| verse_id | flag | AI labels (visual; primary emotion) | text | why flagged | auditor reading (AI) |")
    a("|---|---|---|---|---|---|")
    for ex in examples:
        where = " [production]" if ex["in_production"] else (" [priority_v1]" if ex["in_priority_v1"] else "")
        a(f"| {ex['verse_id']}{where} | {ex['flag']} | {ex['visual']}; {ex['primary']} | {ex['text']} | "
          f"{FLAG_AR[ex['flag']]} ({ex['detail']}) | {EXAMPLE_NOTES.get(ex['verse_id'], '-')} |")
    a("")
    a("## 3. Triage score (0–14)")
    a("")
    a("Seven components, 0–2 each. A **triage heuristic for ordering review, not a measure of label quality**:")
    a("")
    a("| Component | 2 | 1 | 0 |")
    a("|---|---|---|---|")
    a("| meaning | meaning_ar ≥ 10 words, no context marker | shorter, or mentions poem context | absent |")
    a("| standalone | no flag | only lead_wa_fa | context_in_meaning, context_in_justification, lead_connective, lead_pronoun, short_verse or missing hemistich (an APCD text_note counts only under text_attribution) |")
    a("| evidence (best tier-1 scene relation for the cell) | literal span containing a taxonomy scene term | literal span without a term, or specific scene_association | generic scene_association, or no tier-1 relation |")
    a("| scene_link | literal with no cue | literal after simile particle, or a city label | literal after negation / inside wish, generic scene_association, none; scene_association = 1 |")
    a("| emotion_link | emotion accepted by human:renad, or expressed with span and low uncertainty | evoked/low or expressed/medium | high uncertainty, or further −1 for love/praise marker |")
    a("| text_attribution | source_verified, no text_note | apcd_only, no text_note | text_note or disputed |")
    a("| rights | public_domain_classical / public_domain_all | – | us_risk / unverified |")
    a("")
    a(f"\"Strong\" candidate for a cell = total ≥ {STRONG_THRESHOLD}, evidence ≥ 1, scene_link ≥ 1, standalone ≥ 1, "
      "rights 2, text_attribution ≥ 1. Histogram of totals (best scene group per record): "
      + ", ".join(f"{k}: {v}" for k, v in s["scoring"]["histogram_total"].items())
      + f". Strong records: {s['scoring']['strong_records_best_group']} of 1,053.")
    a("")
    a("## 4. priority_v2 review list")
    a("")
    pv = s["priority_v2"]
    a(f"`priority_v1` (56 rows) already schedules up to three poems for every pilot cell, so it covers the pilot "
      f"gaps well on paper. Scored with the rule above, {pv['omar_rows_strong']} of its 56 rows are strong for at "
      "least one of their cells. priority_v2 therefore does **not** duplicate priority_v1: it is a complement that "
      f"brings every pilot cell to {CELL_TARGET} *strong* distinct poems where priority_v1's own strong rows fall "
      "short (group G), plus emotion-accepted records outside priority_v1 that only need visual confirmation "
      f"(group V2). Rows: **{pv['rows']}** ({', '.join(f'{k} {v}' for k, v in pv['by_group'].items())}; "
      f"{', '.join(f'{k} {v}' for k, v in pv['by_scope'].items())}); overlap with priority_v1: "
      f"{len(pv['overlap_with_priority_v1'])}. `priority_v1_order.csv` ranks the existing 56 (no decision "
      "columns; decisions stay in Omar's workbook).")
    a("")
    a("| Pilot cell | dev poems | production poems (AI visual) | omar poems | omar strong | priority_v2 added | strong after |")
    a("|---|---|---|---|---|---|---|")
    for k, v in cells_after.items():
        a(f"| {k.replace('scene_group.', '').replace('lit_emotion.', '')} | {v['dev_tier1_poems']} | "
          f"{v['production_ai_visual_poems']} | {v['omar_poems']} | {v['omar_strong_poems']} | "
          f"{v['priority_v2_added']} | {v['strong_after']} |")
    a("")
    a("Files: `poetry_corpus/review_packages/priority_v2/` (`review_sheet_priority_v2.csv` UTF-8 BOM with empty "
      "decision columns, `priority_v1_order.csv`, `priority_v2_manifest.json`, `README_AR.md`). No xlsx: openpyxl "
      "is not installed in `.venv`.")
    a("")
    a("## 5. Limits")
    a("")
    a("- Heuristics are lexical. Substring-free token matching misses broken plurals not in the term list and may "
      "accept a homograph; negation/wish cues ignore scope. Counts are flags, not errors.")
    a("- Person and place names that need the poem (e.g. a patron's name) are only caught when the AI meaning "
      "mentions a ممدوح or the poem context.")
    a("- The score treats the AI's own `annotator_uncertainty` as a signal, which is self-reported by the drafting model.")
    with open(os.path.join(REPORTS, "label_audit_v2.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
