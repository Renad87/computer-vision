"""Compact priority review package for Omar: the 25 pilot cells (5 scene groups x 5 literary emotions).

    python3 -m poetry_corpus.review.build_priority_review [--corpus poetry_corpus/exports/corpus_all_v2.jsonl]
        [--levels ABC]

Selection (deterministic):
1. "visual-only" rows: records whose emotion a human already accepted (review.decisions emotion accept) and
   whose AI scene association puts them in a pilot cell at tier 1. Only the visual decision is asked; the
   emotion cells stay empty so no decision is recorded twice.
2. the greedy pilot cover of poetry_corpus.tools.build_review_package.priority_levels over the records still
   not_reviewed (and not pending clarification on a returned sheet), seeded with the rows of step 1, so each
   pilot cell reaches up to three distinct poems (levels A, B, C). These rows need emotion and visual decisions.

Every reviewer cell is empty. Nothing here records a review. Returned workbook:
    python3 -m poetry_corpus.review.import_review <returned.xlsx> --reviewer human:omar \
        --base poetry_corpus/exports/corpus_all_v2.jsonl --out-version v3 \
        --sent poetry_corpus/review_packages/priority_v1/<workbook>.xlsx
"""
import argparse
import csv
import json
import os
import sys

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import load_jsonl

from poetry_corpus.tools import build_review_package as P
from poetry_corpus.tools.build_batch import verse_number
from poetry_corpus.tools.build_p0_drafts import EMOTION_ORDER
from poetry_corpus.tools.review_sheet import (DECISIONS, NONE_AR, SHEET_EMOTIONS, SHEET_INSTRUCTIONS, SHEET_REVIEW,
                                              VISUAL_DECISIONS, header_text, read_review, rtl)
from poetry_corpus.tools.xlsx import Workbook, col_letter

from .import_review import ROOT, sha256_file

OUT_DIR = os.path.join(ROOT, "poetry_corpus", "review_packages", "priority_v1")
CORPUS = os.path.join(ROOT, "poetry_corpus", "exports", "corpus_all_v2.jsonl")
IMPORT_REPORT = os.path.join(ROOT, "poetry_corpus", "reports", "review_import_v2.json")
SCOPE_VISUAL, SCOPE_BOTH = "visual_only", "emotion_and_visual"
SCOPE_AR = {SCOPE_VISUAL: "الوسم البصري فقط (الإحساس مقبول سابقًا)", SCOPE_BOTH: "الإحساس والوسم البصري"}
REVIEWER_FIELDS = ("decision", "corrected_primary", "corrected_secondary", "visual_decision", "note")

COLUMNS = [  # (field, Arabic header, width, style)
    ("n", "رقم", 6, "number"),
    ("priority", "الأولوية", 9, "text"),
    ("review_scope", "المطلوب", 18, "text"),
    ("text_original", "البيت كما في APCD", 46, "verse"),
    ("meaning_ar", "المعنى (مسودة)", 36, "text"),
    ("poet", "الشاعر", 16, "text"),
    ("proposed_primary", "الإحساس الأساسي المقترح", 16, "text"),
    ("proposed_secondary", "الإحساسات الثانوية المقترحة", 18, "text"),
    ("evidence_text", "الدليل النصي للإحساس", 24, "text"),
    ("justification_ar", "مبرر الإحساس", 30, "text"),
    ("emotion_review", "حالة مراجعة الإحساس", 20, "text"),
    ("proposed_visual_labels", "الوسوم البصرية المقترحة مع الدليل", 40, "text"),
    ("pilot_cells", "الخلايا التجريبية", 26, "text"),
    ("decision", "قرار الإحساس", 13, "editable"),
    ("corrected_primary", "الأساسي المصحح", 18, "editable"),
    ("corrected_secondary", "الثانوي المصحح", 18, "editable"),
    ("visual_decision", "قرار الوسم البصري", 14, "editable"),
    ("note", "ملاحظة المراجِع", 32, "editable"),
    ("era", "العصر", 14, "text"),
    ("verse_id", "معرّف البيت", 17, "text"),
    ("apcd_row", "صف APCD", 10, "number"),
    ("text_note", "ملاحظة على نص APCD", 26, "text"),
    ("attribution_status", "حالة النسبة", 16, "text"),
    ("annotation_method", "حالة التعليق", 22, "text"),
]
CSV_FIELDS = [f for f, _, _, _ in COLUMNS if f != "n"]


