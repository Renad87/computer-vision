"""Build one batch of AI-draft poetry records from its spec, after P0 (P1, P2, ...).

    python3 -m poetry_corpus.tools.build_batch poetry_corpus/drafts/p1_b01_ai_draft_specs_v1.json
        [--apcd-zip PATH] [--kb PATH] [--check]

1. The spec holds labels, meanings and evidence phrases only, never verse text. Every verse is copied
   verbatim from its APCD row and every evidence span is cut from that text (build_p0_drafts.locate).
2. Attribution is source_verified only when the history knowledge base locates the row in a verified poem
   (build_p0_drafts.load_kb); every other verse stays apcd_only. Annotation is ai_draft with the spec's
   model id; review is not_reviewed with no reviewers. Nothing here marks a verse as reviewed.
3. Refuses to write when an id is reused or does not continue from the highest id of the other record
   files, when an APCD row or verse text is already in the corpus, when the batch fails the validator in
   development mode against APCD, or when any record would be displayable in production.
4. Writes poetry_corpus/records/<batch>_ai_drafts_v1.jsonl and poetry_corpus/reports/<batch>_report.{json,md}
   with per-cell counts for the batch and for the whole corpus (tools/coverage.py), attribution and gaps.

--check rebuilds in memory and exits 1 if the record file differs from a fresh build (nothing is written).
"""
import argparse
import collections
import json
import os
import sys

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, text_sha256, validate_records

from . import coverage
from .build_p0_drafts import DEFAULT_KB, ERA_ORDER, load_kb, locate
from .find_candidates import fold

ROOT = coverage.ROOT
RECORDS_DIR = coverage.RECORDS_DIR
REPORTS_DIR = os.path.join(ROOT, "poetry_corpus", "reports")
TOOL = "poetry_corpus/tools/build_batch.py"


def records_path(batch):
    return os.path.join(RECORDS_DIR, f"{batch}_ai_drafts_v1.jsonl")


def report_paths(batch):
    return (os.path.join(REPORTS_DIR, f"{batch}_report.json"), os.path.join(REPORTS_DIR, f"{batch}_report.md"))


def verse_number(verse_id):
    return int(verse_id.rsplit(":", 1)[1])


def build_records(spec, rows, kb_by_row):
    out = []
    for v in spec["verses"]:
        row = rows[v["apcd_row"]]
        text = row[apcd.VERSE]
        kb = kb_by_row.get(v["apcd_row"])
        primary = v["primary"] if isinstance(v["primary"], list) else [v["primary"]]

        def entries(items):
            return [{"id": e["id"], "basis": e["basis"],
                     "evidence_span": locate(text, e["evidence"]) if e.get("evidence") else None,
                     "justification_ar": e.get("justification")} for e in items]

        out.append({
            "schema_version": "1.0.0",
            "taxonomy_version": "1.0.0",
            "verse_id": f"pv:verse:{v['n']:06d}",
            "apcd_row": v["apcd_row"],
            "text_original": text,
            "text_sha256": text_sha256(text),
            "hemistichs": {"shatr_right": row[apcd.SHATR_RIGHT], "shatr_left": row[apcd.SHATR_LEFT]},
            "text_verification": {"method": "apcd_row_exact", "tool": TOOL, "date": spec["date"]},
            "text_note": v.get("text_note"),
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
                 "justification_ar": a.get("justification")} for a in v["visual"]],
            "emotion_status": "has_emotion",
            "emotions": {"primary": entries(primary), "secondary": entries(v.get("secondary") or [])},
            "semantic_concepts": [],
            "genre": None,
            "meaning_ar": v["meaning"],
            "dimension_status": {"visual": "complete", "emotion": "complete", "concepts": "not_annotated",
                                 "genre": "not_annotated", "meaning": "complete"},
            "annotation": {"annotator_id": f"ai:{spec['model_id']}", "method": "ai_draft",
                           "model_id": spec["model_id"], "date": spec["date"]},
            "review": {"status": "not_reviewed", "reviewers": [], "decisions": []},
            "annotator_uncertainty": v["uncertainty"],
        })
    return out


