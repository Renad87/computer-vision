"""Consolidated corpus exports and reports (Python standard library only).

    python3 -m poetry_corpus.tools.export_corpus [--out poetry_corpus/exports] [--no-apcd]

Writes, from every record file:
- corpus_all_v1.jsonl / .csv / .xlsx: all records (the xlsx adds the coverage matrix and a provenance sheet);
- production_eligible_v1.jsonl: only records that contracts.validate.display_allowed admits in production mode,
  i.e. genuinely human-reviewed ones (empty until reviews are merged);
- coverage_matrix_v1.{json,md}: 9 scene groups x 8 literary emotions (distinct poems at tier 1, records, secondary);
- provenance_report_v1.{json,md}, annotation_quality_report_v1.{json,md}, duplicate_report_v1.{json,md}.
The whole corpus is validated as one collection (development mode, against APCD unless --no-apcd), so ids and
APCD rows are checked across files, not only within a batch.
"""
import argparse
import collections
import csv
import json
import os
import sys

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, validate_records

from . import coverage
from .build_batch import folded, shared_hemistichs, verse_number
from .find_candidates import MODERN_ERA, MODERN_POETS
from .xlsx import Workbook

ROOT = coverage.ROOT
OUT = os.path.join(ROOT, "poetry_corpus", "exports")
EMOTIONS = ["lit_emotion.sadness", "lit_emotion.longing", "lit_emotion.loneliness", "lit_emotion.awe",
            "lit_emotion.serenity", "lit_emotion.joy", "lit_emotion.pride", "lit_emotion.fear"]
GROUPS = ["scene_group.desert", "scene_group.sea", "scene_group.mountains", "scene_group.water",
          "scene_group.greenery", "scene_group.sky_night", "scene_group.heritage", "scene_group.city",
          "scene_group.worship"]
CSV_FIELDS = ["verse_id", "batch", "apcd_row", "text_original", "poet", "era", "diwan", "meter", "rhyme",
              "attribution_status", "evidence_ids", "poem_id", "copyright_status", "primary_emotions",
              "secondary_emotions", "emotion_evidence", "emotion_justifications", "scene_groups", "visual_tags",
              "visual_relations", "visual_evidence", "meaning_ar", "text_note", "annotation_method", "model_id",
              "annotation_date", "annotator_uncertainty", "review_status", "reviewers", "production_eligible",
              "development_eligible", "text_sha256"]


def copyright_status(record):
    if record["era_apcd"] != MODERN_ERA:
        return "public_domain_classical"
    return MODERN_POETS.get(record["poet"]["name_apcd"], (None, "not_listed"))[1]


def flatten(record, batch, taxonomy):
    emo = record["emotions"]
    visual = record["visual_associations"]
    joiner = " | ".join
    return {
        "verse_id": record["verse_id"], "batch": batch, "apcd_row": record["apcd_row"],
        "text_original": record["text_original"], "poet": record["poet"]["name_apcd"], "era": record["era_apcd"],
        "diwan": record["source"]["diwan_apcd"], "meter": record["source"]["meter_apcd"],
        "rhyme": record["source"]["rhyme_apcd"], "attribution_status": record["attribution_status"],
        "evidence_ids": joiner(record["evidence_ids"]), "poem_id": record.get("poem_id") or "",
        "copyright_status": copyright_status(record),
        "primary_emotions": joiner(e["id"] for e in emo["primary"]),
        "secondary_emotions": joiner(e["id"] for e in emo["secondary"]),
        "emotion_evidence": joiner((e.get("evidence_span") or {}).get("text", "") for e in emo["primary"] + emo["secondary"]),
        "emotion_justifications": joiner(e.get("justification_ar") or "" for e in emo["primary"] + emo["secondary"]),
        "scene_groups": joiner(f"{a['target']}:{a['relation']}" for a in visual
                               if taxonomy.layer(a["target"]) == "scene_group"),
        "visual_tags": joiner(f"{a['target']}:{a['relation']}" for a in visual if taxonomy.layer(a["target"]) == "tag"),
        "visual_relations": joiner(a["relation"] for a in visual),
        "visual_evidence": joiner((a.get("evidence_span") or {}).get("text", "") or (a.get("justification_ar") or "")
                                  for a in visual),
        "meaning_ar": record.get("meaning_ar") or "", "text_note": record.get("text_note") or "",
        "annotation_method": record["annotation"]["method"], "model_id": record["annotation"].get("model_id") or "",
        "annotation_date": record["annotation"]["date"], "annotator_uncertainty": record["annotator_uncertainty"],
        "review_status": record["review"]["status"], "reviewers": joiner(record["review"]["reviewers"]),
        "production_eligible": display_allowed(record, "production"),
        "development_eligible": display_allowed(record, "development"), "text_sha256": record["text_sha256"],
    }


