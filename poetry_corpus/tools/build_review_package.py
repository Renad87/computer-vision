"""Review packages for P1+ batches: one full workbook and one compact priority workbook.

    python3 -m poetry_corpus.tools.build_review_package build [--batch p1_b01 ...] [--name p1_b01]
    python3 -m poetry_corpus.tools.build_review_package check <returned.xlsx|.csv> [--final] [--expect full|priority]

Method: Renad's P0 workbook (tools/review_sheet.py and guidelines/annotation_guide_ar.md) unchanged, plus one
column, «قرار الوسم البصري», because production retrieval ranks tier 1 by a reviewed scene relation
(docs/SPEC.md). Packages go to poetry_corpus/review_packages/<name>/; handoff/renad_p0/ is never touched.

Priority: a greedy cover of the 25 pilot cells by distinct poems (coverage.poem_key). Level A gives every
coverable cell one verse, level B a second poem and level C a third; a verse that covers two cells counts for
both. Ties prefer lower annotator uncertainty, then the lower verse id. The compact workbook holds A and B.
With --prior (an earlier package), the poems that package already schedules (all levels) are counted first,
so the new package only ranks what the earlier one cannot provide, and its compact workbook holds A, B and C
(the verses needed to reach three reviewed poems per cell).

Nothing here records a review: every reviewer cell is empty and the records keep review.status = not_reviewed.
"""
import argparse
import collections
import json
import os
import shutil
import sys
import zipfile

from contracts import apcd
from contracts.taxonomy import load_taxonomy

from . import coverage
from .build_batch import records_path, verse_number
from .build_p0_drafts import EMOTION_ORDER
from .review_sheet import (CSV_COLUMNS, REVIEWER_FIELDS, build_rows, check_review, read_review, write_csv,
                           write_workbook)

ROOT = coverage.ROOT
PACKAGES_DIR = os.path.join(ROOT, "poetry_corpus", "review_packages")
GUIDE = os.path.join(ROOT, "poetry_corpus", "guidelines", "annotation_guide_ar.md")
LEVELS = ("A", "B", "C")
COMPACT_LEVELS = ("A", "B")
UNCERTAINTY_RANK = {"low": 0, "medium": 1, "high": 2}
CSV_EXTRA = ["priority", "visual_decision"]


def all_cells(taxonomy):
    return [(g, e) for g in taxonomy.ids("scene_group") for e in taxonomy.ids("lit_emotion")]


def pilot_covers(record, taxonomy, cells=None):
    members = coverage.cell_members([record], taxonomy, "development")
    return [c for c in (cells or coverage.pilot_cells(taxonomy)) if members.get(c, {}).get("tier1")]


def priority_levels(records, taxonomy, seed_records=(), cells=None):
    """{verse_id: level} for the greedy cover, plus {cell: [poem keys]} selected per cell.
    seed_records are already scheduled elsewhere: their poems count before any new verse is ranked.
    cells defaults to the 25 pilot cells; pass all_cells(taxonomy) for every scene-emotion pair."""
    cells = cells or coverage.pilot_cells(taxonomy)
    covers = {r["verse_id"]: pilot_covers(r, taxonomy, cells) for r in records}
    poems = {c: [] for c in cells}
    for r in seed_records:
        key = coverage.poem_key(r)
        for c in pilot_covers(r, taxonomy, cells):
            if key not in poems[c]:
                poems[c].append(key)
    assigned = {}
    for depth, level in enumerate(LEVELS, 1):
        while True:
            best, best_key, best_gain = None, None, []
            for r in records:
                if r["verse_id"] in assigned:
                    continue
                key = coverage.poem_key(r)
                gain = [c for c in covers[r["verse_id"]] if len(poems[c]) < depth and key not in poems[c]]
                if not gain:
                    continue
                rank = (len(gain), -UNCERTAINTY_RANK[r["annotator_uncertainty"]], -verse_number(r["verse_id"]))
                if best is None or rank > best[0]:
                    best, best_key, best_gain = (rank, r), key, gain
            if best is None:
                break
            assigned[best[1]["verse_id"]] = level
            for c in best_gain:
                poems[c].append(best_key)
    return assigned, poems