def other_records(batch):
    """Records of the files that precede this batch (P0, then earlier batches in name order).

    The batch's own file and later batches are excluded, so an earlier batch can be rebuilt and checked
    after later ones exist."""
    own = os.path.basename(records_path(batch))
    paths = [p for p in coverage.record_files() if os.path.basename(p) < own]
    return [r for _, r in coverage.load_records(paths)]


def folded(text):
    """Letters only, diacritics and hamza/alef/ya/ta-marbuta spelling folded: catches the same verse typed
    with different vocalization in another APCD row."""
    return "".join(ch for ch in fold(text) if not ch.isspace())


def corpus_conflicts(records, existing):
    """Problems that make the batch unsafe to add to the corpus (ids, rows, texts, display flag)."""
    problems = []
    used_ids = {r["verse_id"] for r in existing}
    used_rows = {r["apcd_row"] for r in existing}
    used_text = {r["text_sha256"] for r in existing}
    used_folded = {folded(r["text_original"]) for r in existing}
    seen_folded = set()
    expected = max((verse_number(i) for i in used_ids), default=0) + 1
    numbers = [verse_number(r["verse_id"]) for r in records]
    if numbers != list(range(expected, expected + len(records))):
        problems.append(f"verse ids must continue from pv:verse:{expected:06d} without gaps")
    seen_rows, seen_text = set(), set()
    for r in records:
        if r["verse_id"] in used_ids:
            problems.append(f"{r['verse_id']} is already used")
        if r["apcd_row"] in used_rows or r["apcd_row"] in seen_rows:
            problems.append(f"{r['verse_id']}: APCD row {r['apcd_row']} is already in the corpus")
        if r["text_sha256"] in used_text or r["text_sha256"] in seen_text:
            problems.append(f"{r['verse_id']}: the same verse text is already in the corpus")
        elif folded(r["text_original"]) in used_folded or folded(r["text_original"]) in seen_folded:
            problems.append(f"{r['verse_id']}: the same verse (ignoring diacritics) is already in the corpus")
        seen_folded.add(folded(r["text_original"]))
        if display_allowed(r, "production"):
            problems.append(f"{r['verse_id']}: an unreviewed draft must not be displayable in production")
        seen_rows.add(r["apcd_row"])
        seen_text.add(r["text_sha256"])
    return problems


def shared_hemistichs(records, corpus):
    """[(new verse id, other verse id)] where a full hemistich (folded) also occurs in another corpus verse."""
    index = collections.defaultdict(set)
    for r in corpus:
        for part in (r.get("hemistichs") or {}).values():
            if part and folded(part):
                index[folded(part)].add(r["verse_id"])
    pairs = set()
    for r in records:
        for part in (r.get("hemistichs") or {}).values():
            for other in index.get(folded(part or ""), ()):
                if other != r["verse_id"]:
                    pairs.add((r["verse_id"], other))
    return sorted(pairs)


def batch_cells(records, taxonomy):
    """Tier-1 primary records per pilot cell in this batch alone."""
    cells = coverage.cell_members(records, taxonomy, "development")
    return {f"{g}|{e}": len(cells.get((g, e), {}).get("tier1", [])) for g, e in coverage.pilot_cells(taxonomy)}


def status_counts(records):
    attribution = collections.Counter(r["attribution_status"] for r in records)
    return {
        "records": len(records),
        "source_verified": attribution.get("source_verified", 0),
        "apcd_only": attribution.get("apcd_only", 0),
        "disputed": attribution.get("disputed", 0),
        "ai_draft": sum(1 for r in records if r["annotation"]["method"] == "ai_draft"),
        "human_reviewed": sum(1 for r in records if r["review"]["status"] in ("reviewed", "double_reviewed",
                                                                               "adjudicated")),
        "production_eligible": sum(1 for r in records if display_allowed(r, "production")),
        "development_eligible": sum(1 for r in records if display_allowed(r, "development")),
    }