def name_ar(taxonomy, label_id):
    return taxonomy.labels[label_id]["name_ar"]


def visual_text(record, taxonomy):
    parts = []
    for a in record["visual_associations"]:
        span = (a.get("evidence_span") or {}).get("text")
        basis = f"الدليل: «{span}»" if span else f"المبرر: {a.get('justification_ar') or ''}"
        parts.append(f"{name_ar(taxonomy, a['target'])} — {name_ar(taxonomy, a['relation'])} — {basis}")
    return "؛ ".join(parts) or NONE_AR


def select(records, taxonomy, pending_ids, levels):
    accepted = [r for r in records if any(d["dimension"] in ("emotion", "all") and d["decision"] == "accept"
                                          for d in r["review"]["decisions"])]
    visual_done = {r["verse_id"] for r in records if any(d["dimension"] in ("visual", "all")
                                                         for d in r["review"]["decisions"])}
    seed = [r for r in accepted if r["verse_id"] not in visual_done and P.pilot_covers(r, taxonomy)]
    candidates = [r for r in records if r["review"]["status"] == "not_reviewed" and r["verse_id"] not in pending_ids]
    assigned, poems = P.priority_levels(candidates, taxonomy, seed)
    order = {lvl: i for i, lvl in enumerate(P.LEVELS)}
    new = sorted((r for r in candidates if assigned.get(r["verse_id"]) in levels),
                 key=lambda r: (order[assigned[r["verse_id"]]], verse_number(r["verse_id"])))
    chosen = [(r, "V", SCOPE_VISUAL) for r in sorted(seed, key=lambda r: verse_number(r["verse_id"]))]
    chosen += [(r, assigned[r["verse_id"]], SCOPE_BOTH) for r in new]
    return chosen, poems


def build_rows(chosen, taxonomy):
    rows = []
    for n, (r, level, scope) in enumerate(chosen, 1):
        emo = r["emotions"]
        primary = emo["primary"]
        justification = "؛ ".join(f"{name_ar(taxonomy, e['id'])}: {e['justification_ar']}"
                                  for e in primary + emo["secondary"] if e.get("justification_ar"))
        evidence = "؛ ".join((e.get("evidence_span") or {}).get("text", "") for e in primary
                            if e.get("evidence_span"))
        reviewers = [d["reviewer_id"] for d in r["review"]["decisions"] if d["dimension"] in ("emotion", "all")]
        rows.append({
            "n": n, "priority": level, "review_scope": scope,
            "text_original": r["text_original"], "meaning_ar": r.get("meaning_ar") or "",
            "poet": r["poet"]["name_apcd"],
            "proposed_primary": "، ".join(name_ar(taxonomy, e["id"]) for e in primary),
            "proposed_secondary": "، ".join(name_ar(taxonomy, e["id"]) for e in emo["secondary"]) or NONE_AR,
            "evidence_text": evidence, "justification_ar": justification,
            "emotion_review": (f"مقبول من {', '.join(reviewers)}" if reviewers else "مسودة آلية لم تُراجع"),
            "proposed_visual_labels": visual_text(r, taxonomy),
            "pilot_cells": "؛ ".join(f"{name_ar(taxonomy, g)} × {name_ar(taxonomy, e)}"
                                    for g, e in P.pilot_covers(r, taxonomy)),
            "decision": "", "corrected_primary": "", "corrected_secondary": "", "visual_decision": "", "note": "",
            "era": r["era_apcd"], "verse_id": r["verse_id"], "apcd_row": r["apcd_row"],
            "text_note": r.get("text_note") or "", "attribution_status": r["attribution_status"],
            "annotation_method": f"{r['annotation']['method']} / {r['review']['status']}",
        })
    return rows