README = """# حزمة مراجعة: {name}

حزمة منفصلة عن حزمة رناد الأولى (`handoff/renad_p0/`)، وبالطريقة نفسها: مراجعة الإحساس في أبيات حقيقية منقولة حرفيًا من APCD، مع عمود واحد إضافي للوسوم البصرية.

## الملفات

| الملف | المحتوى |
|---|---|
| `{priority_xlsx}` | **ابدئي به.** {priority_text} |
| `{full_xlsx}` | الأبيات كلها ({full_n} بيتًا)، وفيها عمود «الأولوية» يبين ما سبقت مراجعته في الملف الأول |
| `annotation_guide_ar.md` | دليل المراجعة نفسه المستعمل في حزمة P0 |
| `{priority_csv}`، `{full_csv}` | نسخ آلية للاستعمال البرمجي |
| `manifest.json` | المعرّفات في كل ملف، ومستويات الأولوية، ونتيجة التحقق |

## المطلوب

1. اقرئي `annotation_guide_ar.md` (القواعد نفسها: ACCEPT أو CORRECT أو REJECT أو UNSURE للإحساس).
2. **العمود الجديد «قرار الوسم البصري»:** احكمي على الوسوم البصرية المقترحة كلها (مثل «البحر والساحل — حرفية»):
   - ACCEPT: الوسوم صحيحة؛
   - REJECT: وسم واحد على الأقل غير صحيح، واذكريه في الملاحظة؛
   - UNSURE: لا تستطيعين الحكم، مع ملاحظة.
3. أعيدي الملف الأول باسم `{priority_return}`، ثم الثاني باسم `{full_return}` لما بقي فيه فقط. لا تعيدي مراجعة أبيات الملف الأول.

## ما يجب معرفته

- **الأبيات حقيقية:** كل بيت منسوخ آليًا وحرفيًا من صفه في APCD. لا تعدّلي النص؛ اذكري أي خطأ ظاهر في الملاحظة.
- **المقترحات مسودات آلية** (`ai_draft`) من {model} لم يراجعها إنسان: الإحساس والدليل والمبرر والمعنى والوسوم.
- **النسبة:** {attribution}. `source_verified` لا يكون إلا بدليل من قاعدة المعرفة التاريخية.
- **لماذا عمود الوسوم:** في وضع الإنتاج لا يُقترح البيت لصورة إلا بعلاقة بصرية مراجَعة مع المشهد. دون حكم على الوسوم يبقى البيت صالحًا للإحساس وحده.
- **لا تُسجَّل موافقة بشرية آليًا:** تبقى السجلات `not_reviewed` حتى يعود الملف بقراراتك ويُدمج.

## التحقق الذي أُجري

- قُرئت الملفات بعد إنشائها: نص كل بيت يطابق سجله وصفه في APCD ({verified} من {total_rows} صفًا)، وخلايا المراجعة كلها فارغة.
- فحص الملف المعاد:

```bash
python3 -m poetry_corpus.tools.build_review_package check {priority_return} --expect priority --final
```
"""


def load_manifest(name):
    with open(os.path.join(PACKAGES_DIR, name, "manifest.json"), encoding="utf-8") as fh:
        return json.load(fh)