def make_report(spec, records, corpus_records, taxonomy, target):
    summary = coverage.summarize(corpus_records, taxonomy, "development", target)
    eras = collections.Counter(r["era_apcd"] for r in records)
    others = [r for r in corpus_records if r["verse_id"] not in {x["verse_id"] for x in records}]
    log = spec.get("work_log") or {}
    return {
        "batch": spec["batch"],
        "records_file": os.path.relpath(records_path(spec["batch"]), ROOT),
        "verse_ids": [records[0]["verse_id"], records[-1]["verse_id"]] if records else [],
        "records": len(records),
        "validator": {"mode": "development", "apcd_verified": True, "issues": 0},
        "displayable_in_production": sum(1 for r in records if display_allowed(r, "production")),
        "annotation": {"method": "ai_draft", "model_id": spec["model_id"], "review_status": "not_reviewed"},
        "attribution": dict(sorted(collections.Counter(r["attribution_status"] for r in records).items())),
        "poets": len({r["poet"]["name_apcd"] for r in records}),
        "eras": {e: eras[e] for e in sorted(eras, key=lambda e: (ERA_ORDER.index(e) if e in ERA_ORDER
                                                                     else len(ERA_ORDER), e))},
        "text_notes": sum(1 for r in records if r.get("text_note")),
        "uncertainty": dict(sorted(collections.Counter(r["annotator_uncertainty"] for r in records).items())),
        "primary_emotions": dict(sorted(collections.Counter(
            e["id"] for r in records for e in r["emotions"]["primary"]).items())),
        "batch_tier1_records_per_pilot_cell": batch_cells(records, taxonomy),
        "corpus": {k: summary[k] for k in ("records", "displayable_records", "target_tier1_poems_per_cell",
                                           "pilot_cells_at_target", "pilot_cells_empty", "pilot_gap_total")},
        "corpus_tier1_poems_per_pilot_cell": {k: v["tier1_poems"] for k, v in summary["matrix"].items()},
        "corpus_cells_below_3_poems": sorted(k for k, v in summary["matrix"].items() if v["tier1_poems"] < 3),
        "gaps_to_target": summary["gaps"],
        "outside_pilot_tier1_cells": {k: v["tier1_poems"] for k, v in summary["outside_pilot"].items()},
        "status_batch": status_counts(records),
        "status_cumulative": status_counts(corpus_records),
        "duplicate_checks": {
            "apcd_rows_unique_in_corpus": len({r["apcd_row"] for r in corpus_records}) == len(corpus_records),
            "text_sha256_unique_in_corpus": len({r["text_sha256"] for r in corpus_records}) == len(corpus_records),
            "folded_text_unique_in_corpus": len({folded(r["text_original"]) for r in corpus_records})
            == len(corpus_records),
            "shared_hemistichs": [list(p) for p in shared_hemistichs(records, corpus_records)],
            "batch_poems": len({coverage.poem_key(r) for r in records}),
            "batch_poems_already_in_corpus": len({coverage.poem_key(r) for r in records}
                                                 & {coverage.poem_key(r) for r in others}),
        },
        "throughput": {
            "started": log.get("started"), "finished": log.get("finished"), "basis": log.get("basis"),
            "minutes": log.get("minutes"),
            "verses_per_hour": round(len(records) * 60 / log["minutes"], 1) if log.get("minutes") else None,
            "candidates_listed": log.get("candidates_listed"), "read_in_context": log.get("read_in_context"),
        },
    }, summary