def write_workbook(rows, taxonomy, path, return_name):
    book = Workbook(title="مراجعة أولوية لعمر: الخلايا التجريبية")
    last = len(rows) + 1
    col = {f: i for i, (f, _, _, _) in enumerate(COLUMNS, 1)}
    rng = lambda f: f"{col_letter(col[f])}2:{col_letter(col[f])}{last}"
    n_visual = sum(1 for r in rows if r["review_scope"] == SCOPE_VISUAL)

    s = book.add_sheet(SHEET_INSTRUCTIONS)
    s.widths = {1: 10, 2: 30, 3: 30, 4: 30, 5: 30}
    s.set(1, 1, rtl(f"مراجعة ذات أولوية — الخلايا التجريبية الخمس والعشرون ({len(rows)} بيتًا)"), "title")
    s.merges.append("A1:E1")
    s.heights[1] = 30
    steps = [
        "افتح ورقة «المراجعة». كل صف بيت حقيقي منقول آليًا وحرفيًا من صفه في APCD؛ لا تعدّل نص البيت، "
        "واذكر أي خطأ ظاهر في الملاحظة.",
        "عمود «المطلوب» يحدد ما تحكم فيه: «الوسم البصري فقط» أو «الإحساس والوسم البصري».",
        f"صفوف «الوسم البصري فقط» ({n_visual} صفًا، الأولوية V): قبلت المراجِعة human:renad إحساسها. "
        "اترك أعمدة الإحساس الثلاثة فارغة فيها، واحكم على الوسوم البصرية وحدها.",
        "صفوف «الإحساس والوسم البصري» (الأولوية A ثم B ثم C): كل ما فيها مسودة آلية (ai_draft) لم يراجعها إنسان.",
        "«قرار الإحساس»: ACCEPT (أوافق) أو CORRECT (أصحح) أو REJECT (أرفض) أو UNSURE (غير متأكد). "
        "عند CORRECT اختر «الأساسي المصحح» و/أو «الثانوي المصحح» من القائمة («لا يوجد» للثانوي). "
        "عند ACCEPT أو REJECT أو UNSURE اترك عمودي التصحيح فارغين.",
        "«قرار الوسم البصري»: احكم على الوسوم المقترحة كلها مع علاقتها ودليلها (مثل «البحر والساحل — حرفية»): "
        "ACCEPT إن صحت كلها، REJECT إن لم يصح وسم واحد على الأقل، UNSURE عند الشك.",
        "مع REJECT أو UNSURE (في الإحساس أو الوسم) اكتب ملاحظة قصيرة (20 كلمة كحد أقصى) تذكر السبب.",
        "لا يُستورد إلا القرار الواضح: ACCEPT دون تصحيح. القرار المتناقض (مثل REJECT مع إحساس مصحح) يبقى معلقًا.",
        "احكم على الإحساس الغالب على البيت كله، لا على كلمة معزولة؛ التعريفات في ورقة «الأحاسيس الثمانية».",
        f"احفظ الملف باسم {return_name}.",
    ]
    s.set(3, 1, "الخطوة", "header")
    s.set(3, 2, "التعليمات", "header")
    s.merges.append("B3:E3")
    for i, step in enumerate(steps, 1):
        r = 3 + i
        s.set(r, 1, i, "number")
        s.set(r, 2, rtl(step), "text")
        s.merges.append(f"B{r}:E{r}")
        s.heights[r] = 44
    r = 4 + len(steps) + 1
    s.set(r, 1, "المفتاح", "subtitle")
    s.set(r, 2, "", "editable")
    s.set(r, 3, rtl("الخلايا الصفراء وحدها للتعبئة: قرار الإحساس، الأساسي المصحح، الثانوي المصحح، "
                    "قرار الوسم البصري، ملاحظة المراجِع."), "text")
    s.merges.append(f"C{r}:E{r}")
    s.heights[r] = 36
    r += 2
    review_ref = f"'{SHEET_REVIEW}'!{rng('visual_decision')}"
    s.set(r, 1, "التقدم", "subtitle")
    s.set(r, 2, "صفوف فيها قرار بصري", "text")
    s.formula(r, 3, f"COUNTA({review_ref})", 0)
    s.set(r + 1, 2, "صفوف متبقية", "text")
    s.formula(r + 1, 3, f"{len(rows)}-COUNTA({review_ref})", len(rows))

    e = book.add_sheet(SHEET_EMOTIONS)
    e.widths = {1: 20, 2: 20, 3: 40, 4: 40, 5: 44}
    for c, h in enumerate(["الإحساس", "المعرّف (id)", "التعريف", "يشمل", "لا يشمل"], 1):
        e.set(1, c, h, "header")
    e.freeze = (2, 1)
    for i, label_id in enumerate(EMOTION_ORDER, 2):
        entry = taxonomy.labels[label_id]
        e.set(i, 1, entry["name_ar"], "subtitle")
        e.set(i, 2, label_id, "text")
        e.set(i, 3, rtl(entry["definition_ar"]), "text")
        e.set(i, 4, rtl("؛ ".join(entry["include_ar"])), "text")
        e.set(i, 5, rtl("؛ ".join(entry["exclude_ar"])), "text")
        e.heights[i] = 48

    v = book.add_sheet(SHEET_REVIEW)
    v.landscape = True
    for field, header, width, _ in COLUMNS:
        v.set(1, col[field], header_text(field, header), "header")
        v.widths[col[field]] = width
    v.heights[1] = 48
    for i, row in enumerate(rows, 2):
        for field, _, width, style in COLUMNS:
            v.set(i, col[field], row[field], style)
        longest = max(len(str(row[f])) / max(1, w * 1.2) for f, _, w, _ in COLUMNS)
        v.heights[i] = min(160, 8 + 19 * (int(longest) + 1))
    v.freeze = (2, 5)
    v.autofilter = f"A1:{col_letter(len(COLUMNS))}{last}"
    lit_names = [name_ar(taxonomy, x) for x in EMOTION_ORDER]
    v.validations = [
        (rng("decision"), list(DECISIONS), "قرار الإحساس", "ACCEPT أو CORRECT أو REJECT أو UNSURE؛ فارغ في صفوف الوسم فقط",
         "قيمة غير صحيحة", "اختر من القائمة"),
        (rng("corrected_primary"), lit_names, "الأساسي المصحح", "عند CORRECT فقط", "قيمة غير صحيحة",
         "اختر أحد الأحاسيس الثمانية"),
        (rng("corrected_secondary"), lit_names + [NONE_AR], "الثانوي المصحح", "عند CORRECT فقط، أو «لا يوجد»",
         "قيمة غير صحيحة", "اختر من القائمة"),
        (rng("visual_decision"), list(VISUAL_DECISIONS), "قرار الوسم البصري", "ACCEPT أو REJECT أو UNSURE",
         "قيمة غير صحيحة", "اختر من القائمة"),
    ]
    book.defined_names.append(("_xlnm._FilterDatabase", 2, True,
                               f"'{SHEET_REVIEW}'!$A$1:${col_letter(len(COLUMNS))}${last}"))
    book.active = 0
    book.save(path)


