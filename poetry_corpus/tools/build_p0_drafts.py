"""Build the P0 AI-draft records and Renad's review package.

    python3 -m poetry_corpus.tools.build_p0_drafts [--apcd-zip PATH] [--kb PATH]

1. Reads the AI-draft specs (poetry_corpus/drafts/p0_ai_draft_specs_v1.json): labels, meanings and evidence
   phrases only, never verse text.
2. Copies each verse verbatim from its APCD row. Evidence phrases are located in the verse ignoring
   diacritics and hamza/alef/ya/ta-marbuta spelling, and the exact original substring is copied.
3. Marks poems that are source-verified in the history knowledge base (data/poems_reference.json of the
   original project, read-only) as source_verified with their evidence ids; all others stay apcd_only.
4. Writes poetry_corpus/records/p0_ai_drafts_v1.jsonl and validates it in production mode against APCD.
5. Writes handoff/renad_p0/: the workbook, the CSV, README_AR.md, annotation_guide_ar.md and the zip,
   then reads the workbook and CSV back and compares every verse with its APCD row.
"""
import argparse
import collections
import json
import os
import re
import shutil
import sys
import zipfile

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, load_jsonl, text_sha256, validate_records

from .review_sheet import CSV_COLUMNS, REVIEWER_FIELDS, build_rows, read_review, write_csv, write_workbook

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPECS = os.path.join(ROOT, "poetry_corpus", "drafts", "p0_ai_draft_specs_v1.json")
RECORDS = os.path.join(ROOT, "poetry_corpus", "records", "p0_ai_drafts_v1.jsonl")
GUIDE = os.path.join(ROOT, "poetry_corpus", "guidelines", "annotation_guide_ar.md")
REPORT = os.path.join(ROOT, "poetry_corpus", "reports", "p0_package_verification.json")
OUT_DIR = os.path.join(ROOT, "handoff", "renad_p0")
DEFAULT_KB = os.environ.get("PV_KB_POEMS",
                            os.path.join(ROOT, "external", "poetry_vision_old", "data", "poems_reference.json"))
TOOL = "poetry_corpus/tools/build_p0_drafts.py"
EMOTION_ORDER = ["lit_emotion.sadness", "lit_emotion.longing", "lit_emotion.loneliness", "lit_emotion.awe",
                 "lit_emotion.serenity", "lit_emotion.joy", "lit_emotion.pride", "lit_emotion.fear"]
FILES = ["Renad_Poetry_Review_40.xlsx", "renad_review_sheet_p0.csv", "README_AR.md", "annotation_guide_ar.md"]
ZIP_NAME = "Renad_Poetry_Review_Package.zip"
DIACRITICS = {chr(c) for c in range(0x064B, 0x0653)} | {"ٰ", "ـ"}
FOLD = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه", "ؤ": "و", "ئ": "ي"}


def locate(text, phrase):
    """Return the span of `phrase` in `text` (one whole-word occurrence) copied from the original text."""
    letters, positions = [], []
    for i, ch in enumerate(text):
        if ch not in DIACRITICS:
            letters.append(FOLD.get(ch, ch))
            positions.append(i)
    plain = "".join(letters)
    query = "".join(FOLD.get(ch, ch) for ch in phrase if ch not in DIACRITICS)
    hits = [m.start() for m in re.finditer(re.escape(query), plain)
            if (m.start() == 0 or not plain[m.start() - 1].isalpha())
            and (m.end() == len(plain) or not plain[m.end()].isalpha())]
    if len(hits) != 1:
        raise SystemExit(f"evidence {phrase!r} found {len(hits)} times in {text!r}")
    start = positions[hits[0]]
    end = positions[hits[0] + len(query) - 1] + 1
    while end < len(text) and text[end] in DIACRITICS:
        end += 1
    return {"start": start, "end": end, "text": text[start:end]}