def build(batches, name, apcd_zip=None, prior=(), every_cell=False, compact_override=None):
    taxonomy = load_taxonomy()
    records = [r for b in batches for _, r in coverage.load_records([records_path(b)])]
    if not records:
        raise SystemExit("no records")
    out_dir = os.path.join(PACKAGES_DIR, name)
    os.makedirs(out_dir, exist_ok=True)
    seed = []
    for prior_name in prior:
        m = load_manifest(prior_name)
        scheduled = set(m["priority_levels"])
        seed += [r for b in m["batches"] for _, r in coverage.load_records([records_path(b)])
                 if r["verse_id"] in scheduled]
    compact_levels = tuple(compact_override) if compact_override else (("A", "B", "C") if prior else COMPACT_LEVELS)
    cells = all_cells(taxonomy) if every_cell else None
    assigned, poems = priority_levels(records, taxonomy, seed, cells)
    full_rows = build_rows(records, taxonomy)
    for row in full_rows:
        level = assigned.get(row["verse_id"][0], "")
        row["priority"] = (level, level or "—")
    order = {lvl: i for i, lvl in enumerate(LEVELS)}
    compact = sorted((r for r in records if assigned.get(r["verse_id"]) in compact_levels),
                     key=lambda r: (order[assigned[r["verse_id"]]], verse_number(r["verse_id"])))
    compact_rows = build_rows(compact, taxonomy)
    for row in compact_rows:
        level = assigned[row["verse_id"][0]]
        row["priority"] = (level, level)

    tag = name.upper().replace("_", "-")
    files = {
        "full_xlsx": f"Poetry_Review_{tag}_{len(records)}.xlsx",
        "full_csv": f"review_sheet_{name}_full.csv",
        "priority_xlsx": f"Poetry_Review_{tag}_Priority_{len(compact)}.xlsx",
        "priority_csv": f"review_sheet_{name}_priority.csv",
        "full_return": f"review_{name}_full_v1.xlsx",
        "priority_return": f"review_{name}_priority_v1.xlsx",
    }
    columns = CSV_COLUMNS + CSV_EXTRA
    write_workbook(full_rows, taxonomy, os.path.join(out_dir, files["full_xlsx"]), EMOTION_ORDER,
                   title=f"مراجعة إحساس الأبيات ووسومها البصرية — {tag} ({len(records)} بيتًا)",
                   book_title=f"مراجعة أبيات {tag}", return_name=files["full_return"], visual=True, priority=True)
    write_csv(full_rows, os.path.join(out_dir, files["full_csv"]), columns)
    write_workbook(compact_rows, taxonomy, os.path.join(out_dir, files["priority_xlsx"]), EMOTION_ORDER,
                   title=f"مراجعة ذات أولوية — {tag} ({len(compact)} بيتًا تغطي الخلايا التجريبية)",
                   book_title=f"مراجعة أولوية {tag}", return_name=files["priority_return"], visual=True,
                   priority=True)
    write_csv(compact_rows, os.path.join(out_dir, files["priority_csv"]), columns)
    shutil.copyfile(GUIDE, os.path.join(out_dir, "annotation_guide_ar.md"))

    # verification: read every file back and compare with the records and with APCD
    truth = {r["verse_id"]: r["text_original"] for r in records}
    rows_apcd = apcd.get_rows([r["apcd_row"] for r in records], apcd_zip) if apcd.available(apcd_zip) else {}
    apcd_ok = all(rows_apcd[r["apcd_row"]][apcd.VERSE] == r["text_original"] for r in records) if rows_apcd else None
    verification = {}
    for key, expected in (("full_xlsx", records), ("full_csv", records), ("priority_xlsx", compact),
                          ("priority_csv", compact)):
        back = read_review(os.path.join(out_dir, files[key]))
        exact = sum(1 for r in back if truth.get(r.get("verse_id")) == r.get("text_original"))
        filled = sum(1 for r in back for f in REVIEWER_FIELDS + ("visual_decision",) if str(r.get(f, "") or "").strip())
        ids_ok = [r.get("verse_id") for r in back] == [r["verse_id"] for r in sorted(
            expected, key=lambda x: verse_number(x["verse_id"]))] if key.startswith("full") else \
            [r.get("verse_id") for r in back] == [r["verse_id"] for r in expected]
        verification[key] = {"rows": len(back), "text_matches_records": exact, "reviewer_cells_filled": filled,
                             "ids_in_order": ids_ok}
        if len(back) != len(expected) or exact != len(expected) or filled or not ids_ok:
            raise SystemExit(f"verification failed for {key}: {verification[key]}")
    verification["text_matches_apcd"] = apcd_ok

    level_counts = collections.Counter(assigned.values())
    covered = {f"{g}|{e}": len(keys) for (g, e), keys in poems.items()}
    manifest = {
        "package": name,
        "batches": list(batches),
        "files": files,
        "full_verse_ids": [r["verse_id"] for r in records],
        "priority_verse_ids": [r["verse_id"] for r in compact],
        "priority_levels": {vid: assigned[vid] for vid in sorted(assigned, key=verse_number)},
        "level_counts": {lvl: level_counts.get(lvl, 0) for lvl in LEVELS},
        "pilot_poems_if_all_levels_accepted": covered,
        "prior_packages": list(prior),
        "compact_levels": list(compact_levels),
        "cells": "all" if every_cell else "pilot",
        "review_columns": "emotion (P0 method) + visual_decision",
        "verification": verification,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    attribution = collections.Counter(r["attribution_status"] for r in records)
    with open(os.path.join(out_dir, "README_AR.md"), "w", encoding="utf-8") as fh:
        fh.write(README.format(
            name=tag, model=records[0]["annotation"]["model_id"], full_n=len(records),
            priority_text=priority_text(len(compact), level_counts, prior),
            attribution="، ".join(f"`{k}` {v}" for k, v in sorted(attribution.items())),
            verified=verification["full_xlsx"]["text_matches_records"], total_rows=len(records), **files))
    members = [files["priority_xlsx"], files["full_xlsx"], "README_AR.md", "annotation_guide_ar.md",
               files["priority_csv"], files["full_csv"], "manifest.json"]
    zip_path = os.path.join(out_dir, f"Poetry_Review_{tag}_Package.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            info = zipfile.ZipInfo(member, (2026, 11, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            with open(os.path.join(out_dir, member), "rb") as fh:
                archive.writestr(info, fh.read())
    return manifest


def priority_text(n, counts, prior):
    if prior and counts.get("A", 0) and not counts.get("B", 0) and not counts.get("C", 0):
        return (f"{n} بيتًا: بيت واحد لكل خلية (مشهد × إحساس) لا تغطيها الحزم السابقة ({'، '.join(prior)}). "
                "راجعي الحزم السابقة أولًا")
    if prior:
        return (f"{n} بيتًا تكمل ما في الحزمة السابقة ({'، '.join(prior)}) حتى ثلاث قصائد مراجَعة لكل خلية "
                f"تجريبية حيث أمكن: A {counts.get('A', 0)}، B {counts.get('B', 0)}، C {counts.get('C', 0)}. "
                "راجعي الحزمة السابقة أولًا")
    return (f"{n} بيتًا مرتبة بالأولوية: المستوى A يعطي كل خلية تجريبية بيتًا واحدًا ({counts.get('A', 0)} بيتًا)، "
            f"والمستوى B قصيدة ثانية ({counts.get('B', 0)} بيتًا)")


def check(path, final=False, expect=None, name="p1_b01"):
    with open(os.path.join(PACKAGES_DIR, name, "manifest.json"), encoding="utf-8") as fh:
        manifest = json.load(fh)
    records = [r for b in manifest["batches"] for _, r in coverage.load_records([records_path(b)])]
    rows = read_review(path)
    if expect:
        wanted = set(manifest[f"{expect}_verse_ids"])
    else:
        wanted = {str(r.get("verse_id", "")).strip() for r in rows}
    expected = [r for r in records if r["verse_id"] in wanted]
    return check_review(rows, expected, final=final, visual=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--batch", action="append", default=None)
    b.add_argument("--name", default=None)
    b.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    b.add_argument("--prior", action="append", default=[], help="earlier package whose schedule counts first")
    b.add_argument("--all-cells", action="store_true", help="rank over all 72 scene-emotion cells, not the pilot")
    b.add_argument("--compact-levels", default=None, help="levels in the priority workbook, e.g. A or ABC")
    c = sub.add_parser("check")
    c.add_argument("path")
    c.add_argument("--final", action="store_true")
    c.add_argument("--expect", choices=("full", "priority"))
    c.add_argument("--name", default="p1_b01")
    args = parser.parse_args(argv)
    if args.command == "build":
        batches = args.batch or ["p1_b01"]
        manifest = build(batches, args.name or "_".join(batches), args.apcd_zip, args.prior, args.all_cells,
                         list(args.compact_levels) if args.compact_levels else None)
        print(json.dumps({k: manifest[k] for k in ("package", "level_counts", "verification")}, ensure_ascii=False))
        return 0
    issues, normalized = check(args.path, args.final, args.expect, args.name)
    for verse_id, field, message in issues:
        print(f"{verse_id}\t{field}\t{message}")
    print(json.dumps({"rows": len(normalized), "decided": sum(1 for r in normalized if r["decision"]),
                      "issues": len(issues)}), file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