README = """# حزمة مراجعة ذات أولوية لعمر: الخلايا التجريبية

{n} بيتًا تغطي الخلايا التجريبية الخمس والعشرين (5 مجموعات مشهد × 5 أحاسيس أدبية في `taxonomy.pilot`)، مأخوذة من `poetry_corpus/exports/corpus_all_v2.jsonl`.

| الملف | المحتوى |
|---|---|
| `{xlsx}` | ملف العمل: التعليمات، والأحاسيس الثمانية، وورقة «المراجعة» |
| `{csv}` | نسخة CSV (UTF-8 مع BOM) للاستعمال البرمجي |
| `priority_v1_manifest.json` | المعرّفات والأولويات والتغطية ونتيجة التحقق |

## ما في الحزمة

- **V، الوسم البصري فقط ({v} صفًا):** أبيات قبلت المراجِعة `human:renad` إحساسها في P0، ولم يراجع إنسان وسومها البصرية بعد. أعمدة الإحساس تبقى فارغة.
- **A/B/C، الإحساس والوسم البصري ({ab} صفًا):** مسودات آلية لم تُراجع، مختارة بالتغطية الجشعة نفسها في `poetry_corpus/tools/build_review_package.py` (حتى ثلاث قصائد مختلفة لكل خلية بعد احتساب صفوف V): A {a}، B {b}، C {c}.
- **مستبعد:** الأبيات الخمسة المعلقة من ورقة رناد ({pending})؛ تحتاج توضيحًا منها، لا مراجعة جديدة.
- خلايا القرار كلها فارغة، ولا يُسجَّل أي قرار آليًا.

## الإرجاع والاستيراد

احفظ الملف باسم `{ret}`، ثم:

```bash
python3 -m poetry_corpus.review.import_review {ret} --reviewer human:omar \\
    --base poetry_corpus/exports/corpus_all_v2.jsonl --out-version v3 \\
    --sent poetry_corpus/review_packages/priority_v1/{xlsx}
```

يستورد البرنامج ACCEPT الواضح وحده، ويترك ما سواه معلقًا مع السبب في `poetry_corpus/reports/review_import_v3.json`.
"""