def load_corpus():
    out = []
    for path in coverage.record_files():
        batch = os.path.basename(path).replace("_ai_drafts_v1.jsonl", "")
        out.extend((batch, r) for _, r in coverage.load_records([path]))
    return sorted(out, key=lambda br: verse_number(br[1]["verse_id"]))


def matrix(records, taxonomy):
    cells = coverage.cell_members(records, taxonomy, "development")
    table = {}
    for g in GROUPS:
        for e in EMOTIONS:
            block = cells.get((g, e)) or {"tier1": [], "secondary": [], "symbolic": []}
            table[f"{g}|{e}"] = {"tier1_poems": len({coverage.poem_key(r) for r in block["tier1"]}),
                                 "tier1_records": len(block["tier1"]), "secondary_records": len(block["secondary"]),
                                 "symbolic_records": len(block["symbolic"])}
    return table


def md_matrix(table, taxonomy, field):
    name = lambda i: taxonomy.labels[i]["name_ar"]
    lines = ["| المجموعة | " + " | ".join(name(e) for e in EMOTIONS) + " | المجموع |",
             "|---" * (len(EMOTIONS) + 2) + "|"]
    for g in GROUPS:
        values = [table[f"{g}|{e}"][field] for e in EMOTIONS]
        lines.append(f"| {name(g)} | " + " | ".join(str(v) for v in values) + f" | {sum(values)} |")
    return "\n".join(lines)