REPORT_MD = """# تقرير الدفعة {batch}

- **السجلات:** {records} بيتًا في `{records_file}` ({first} إلى {last}).
- **الحالة:** مسودات آلية `ai_draft` من {model}، و`review.status = not_reviewed` لكل السجلات. لم يراجعها إنسان، ولا يُعرض أي منها في وضع الإنتاج ({displayable} قابلة للعرض في الإنتاج).
- **التحقق:** الـvalidator في وضع `development` مع التحقق من APCD: 0 مشكلات. كل نص منسوخ حرفيًا من صفه في APCD، وكل دليل نصي مقتطع منه آليًا.
- **النسبة:** {attribution}. لا يُعلَّم `source_verified` إلا بدليل من قاعدة المعرفة التاريخية.
- **الشعراء:** {poets}. **ملاحظات النص:** {notes}. **عدم اليقين:** {uncertainty}.

## مراقبة الجودة

| البند | الدفعة | المدونة كلها |
|---|---|---|
| الأبيات | {b_records} | {c_records} |
| موثّقة المصدر (`source_verified`) | {b_sv} | {c_sv} |
| من APCD وحده (`apcd_only`) | {b_ao} | {c_ao} |
| مراجَعة بشريًا | {b_hr} | {c_hr} |
| صالحة للإنتاج | {b_pe} | {c_pe} |
| صالحة لوضع التطوير | {b_de} | {c_de} |

- **التكرار:** صفوف APCD فريدة: {dup_rows}؛ النصوص فريدة: {dup_sha}؛ فريدة بعد حذف التشكيل: {dup_fold}. أبيات تشترك في شطر كامل مع بيت آخر: {shared}. قصائد الدفعة: {batch_poems}، منها {poems_old} لها بيت سابق في المدونة.
- **الإنتاجية:** {throughput}
- **التحقق:** `python3 -m contracts.validate poetry_record {records_file} --mode development --apcd-zip <APCD>`: 0 مشكلات، مع مطابقة النص والشاعر والعصر والديوان والبحر والقافية لصف APCD.

## التغطية

العدّ من السجلات نفسها (`python3 -m poetry_corpus.tools.coverage`): بيت يحمل الإحساس أساسيًا وعلاقة `literal` أو `scene_association` بالمجموعة، وتُعد القصائد المختلفة لأن المحرك لا يعيد أكثر من بيت من القصيدة الواحدة. الهدف المؤقت {target} قصائد لكل خلية؛ المواصفة لا تحدد رقمًا لكل خلية.

### ما أضافته الدفعة (سجلات)

{batch_table}

### المدونة كلها بعد الدفعة (قصائد مختلفة)

{corpus_table}

- الخلايا التي بلغت الهدف: {at_target} من 25. الخلايا دون 3 قصائد: {below3}.
- النقص الكلي حتى الهدف: {gap} بيتًا على الأقل.

## الفجوات المتبقية

{gaps}
"""


def cell_table(values, taxonomy):
    pilot = taxonomy.pilot
    name = lambda i: taxonomy.labels[i]["name_ar"]
    lines = ["| المجموعة | " + " | ".join(name(e) for e in pilot["lit_emotions"]) + " |",
             "|---" * (len(pilot["lit_emotions"]) + 1) + "|"]
    for g in pilot["scene_groups"]:
        lines.append(f"| {name(g)} | " + " | ".join(str(values[f'{g}|{e}']) for e in pilot["lit_emotions"]) + " |")
    return "\n".join(lines)


def throughput_text(t):
    if not t.get("minutes"):
        return "لم تُسجَّل."
    text = f"{t['verses_per_hour']} بيتًا في الساعة ({t['minutes']} دقيقة من {t['started']} إلى {t['finished']}؛ {t['basis']})"
    if t.get("candidates_listed"):
        text += f". عُرض نحو {t['candidates_listed']} مرشحًا، وقُرئ نحو {t['read_in_context']} بيتًا في سياقه"
    return text + "."