def load_kb(path):
    with open(path, encoding="utf-8") as fh:
        records = json.load(fh)["records"]
    verified = {"verified", "well_supported"}
    by_row = {}
    for record in records:
        if record.get("attribution_status") not in verified:
            continue
        for row in record["apcd_reference"].get("verse_rows_located") or []:
            by_row[row] = record
    return by_row


def build_records(specs, rows, kb_by_row):
    out = []
    for spec in specs["verses"]:
        row = rows[spec["apcd_row"]]
        text = row[apcd.VERSE]
        kb = kb_by_row.get(spec["apcd_row"])

        def entries(items):
            return [{"id": e["id"], "basis": e["basis"],
                     "evidence_span": locate(text, e["evidence"]) if e.get("evidence") else None,
                     "justification_ar": e.get("justification")} for e in items]

        out.append({
            "schema_version": "1.0.0",
            "taxonomy_version": "1.0.0",
            "verse_id": f"pv:verse:{spec['n']:06d}",
            "apcd_row": spec["apcd_row"],
            "text_original": text,
            "text_sha256": text_sha256(text),
            "hemistichs": {"shatr_right": row[apcd.SHATR_RIGHT], "shatr_left": row[apcd.SHATR_LEFT]},
            "text_verification": {"method": "apcd_row_exact", "tool": TOOL, "date": specs["date"]},
            "text_note": spec.get("text_note"),
            "poet": {"name_apcd": row[apcd.POET], "poet_id": kb["poet_id"] if kb else None},
            "era_apcd": row[apcd.ERA],
            "source": {"dataset": "APCD", "diwan_apcd": row[apcd.DIWAN], "meter_apcd": row[apcd.METER],
                       "rhyme_apcd": row[apcd.RHYME]},
            "attribution_status": "source_verified" if kb else "apcd_only",
            "evidence_ids": list(kb["attribution_evidence_ids"]) if kb else [],
            "poem_id": kb["poem_id"] if kb else None,
            "visual_associations": [
                {"target": a["target"], "relation": a["relation"],
                 "evidence_span": locate(text, a["evidence"]) if a.get("evidence") else None,
                 "justification_ar": a.get("justification")} for a in spec["visual"]],
            "emotion_status": "has_emotion",
            "emotions": {"primary": entries([spec["primary"]]), "secondary": entries(spec["secondary"])},
            "semantic_concepts": [],
            "genre": None,
            "meaning_ar": spec["meaning"],
            "dimension_status": {"visual": "complete", "emotion": "complete", "concepts": "not_annotated",
                                 "genre": "not_annotated", "meaning": "complete"},
            "annotation": {"annotator_id": f"ai:{specs['model_id']}", "method": "ai_draft",
                           "model_id": specs["model_id"], "date": specs["date"]},
            "review": {"status": "not_reviewed", "reviewers": [], "decisions": []},
            "annotator_uncertainty": spec["uncertainty"],
        })
    return out


ERA_ORDER = ["قبل الإسلام", "المخضرمين", "الأموي", "العباسي", "الفاطمي", "الأيوبي", "المملوكي", "العثماني",
             "المغرب والأندلس", "الحديث"]


def count_ar(n, one, two, few, many):
    """Arabic counted noun: 1 -> one, 2 -> two, 3..10 -> 'n few' (plural), 11..99 -> 'n many' (singular tamyiz)."""
    if n == 1:
        return one
    if n == 2:
        return two
    return f"{n} {few if 3 <= n <= 10 else many}"