def write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def export(out_dir=OUT, check_apcd=True):
    os.makedirs(out_dir, exist_ok=True)
    taxonomy = load_taxonomy()
    corpus = load_corpus()
    records = [r for _, r in corpus]
    batches = collections.OrderedDict()
    for batch, r in corpus:
        batches.setdefault(batch, []).append(r)

    # corpus-level validation: one collection, so ids and rows are unique across files
    ctx = Context(taxonomy=taxonomy, mode="development", apcd_zip=apcd.DEFAULT_ZIP if check_apcd else None)
    issues = validate_records("poetry_record", list(enumerate(records, 1)), ctx)

    with open(os.path.join(out_dir, "corpus_all_v1.jsonl"), "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)
    production = [r for r in records if display_allowed(r, "production")]
    with open(os.path.join(out_dir, "production_eligible_v1.jsonl"), "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in production)
    rows = [flatten(r, b, taxonomy) for b, r in corpus]
    with open(os.path.join(out_dir, "corpus_all_v1.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    table = matrix(records, taxonomy)
    totals = {"records": len(records), "groups": len(GROUPS), "emotions": len(EMOTIONS),
              "cells_with_tier1": sum(1 for v in table.values() if v["tier1_poems"]),
              "cells_ge_3": sum(1 for v in table.values() if v["tier1_poems"] >= 3),
              "cells_ge_6": sum(1 for v in table.values() if v["tier1_poems"] >= 6),
              "cells_ge_8": sum(1 for v in table.values() if v["tier1_poems"] >= 8)}
    with open(os.path.join(out_dir, "coverage_matrix_v1.json"), "w", encoding="utf-8") as fh:
        json.dump({"totals": totals, "cells": table}, fh, ensure_ascii=False, indent=1)
    write(os.path.join(out_dir, "coverage_matrix_v1.md"),
          "# مصفوفة التغطية: المشهد × الإحساس الأدبي\n\n"
          f"المدونة: {len(records)} بيتًا. العدّ من السجلات: بيت يحمل الإحساس أساسيًا وعلاقة `literal` أو "
          "`scene_association` بالمجموعة، ويُعدّ بالقصائد المختلفة (`guidelines/poem_identity.md`). كلها مسودات "
          "آلية؛ في وضع الإنتاج العدد صفر حتى تُدمج المراجعات.\n\n"
          f"## قصائد مختلفة\n\n{md_matrix(table, taxonomy, 'tier1_poems')}\n\n"
          f"## أبيات (يشمل أكثر من بيت للقصيدة)\n\n{md_matrix(table, taxonomy, 'tier1_records')}\n\n"
          f"- خلايا فيها بيت واحد على الأقل: {totals['cells_with_tier1']} من 72؛ ثلاث قصائد فأكثر: "
          f"{totals['cells_ge_3']}؛ ست فأكثر: {totals['cells_ge_6']}؛ ثمانٍ فأكثر: {totals['cells_ge_8']}.\n")

    # provenance
    attribution = collections.Counter(r["attribution_status"] for r in records)
    copyright = collections.Counter(copyright_status(r) for r in records)
    verified = [{"verse_id": r["verse_id"], "poet": r["poet"]["name_apcd"], "poem_id": r["poem_id"],
                 "evidence_ids": r["evidence_ids"]} for r in records if r["attribution_status"] == "source_verified"]
    eras = collections.Counter(r["era_apcd"] for r in records)
    poets = collections.Counter(r["poet"]["name_apcd"] for r in records)
    models = collections.Counter(r["annotation"].get("model_id") for r in records)
    flagged = [r["verse_id"] for r in records if copyright_status(r) in ("us_risk", "unverified", "not_listed")]
    provenance = {"records": len(records), "text_verification": dict(collections.Counter(
        r["text_verification"]["method"] for r in records)), "attribution": dict(attribution),
        "source_verified": verified, "copyright_status": dict(copyright), "copyright_flagged_for_owner": flagged,
        "eras": dict(eras.most_common()), "poets": len(poets), "top_poets": poets.most_common(15),
        "annotation_models": dict(models), "per_batch": {b: dict(collections.Counter(r["attribution_status"] for r in rs))
                                                          for b, rs in batches.items()}}
    with open(os.path.join(out_dir, "provenance_report_v1.json"), "w", encoding="utf-8") as fh:
        json.dump(provenance, fh, ensure_ascii=False, indent=1)
    write(os.path.join(out_dir, "provenance_report_v1.md"),
          "# تقرير المصدر والنسبة\n\n"
          f"- **النص:** {provenance['text_verification']} (كل بيت منسوخ حرفيًا من صفه في APCD).\n"
          f"- **النسبة:** {dict(attribution)}. `source_verified` لا يكون إلا بدليل من قاعدة المعرفة التاريخية "
          f"({len(verified)} بيتًا)؛ الباقي نسبته كما في APCD دون تحقق مستقل.\n"
          f"- **حالة الملكية:** {dict(copyright)} (`guidelines/copyright_status.md`). سجلات تحتاج قرار المالك قبل "
          f"أي نشر علني: {len(flagged)}.\n"
          f"- **العصور:** {dict(eras.most_common())}.\n- **الشعراء:** {len(poets)}.\n"
          f"- **نماذج التعليق:** {dict(models)}.\n\n## الأبيات الموثّقة المصدر\n\n"
          + "\n".join(f"- {v['verse_id']} {v['poet']}: `{v['poem_id']}` ({'، '.join(v['evidence_ids'])})" for v in verified)
          + "\n")

    # annotation quality
    def stats(rs):
        meaning_words = [len((r.get("meaning_ar") or "").split()) for r in rs]
        return {
            "records": len(rs),
            "uncertainty": dict(collections.Counter(r["annotator_uncertainty"] for r in rs)),
            "primary_emotions": dict(collections.Counter(e["id"] for r in rs for e in r["emotions"]["primary"])),
            "with_secondary": sum(1 for r in rs if r["emotions"]["secondary"]),
            "basis": dict(collections.Counter(e["basis"] for r in rs for e in r["emotions"]["primary"] + r["emotions"]["secondary"])),
            "relations": dict(collections.Counter(a["relation"] for r in rs for a in r["visual_associations"])),
            "scene_groups": dict(collections.Counter(a["target"] for r in rs for a in r["visual_associations"]
                                                     if taxonomy.layer(a["target"]) == "scene_group")),
            "tags": dict(collections.Counter(a["target"] for r in rs for a in r["visual_associations"]
                                             if taxonomy.layer(a["target"]) == "tag")),
            "evidence_spans": sum(1 for r in rs for x in r["emotions"]["primary"] + r["emotions"]["secondary"]
                                  + r["visual_associations"] if x.get("evidence_span")),
            "text_notes": sum(1 for r in rs if r.get("text_note")),
            "meaning_words_avg": round(sum(meaning_words) / len(meaning_words), 1) if meaning_words else 0,
            "without_tier1_scene": sum(1 for r in rs if not any(
                taxonomy.layer(a["target"]) == "scene_group" and a["relation"] in coverage.TIER1_RELATIONS
                for a in r["visual_associations"])),
            "models": dict(collections.Counter(r["annotation"].get("model_id") for r in rs)),
        }
    quality = {"corpus": stats(records), "per_batch": {b: stats(rs) for b, rs in batches.items()},
               "validator": {"mode": "development", "apcd_verified": check_apcd, "issues": [str(i) for i in issues]}}
    with open(os.path.join(out_dir, "annotation_quality_report_v1.json"), "w", encoding="utf-8") as fh:
        json.dump(quality, fh, ensure_ascii=False, indent=1)
    c = quality["corpus"]
    write(os.path.join(out_dir, "annotation_quality_report_v1.md"),
          "# تقرير جودة التعليق\n\n"
          f"- **التحقق على مستوى المدونة:** الـvalidator في وضع `development`"
          f"{' مع مطابقة APCD' if check_apcd else ''} على {len(records)} سجلًا مجموعةً واحدة: {len(issues)} مشكلات.\n"
          f"- **الطريقة:** {dict(collections.Counter(r['annotation']['method'] for r in records))}؛ "
          f"المراجعة: {dict(collections.Counter(r['review']['status'] for r in records))}.\n"
          f"- **عدم اليقين:** {c['uncertainty']}. **الأساس:** {c['basis']}.\n"
          f"- **العلاقات البصرية:** {c['relations']}.\n- **الوسوم:** {c['tags']}.\n"
          f"- **أدلة نصية مقتطعة من النص:** {c['evidence_spans']}. **ملاحظات نص APCD:** {c['text_notes']}. "
          f"**متوسط كلمات المعنى:** {c['meaning_words_avg']}.\n"
          f"- **سجلات بلا علاقة مشهد من المستوى الأول:** {c['without_tier1_scene']} (من P0؛ الدفعات اللاحقة تشترطها).\n\n"
          "## حسب الدفعة\n\n| الدفعة | أبيات | عدم يقين منخفض/متوسط/عال | ثانوي | ملاحظات نص | النموذج |\n|---|---|---|---|---|---|\n"
          + "\n".join(f"| {b} | {s['records']} | {s['uncertainty'].get('low', 0)}/{s['uncertainty'].get('medium', 0)}/"
                      f"{s['uncertainty'].get('high', 0)} | {s['with_secondary']} | {s['text_notes']} | "
                      f"{', '.join(m for m in s['models'] if m)} |" for b, s in quality["per_batch"].items()) + "\n")

    # duplicates
    pairs = shared_hemistichs(records, records)
    per_poem = collections.Counter(coverage.poem_key(r) for r in records)
    duplicates = {
        "records": len(records),
        "verse_ids_unique": len({r["verse_id"] for r in records}) == len(records),
        "apcd_rows_unique": len({r["apcd_row"] for r in records}) == len(records),
        "text_sha256_unique": len({r["text_sha256"] for r in records}) == len(records),
        "folded_text_unique": len({folded(r["text_original"]) for r in records}) == len(records),
        "shared_hemistich_pairs": sorted({tuple(sorted(p)) for p in pairs}),
        "poems": len(per_poem), "max_verses_per_poem": max(per_poem.values()) if per_poem else 0,
        "poems_with_3_or_more_verses": [[list(k), n] for k, n in per_poem.most_common() if n >= 3],
        "max_verses_per_poet": poets.most_common(1)[0] if poets else None,
    }
    with open(os.path.join(out_dir, "duplicate_report_v1.json"), "w", encoding="utf-8") as fh:
        json.dump(duplicates, fh, ensure_ascii=False, indent=1)
    yes = lambda x: "نعم" if x else "لا"
    write(os.path.join(out_dir, "duplicate_report_v1.md"),
          "# تقرير التكرار\n\n"
          f"- معرّفات فريدة: {yes(duplicates['verse_ids_unique'])}؛ صفوف APCD فريدة: {yes(duplicates['apcd_rows_unique'])}؛ "
          f"نصوص فريدة: {yes(duplicates['text_sha256_unique'])}؛ فريدة بعد حذف التشكيل: {yes(duplicates['folded_text_unique'])}.\n"
          f"- أزواج تشترك في شطر كامل: {len(duplicates['shared_hemistich_pairs'])} "
          f"{duplicates['shared_hemistich_pairs'] or ''}\n"
          f"- قصائد مختلفة (الشاعر، البحر، القافية): {duplicates['poems']}؛ أكثر الأبيات من قصيدة واحدة: "
          f"{duplicates['max_verses_per_poem']}.\n"
          f"- أكثر الشعراء حضورًا: {duplicates['max_verses_per_poet']}.\n")

    # workbook
    book = Workbook(title="مدونة Poetry Vision")
    s = book.add_sheet("المدونة")
    widths = {"text_original": 46, "meaning_ar": 40, "poet": 16, "emotion_justifications": 30, "scene_groups": 30,
              "visual_evidence": 24}
    for col, field in enumerate(CSV_FIELDS, 1):
        s.set(1, col, field, "header")
        s.widths[col] = widths.get(field, 14)
    for i, row in enumerate(rows, 2):
        for col, field in enumerate(CSV_FIELDS, 1):
            value = row[field]
            s.set(i, col, value if not isinstance(value, bool) else ("نعم" if value else "لا"),
                  "verse" if field == "text_original" else ("number" if field == "apcd_row" else "text"))
    s.freeze = (2, 2)
    m = book.add_sheet("التغطية")
    m.set(1, 1, "المجموعة", "header")
    for j, e in enumerate(EMOTIONS, 2):
        m.set(1, j, taxonomy.labels[e]["name_ar"], "header")
        m.widths[j] = 14
    m.widths[1] = 24
    for i, g in enumerate(GROUPS, 2):
        m.set(i, 1, taxonomy.labels[g]["name_ar"], "subtitle")
        for j, e in enumerate(EMOTIONS, 2):
            m.set(i, j, table[f"{g}|{e}"]["tier1_poems"], "number")
    p = book.add_sheet("المصادر")
    for i, (k, v) in enumerate([("الأبيات", len(records)), ("source_verified", attribution.get("source_verified", 0)),
                                ("apcd_only", attribution.get("apcd_only", 0)),
                                ("مراجَعة بشريًا", sum(1 for r in records if r["review"]["status"] != "not_reviewed")),
                                ("صالحة للإنتاج", len(production)), ("الشعراء", len(poets))], 1):
        p.set(i, 1, k, "subtitle")
        p.set(i, 2, v, "number")
    p.widths = {1: 24, 2: 12}
    book.save(os.path.join(out_dir, "corpus_all_v1.xlsx"))
    return {"records": len(records), "issues": len(issues), "production_eligible": len(production),
            "coverage": totals, "duplicates": {k: duplicates[k] for k in ("verse_ids_unique", "apcd_rows_unique",
                                                                         "text_sha256_unique", "folded_text_unique")},
            "shared_hemistich_pairs": len(duplicates["shared_hemistich_pairs"])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", default=OUT)
    parser.add_argument("--no-apcd", action="store_true")
    args = parser.parse_args(argv)
    summary = export(args.out, not args.no_apcd)
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["issues"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