def render_markdown(report, taxonomy):
    name = lambda i: taxonomy.labels[i]["name_ar"]
    b, c, d = report["status_batch"], report["status_cumulative"], report["duplicate_checks"]
    yes = lambda x: "نعم" if x else "لا"
    gaps = report["gaps_to_target"]
    gap_lines = [f"- {name(k.split('|')[0])} × {name(k.split('|')[1])}: ينقصها {n}" for k, n in
                 sorted(gaps.items(), key=lambda kv: (-kv[1], kv[0]))]
    below3 = [f"{name(k.split('|')[0])} × {name(k.split('|')[1])}" for k in report["corpus_cells_below_3_poems"]]
    return REPORT_MD.format(
        batch=report["batch"], records=report["records"], records_file=report["records_file"],
        first=report["verse_ids"][0], last=report["verse_ids"][1], model=report["annotation"]["model_id"],
        displayable=report["displayable_in_production"],
        attribution="، ".join(f"`{k}` {v}" for k, v in report["attribution"].items()),
        poets=report["poets"], notes=report["text_notes"],
        b_records=b["records"], c_records=c["records"], b_sv=b["source_verified"], c_sv=c["source_verified"],
        b_ao=b["apcd_only"], c_ao=c["apcd_only"], b_hr=b["human_reviewed"], c_hr=c["human_reviewed"],
        b_pe=b["production_eligible"], c_pe=c["production_eligible"], b_de=b["development_eligible"],
        c_de=c["development_eligible"], dup_rows=yes(d["apcd_rows_unique_in_corpus"]),
        dup_sha=yes(d["text_sha256_unique_in_corpus"]), dup_fold=yes(d["folded_text_unique_in_corpus"]),
        shared=("، ".join(f"{x} و{y}" for x, y in d["shared_hemistichs"]) or "لا شيء"),
        batch_poems=d["batch_poems"], poems_old=d["batch_poems_already_in_corpus"],
        throughput=throughput_text(report["throughput"]),
        uncertainty="، ".join(f"{k} {v}" for k, v in report["uncertainty"].items()),
        target=report["corpus"]["target_tier1_poems_per_cell"],
        batch_table=cell_table(report["batch_tier1_records_per_pilot_cell"], taxonomy),
        corpus_table=cell_table(report["corpus_tier1_poems_per_pilot_cell"], taxonomy),
        at_target=report["corpus"]["pilot_cells_at_target"], below3="، ".join(below3) or "لا شيء",
        gap=report["corpus"]["pilot_gap_total"], gaps="\n".join(gap_lines) or "- لا فجوات حتى الهدف.")


def build(spec_path, apcd_zip, kb_path):
    """Return (spec, records, existing) after every safety check; raises SystemExit on any problem."""
    with open(spec_path, encoding="utf-8") as fh:
        spec = json.load(fh)
    numbers = [v["apcd_row"] for v in spec["verses"]]
    rows = apcd.get_rows(numbers, apcd_zip)
    missing = sorted(set(numbers) - set(rows))
    if missing:
        raise SystemExit(f"APCD rows not found: {missing}")
    records = build_records(spec, rows, load_kb(kb_path))
    existing = other_records(spec["batch"])
    problems = corpus_conflicts(records, existing)
    issues = validate_records("poetry_record", list(enumerate(records, 1)),
                              Context(taxonomy=load_taxonomy(), mode="development", apcd_zip=apcd_zip))
    if problems or issues:
        for line in problems + [str(i) for i in issues]:
            print(line, file=sys.stderr)
        raise SystemExit(f"{len(problems)} corpus problem(s), {len(issues)} contract issue(s); nothing written")
    return spec, records, existing


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec")
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    parser.add_argument("--kb", default=DEFAULT_KB)
    parser.add_argument("--target", type=int, default=coverage.DEFAULT_TARGET)
    parser.add_argument("--check", action="store_true", help="compare the record file with a fresh build")
    parser.add_argument("--report-only", action="store_true",
                        help="rewrite the report only; the record file must equal a fresh build")
    args = parser.parse_args(argv)
    spec, records, existing = build(args.spec, args.apcd_zip, args.kb)
    path = records_path(spec["batch"])
    lines = [json.dumps(r, ensure_ascii=False) + "\n" for r in records]
    if args.check or args.report_only:
        with open(path, encoding="utf-8") as fh:
            same = fh.readlines() == lines
        print("record file matches a fresh build" if same else "record file differs from a fresh build")
        if not same or args.check:
            return 0 if same else 1
    else:
        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    taxonomy = load_taxonomy()
    report, _ = make_report(spec, records, existing + records, taxonomy, args.target)
    json_path, md_path = report_paths(spec["batch"])
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_markdown(report, taxonomy))
    print(json.dumps({k: report[k] for k in ("batch", "records", "attribution", "corpus")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