README = """# حزمة مراجعة رناد: إحساس {total} (P0)

هذه الحزمة جاهزة للعمل الآن، ولا تحتاج إلى أي برنامج غير Excel أو Numbers أو Google Sheets.

## ما في الحزمة

| الملف | الاستعمال |
|---|---|
| `Renad_Poetry_Review_40.xlsx` | ملف العمل: التعليمات، وتعريفات الأحاسيس الثمانية، والأبيات الأربعون مع المقترحات وقوائم الاختيار |
| `annotation_guide_ar.md` | دليل المراجعة؛ اقرئيه أولًا (نحو 10 دقائق) |
| `renad_review_sheet_p0.csv` | نسخة آلية من الورقة للاستعمال البرمجي؛ لا تحتاجين إلى فتحها |
| `README_AR.md` | هذا الملف |

## المطلوب منك

1. اقرئي `annotation_guide_ar.md`.
2. افتحي `Renad_Poetry_Review_40.xlsx`، ثم ورقة «المراجعة».
3. لكل بيت اختاري قرارًا في عمود «القرار»: ACCEPT أو CORRECT أو REJECT أو UNSURE.
4. عند CORRECT اختاري التصحيح من القائمة. عند REJECT أو UNSURE اكتبي ملاحظة قصيرة.
5. احفظي الملف باسم `renad_review_v1.xlsx` وأرسليه إلى عمر.

- الأعمدة الصفراء الأربعة وحدها للتعبئة.
- الوقت المتوقع نحو ساعة ونصف إلى ساعتين [تقدير].

## ما يجب معرفته

- **الأبيات حقيقية:** نُسخ كل بيت آليًا وحرفيًا من صفّه في APCD، والصف مذكور في عمود «صف APCD».
  - لا تعدّلي النص حتى لو بدا فيه خطأ؛ اذكريه في الملاحظة.
  - عدد الأبيات التي فيها ملاحظة على شكل النص في APCD: {notes}، وتظهر في عمود «ملاحظة على نص APCD».
- **المقترحات مسودات آلية:** الإحساس والدليل والمبرر والمعنى والوسوم البصرية كلها مسودة آلية (ai_draft) أعدها النموذج اللغوي {model}، ولم يراجعها إنسان بعد.
  - حكمك هو المرجع، و«غير متأكدة» إجابة مقبولة.
- **مراجعتك للإحساس فقط:** إن رأيتِ خطأ في المعنى أو الوسوم البصرية فاذكريه في الملاحظة.
- **القائمة ثمانية أحاسيس فقط،** والحب والتأمل ليسا منها.

## كيف اختيرت الأبيات

- **الإحساس الأساسي المقترح:** {counts}.
  - الهدف الأولي خمسة أبيات لكل إحساس، دون فرض تصنيف غير صحيح لتحقيق التوازن.
- **الشعراء:** {poets}، كلهم من أصحاب الدواوين المعروفة. عصورهم بحسب تصنيف APCD: {eras}.
- **ما استُبعد:** لم تُختر أبيات من قصائد اشتهر الخلاف في نسبتها، مثل لامية العرب المنسوبة إلى الشنفرى، وما يُنسب إلى مجنون ليلى.
- **النسبة:**
  - {kb} من قصائد نسبتها موثقة بأدلة في قاعدة المعرفة التاريخية للمشروع؛
  - الباقي ({apcd_only}) نسبته كما في APCD دون تحقق مستقل.

## التحقق الذي أُجري

- قُرئ ملفا xlsx وcsv بعد إنشائهما، وقورن نص كل بيت بصفّه في APCD: {verified} من {total} مطابقة حرفيًا.
- كل دليل نصي مقتطع آليًا من نص البيت نفسه، لا منسوخ يدويًا.
- السجلات المقابلة اجتازت validator عقد `poetry_record` في وضع الإنتاج مع التحقق من APCD.
- أعمدة القرار والتصحيح والملاحظة فارغة في الأبيات الأربعين؛ لم يُكتب أي قرار بشري سلفًا.

## للفريق

- **السجلات:** `poetry_corpus/records/p0_ai_drafts_v1.jsonl` (`method=ai_draft`، `review=not_reviewed`).
- **فحص الملف المعاد:**

```bash
python3 -m poetry_corpus.tools.review_sheet check renad_review_v1.xlsx --final
```
"""