def build(corpus=CORPUS, levels=("A", "B", "C"), apcd_zip=None):
    taxonomy = load_taxonomy()
    loaded, issues = load_jsonl(corpus)
    if issues:
        raise SystemExit(f"{corpus}: {issues}")
    records = [r for _, r in loaded]
    pending_ids = set()
    if os.path.exists(IMPORT_REPORT):
        with open(IMPORT_REPORT, encoding="utf-8") as fh:
            pending_ids = {p["verse_id"] for p in json.load(fh)["pending"]}
    chosen, poems = select(records, taxonomy, pending_ids, levels)
    rows = build_rows(chosen, taxonomy)
    os.makedirs(OUT_DIR, exist_ok=True)
    xlsx_name = f"Poetry_Review_Priority_v1_{len(rows)}.xlsx"
    csv_name = "review_sheet_priority_v1.csv"
    ret = "review_priority_v1_v1.xlsx"
    write_workbook(rows, taxonomy, os.path.join(OUT_DIR, xlsx_name), ret)
    with open(os.path.join(OUT_DIR, csv_name), "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(CSV_FIELDS)
        for row in rows:
            w.writerow([row[f] for f in CSV_FIELDS])

    # read both files back: verse text exact, reviewer cells empty, ids in order
    truth = {r["verse_id"]: r["text_original"] for r, _, _ in chosen}
    ids = [r["verse_id"] for r, _, _ in chosen]
    zip_path = apcd_zip or apcd.DEFAULT_ZIP
    rows_apcd = apcd.get_rows([r["apcd_row"] for r, _, _ in chosen], zip_path) if apcd.available(zip_path) else {}
    verification = {}
    for key, name in (("xlsx", xlsx_name), ("csv", csv_name)):
        back = read_review(os.path.join(OUT_DIR, name))
        verification[key] = {
            "rows": len(back),
            "text_matches_records": sum(truth.get(b.get("verse_id")) == b.get("text_original") for b in back),
            "reviewer_cells_filled": sum(1 for b in back for f in REVIEWER_FIELDS if str(b.get(f, "") or "").strip()),
            "ids_in_order": [b.get("verse_id") for b in back] == ids,
        }
        if verification[key] != {"rows": len(ids), "text_matches_records": len(ids), "reviewer_cells_filled": 0,
                                 "ids_in_order": True}:
            raise SystemExit(f"verification failed: {key} {verification[key]}")
    verification["text_matches_apcd"] = (all(rows_apcd[r["apcd_row"]][apcd.VERSE] == r["text_original"]
                                              for r, _, _ in chosen) if rows_apcd else None)
    counts = {lvl: sum(1 for _, l, _ in chosen if l == lvl) for lvl in ("V",) + P.LEVELS}
    manifest = {
        "package": "priority_v1",
        "corpus": os.path.relpath(corpus, ROOT),
        "corpus_sha256": sha256_file(corpus),
        "files": {"xlsx": xlsx_name, "csv": csv_name, "return": ret},
        "levels_included": ["V"] + list(levels),
        "level_counts": counts,
        "verse_ids": ids,
        "rows": [{"verse_id": r["verse_id"], "priority": l, "scope": sc,
                  "pilot_cells": ["|".join(c) for c in P.pilot_covers(r, taxonomy)]} for r, l, sc in chosen],
        "excluded_pending_clarification": sorted(pending_ids),
        "pilot_distinct_poems_if_all_accepted": {"|".join(c): len(v) for c, v in poems.items()},
        "verification": verification,
        "import_command": f"python3 -m poetry_corpus.review.import_review {ret} --reviewer human:omar "
                          f"--base poetry_corpus/exports/corpus_all_v2.jsonl --out-version v3 "
                          f"--sent poetry_corpus/review_packages/priority_v1/{xlsx_name}",
    }
    with open(os.path.join(OUT_DIR, "priority_v1_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(os.path.join(OUT_DIR, "README_AR.md"), "w", encoding="utf-8") as fh:
        fh.write(README.format(n=len(rows), xlsx=xlsx_name, csv=csv_name, v=counts["V"],
                               ab=len(rows) - counts["V"], a=counts["A"], b=counts["B"], c=counts["C"],
                               pending="، ".join(f"`{x}`" for x in sorted(pending_ids)) or "لا شيء", ret=ret))
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--corpus", default=CORPUS)
    parser.add_argument("--levels", default="ABC")
    args = parser.parse_args(argv)
    m = build(args.corpus, tuple(args.levels))
    print(json.dumps({k: m[k] for k in ("level_counts", "verification")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