def counts_text(records, taxonomy):
    counter = collections.Counter(r["emotions"]["primary"][0]["id"] for r in records)
    return "، ".join(f"{taxonomy.labels[e]['name_ar']} {counter.get(e, 0)}" for e in EMOTION_ORDER)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    parser.add_argument("--kb", default=DEFAULT_KB)
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    with open(SPECS, encoding="utf-8") as fh:
        specs = json.load(fh)
    row_numbers = [s["apcd_row"] for s in specs["verses"]]
    if len(set(row_numbers)) != len(row_numbers):
        raise SystemExit("duplicate APCD rows in the specs")
    rows = apcd.get_rows(row_numbers, args.apcd_zip)
    missing = sorted(set(row_numbers) - set(rows))
    if missing:
        raise SystemExit(f"APCD rows not found: {missing}")
    records = build_records(specs, rows, load_kb(args.kb))

    issues = validate_records("poetry_record", list(enumerate(records, 1)),
                              Context(taxonomy=taxonomy, mode="production", apcd_zip=args.apcd_zip))
    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        raise SystemExit(f"{len(issues)} contract issue(s); nothing written")
    os.makedirs(os.path.dirname(RECORDS), exist_ok=True)
    with open(RECORDS, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)

    os.makedirs(OUT_DIR, exist_ok=True)
    review_rows = build_rows(records, taxonomy)
    xlsx_path = os.path.join(OUT_DIR, FILES[0])
    csv_path = os.path.join(OUT_DIR, FILES[1])
    write_workbook(review_rows, taxonomy, xlsx_path, EMOTION_ORDER)
    write_csv(review_rows, csv_path)
    shutil.copyfile(GUIDE, os.path.join(OUT_DIR, FILES[3]))

    # verification: read both files back and compare every verse with APCD
    truth = {f"pv:verse:{s['n']:06d}": rows[s["apcd_row"]][apcd.VERSE] for s in specs["verses"]}
    report = {"records": len(records), "contract_issues": 0}
    for label, path in (("xlsx", xlsx_path), ("csv", csv_path)):
        back = read_review(path)
        exact = sum(1 for r in back if truth.get(r.get("verse_id")) == r.get("text_original"))
        filled = sum(1 for r in back for f in REVIEWER_FIELDS if str(r.get(f, "") or "").strip())
        report[label] = {"rows": len(back), "text_matches_apcd": exact, "reviewer_cells_filled": filled}
        if len(back) != len(records) or exact != len(records) or filled:
            raise SystemExit(f"verification failed for {label}: {report[label]}")
    with open(csv_path, encoding="utf-8-sig", newline="") as fh:
        header = fh.readline().strip().split(",")
    report["csv_header_matches_contract"] = header == CSV_COLUMNS
    counter = collections.Counter(r["emotions"]["primary"][0]["id"] for r in records)
    report["primary_counts"] = {e: counter.get(e, 0) for e in EMOTION_ORDER}
    report["attribution"] = dict(collections.Counter(r["attribution_status"] for r in records))
    report["poets"] = len({r["poet"]["name_apcd"] for r in records})
    report["text_notes"] = sum(1 for r in records if r.get("text_note"))

    eras = sorted({r["era_apcd"] for r in records},
                  key=lambda e: ERA_ORDER.index(e) if e in ERA_ORDER else len(ERA_ORDER))
    verses = ("بيت واحد", "بيتان", "أبيات", "بيتًا")
    readme = README.format(
        total=count_ar(len(records), *verses), notes=report["text_notes"], model=specs["model_id"],
        counts=counts_text(records, taxonomy), eras="، ".join(eras),
        poets=count_ar(report["poets"], "شاعر واحد", "شاعران", "شعراء", "شاعرًا"),
        kb=count_ar(report["attribution"].get("source_verified", 0), *verses),
        apcd_only=report["attribution"].get("apcd_only", 0), verified=report["xlsx"]["text_matches_apcd"])
    with open(os.path.join(OUT_DIR, FILES[2]), "w", encoding="utf-8") as fh:
        fh.write(readme)

    zip_path = os.path.join(OUT_DIR, ZIP_NAME)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            info = zipfile.ZipInfo(name, (2026, 11, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(OUT_DIR, name), "rb") as fh:
                archive.writestr(info, fh.read())
    with zipfile.ZipFile(zip_path) as archive:
        report["zip_members"] = archive.namelist()
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
