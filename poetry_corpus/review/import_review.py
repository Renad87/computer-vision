"""Import a returned human review workbook into the corpus (Python standard library only).

    python3 -m poetry_corpus.review.import_review <returned.xlsx|.csv> --reviewer human:renad
        [--base poetry_corpus/exports/corpus_all_v1.jsonl] [--sent <package workbook>] [--date YYYY-MM-DD]
        [--out-version v2] [--apcd-zip PATH] [--dry-run]

Reads the sheet with poetry_corpus.tools.review_sheet.read_review (the same reader and column contract as the
packages), checks every row against the base corpus, and imports only valid, unambiguous human decisions:

- emotion ACCEPT with both correction columns empty -> review.decisions {dimension: emotion, decision: accept};
  rows whose emotion was already accepted in the base corpus (visual-only rows) must leave the emotion cells
  empty, so no decision is recorded twice;
- visual ACCEPT (only when the sheet has the visual_decision column) -> {dimension: visual, decision: accept};
- a record changes only when every decision on its row is such an unambiguous ACCEPT. It then becomes
  annotation.method = ai_draft_human_reviewed, review.status = reviewed, reviewer added to review.reviewers.

Everything else stays exactly as in the base corpus (pending, not_reviewed) and is listed in the report with
the cell values that made it pending: REJECT (never made displayable here), CORRECT and UNSURE (labels would
change: not applied automatically), ACCEPT or REJECT with correction cells filled (contradictory), missing
decisions, and rows whose verse text differs from text_original. Nothing in this module invents a decision,
a note or a correction: notes are copied verbatim, and an empty cell stays empty (null).

Outputs (new files only): poetry_corpus/exports/corpus_all_<v>.jsonl, production_eligible_<v>.jsonl and
poetry_corpus/reports/review_import_<v>.{json,md}. The base corpus file is only read.
"""
import argparse
import collections
import copy
import datetime
import hashlib
import json
import os
import re
import sys
import zipfile

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, load_jsonl, validate_records

from poetry_corpus.tools.review_sheet import NONE_AR, _to_id, read_review
from poetry_corpus.tools.xlsx import read_workbook

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXPORTS = os.path.join(ROOT, "poetry_corpus", "exports")
REPORTS = os.path.join(ROOT, "poetry_corpus", "reports")
BASE = os.path.join(EXPORTS, "corpus_all_v1.jsonl")
REVIEWER_CELLS = ("decision", "corrected_primary", "corrected_secondary", "note", "visual_decision")

IMPORTED, PENDING = "imported", "pending"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def workbook_modified_date(path):
    """Date part of docProps/core.xml dcterms:modified (the reviewer's last save), or None."""
    if not path.lower().endswith(".xlsx"):
        return None
    try:
        with zipfile.ZipFile(path) as archive:
            core = archive.read("docProps/core.xml").decode("utf-8")
    except (KeyError, zipfile.BadZipFile):
        return None
    match = re.search(r"<dcterms:modified[^>]*>(\d{4}-\d{2}-\d{2})T", core)
    return match.group(1) if match else None


def _cell(row, field):
    value = row.get(field)
    return "" if value is None else str(value).strip()


def classify(rows, records_by_id, taxonomy=None, has_visual=None):
    """One result per sheet row: {verse_id, status, reasons, emotion, visual, note, cells, text_match}.
    status is IMPORTED only when every decision on the row is an unambiguous ACCEPT."""
    taxonomy = taxonomy or load_taxonomy()
    if has_visual is None:
        has_visual = any("visual_decision" in r for r in rows)
    results, seen = [], set()
    for row in rows:
        verse_id = _cell(row, "verse_id")
        cells = {f: _cell(row, f) for f in REVIEWER_CELLS if f != "visual_decision" or has_visual}
        item = {"verse_id": verse_id, "cells": cells, "reasons": [], "emotion": None, "visual": None,
                "note": cells.get("note") or None, "text_match": None, "status": PENDING}
        results.append(item)
        record = records_by_id.get(verse_id)
        if record is None:
            item["reasons"].append("verse_id not found in the base corpus")
            continue
        if verse_id in seen:
            item["reasons"].append("verse_id appears twice in the sheet")
        seen.add(verse_id)
        item["text_match"] = str(row.get("text_original", "")) == record["text_original"]
        if not item["text_match"]:
            item["reasons"].append("verse text in the sheet differs from text_original")

        decision = cells["decision"].upper()
        primary = _to_id(cells["corrected_primary"], taxonomy, allow_none=False)
        secondary = _to_id(cells["corrected_secondary"], taxonomy, allow_none=True)
        corrections = bool(cells["corrected_primary"] or cells["corrected_secondary"])
        emotion_done = [d["reviewer_id"] for d in record["review"]["decisions"]
                        if d["dimension"] in ("emotion", "all") and d["decision"] == "accept"]
        if emotion_done and (decision or corrections):
            item["reasons"].append(f"emotion already reviewed by {', '.join(emotion_done)}; this row's emotion "
                                   "cells must stay empty (duplicate decision not imported)")
        elif emotion_done:
            pass  # visual-only row: the emotion decision already exists in the base corpus
        elif not decision:
            item["reasons"].append("no emotion decision")
        elif decision not in ("ACCEPT", "CORRECT", "REJECT", "UNSURE"):
            item["reasons"].append(f"emotion decision {cells['decision']!r} is not ACCEPT/CORRECT/REJECT/UNSURE")
        elif decision == "ACCEPT" and corrections:
            item["reasons"].append("ACCEPT with a correction cell filled: contradictory (accept the draft, or "
                                   "correct it?)")
        elif decision == "ACCEPT":
            item["emotion"] = "accept"
        elif decision == "REJECT" and corrections:
            item["reasons"].append("REJECT with a corrected emotion filled: REJECT (draft wrong) or CORRECT (to "
                                   "the filled emotion)?" + ("" if cells["note"] else "; note empty"))
        elif decision == "REJECT":
            item["reasons"].append("REJECT: not made displayable" + ("" if cells["note"] else "; note missing"))
        elif decision == "CORRECT":
            valid = primary is not None and secondary is not None and (primary or secondary)
            item["reasons"].append("CORRECT: label change not applied automatically"
                                   + ("" if valid else "; correction is not a valid literary emotion"))
        else:
            item["reasons"].append("UNSURE")
        if primary is None or secondary is None:
            item["reasons"].append("a correction cell is not one of the eight literary emotions or " + NONE_AR)

        if has_visual:
            visual = cells.get("visual_decision", "").upper()
            if visual == "ACCEPT":
                item["visual"] = "accept"
            elif not visual:
                item["reasons"].append("no visual decision")
            else:
                item["reasons"].append(f"visual decision {cells.get('visual_decision')!r}: not imported")
        if not item["reasons"] and (item["emotion"] or item["visual"]):
            item["status"] = IMPORTED
        elif not item["reasons"]:
            item["reasons"].append("no decision to import")
    return results


def apply(records, results, reviewer_id, date):
    """Return a deep copy of records with the IMPORTED results applied; other records are untouched objects
    (copied, not modified)."""
    by_id = {r["verse_id"]: r for r in results if r["status"] == IMPORTED}
    out = []
    for record in records:
        result = by_id.get(record["verse_id"])
        record = copy.deepcopy(record)
        if result:
            if record["annotation"]["method"] == "ai_draft":
                record["annotation"]["method"] = "ai_draft_human_reviewed"
            review = record["review"]
            if reviewer_id not in review["reviewers"]:
                review["reviewers"].append(reviewer_id)
            if review["status"] == "not_reviewed":
                review["status"] = "reviewed"
            for dimension in ("emotion", "visual"):
                if result[dimension] == "accept":
                    review["decisions"].append({"reviewer_id": reviewer_id, "dimension": dimension,
                                                "decision": "accept", "note": result["note"], "date": date})
        out.append(record)
    return out


def compare_with_sent(returned_path, sent_path):
    """Cells that differ between the sent package workbook and the returned one, outside the reviewer columns
    and outside formula results. Returns [(sheet, row, column, sent, returned)]."""
    returned, sent = read_workbook(returned_path), read_workbook(sent_path)
    review_sheet = "المراجعة"
    reviewer_letters = set()
    header = sent.get(review_sheet, {}).get(1, {})
    for letters, text in header.items():
        m = re.search(r"\(([a-z_]+)\)\s*$", str(text or ""))
        if m and m.group(1) in REVIEWER_CELLS:
            reviewer_letters.add(letters)
    diffs = []
    for name in sorted(set(returned) | set(sent)):
        a, b = sent.get(name, {}), returned.get(name, {})
        for r in sorted(set(a) | set(b)):
            for c in sorted(set(a.get(r, {})) | set(b.get(r, {}))):
                va, vb = a.get(r, {}).get(c), b.get(r, {}).get(c)
                if (va if va != "" else None) == (vb if vb != "" else None):
                    continue
                if name == review_sheet and c in reviewer_letters and r > 1:
                    continue
                diffs.append((name, r, c, va, vb))
    return diffs


def dump_jsonl(records, path):
    with open(path, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("workbook")
    parser.add_argument("--reviewer", required=True, help="reviewer id recorded in review.reviewers")
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--sent", default=None, help="the package workbook as sent, to check untouched cells")
    parser.add_argument("--date", default=None, help="decision date (default: workbook docProps modified date)")
    parser.add_argument("--out-version", default="v2")
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    taxonomy = load_taxonomy()
    loaded, issues = load_jsonl(args.base)
    if issues:
        raise SystemExit(f"{args.base}: {issues}")
    records = [r for _, r in loaded]
    by_id = {r["verse_id"]: r for r in records}
    rows = read_review(args.workbook)
    results = classify(rows, by_id, taxonomy)
    date = args.date or workbook_modified_date(args.workbook)
    if not date:
        raise SystemExit("no --date given and the workbook has no modified date")
    datetime.date.fromisoformat(date)
    for item in results:
        print(f"{item['verse_id']}\t{item['status']}\t{'; '.join(item['reasons'])}")
    if args.dry_run:
        return 0
    new = apply(records, results, args.reviewer, date)
    v = args.out_version
    corpus_path = os.path.join(EXPORTS, f"corpus_all_{v}.jsonl")
    prod_path = os.path.join(EXPORTS, f"production_eligible_{v}.jsonl")
    for path in (corpus_path, prod_path):
        if os.path.exists(path):
            raise SystemExit(f"{path} exists; new files only")
    dump_jsonl(new, corpus_path)
    dump_jsonl([r for r in new if display_allowed(r, "production")], prod_path)
    summary = report(args, records, new, results, rows, corpus_path, prod_path, date, taxonomy)
    print(json.dumps(summary["counts"], ensure_ascii=False), file=sys.stderr)
    return 0


# --------------------------------------------------------------------------------------------- report
def _validate(path, mode, apcd_zip=None):
    from contracts.validate import validate_file
    return [str(i) for i in validate_file("poetry_record", path, mode=mode, apcd_zip=apcd_zip)]


def corpus_counts(records):
    from poetry_corpus.tools.export_corpus import copyright_status
    def has(record, dimension):
        return any(d["dimension"] in (dimension, "all") and d["decision"] in ("accept", "correct", "adjudicate")
                   for d in record["review"]["decisions"])
    return {
        "total_verses": len(records),
        "text_verification_apcd_row_exact": sum(r["text_verification"]["method"] == "apcd_row_exact" for r in records),
        "attribution_status": dict(sorted(collections.Counter(r["attribution_status"] for r in records).items())),
        "ai_draft_only_not_reviewed": sum(r["annotation"]["method"] == "ai_draft"
                                          and r["review"]["status"] == "not_reviewed" for r in records),
        "human_reviewed_emotion": sum(has(r, "emotion") for r in records),
        "human_reviewed_visual_association": sum(has(r, "visual") for r in records),
        "review_status": dict(sorted(collections.Counter(r["review"]["status"] for r in records).items())),
        "annotation_method": dict(sorted(collections.Counter(r["annotation"]["method"] for r in records).items())),
        "display_allowed_production": sum(display_allowed(r, "production") for r in records),
        "display_allowed_development": sum(display_allowed(r, "development") for r in records),
        "copyright_status_derived": dict(sorted(collections.Counter(copyright_status(r) for r in records).items())),
    }


def report(args, old, new, results, rows, corpus_path, prod_path, date, taxonomy):
    changed = [n["verse_id"] for o, n in zip(old, new) if o != n]
    # unchanged records must serialize to exactly the base file's lines
    with open(args.base, encoding="utf-8") as fh:
        base_lines = fh.readlines()
    with open(corpus_path, encoding="utf-8") as fh:
        new_lines = fh.readlines()
    differing_lines = [i for i, (a, b) in enumerate(zip(base_lines, new_lines)) if a != b]
    apcd_zip = args.apcd_zip if apcd.available(args.apcd_zip) else None
    validation = {}
    for label, path in (("corpus", corpus_path), ("production_eligible", prod_path)):
        for mode in ("production", "development"):
            validation[f"{label}:{mode}"] = _validate(path, mode)
        if apcd_zip:
            validation[f"{label}:production+apcd_zip"] = _validate(path, "production", apcd_zip)
    decisions = collections.Counter(item["cells"]["decision"].upper() or "(empty)" for item in results)
    pending = [item for item in results if item["status"] == PENDING]
    sent_diffs = compare_with_sent(args.workbook, args.sent) if args.sent else None
    summary = {
        "workbook": os.path.relpath(args.workbook, ROOT) if os.path.abspath(args.workbook).startswith(ROOT)
        else args.workbook,
        "workbook_sha256": sha256_file(args.workbook),
        "sent_workbook": os.path.relpath(args.sent, ROOT) if args.sent else None,
        "sent_workbook_sha256": sha256_file(args.sent) if args.sent else None,
        "non_reviewer_cells_changed_vs_sent": None if sent_diffs is None else [
            {"sheet": s, "row": r, "col": c, "sent": a, "returned": b} for s, r, c, a, b in sent_diffs],
        "reviewer_id": args.reviewer,
        "decision_date": date,
        "decision_date_source": "--date" if args.date else "workbook docProps/core.xml dcterms:modified",
        "sheet_has_visual_decision_column": any("visual_decision" in r for r in rows),
        "base_corpus": os.path.relpath(args.base, ROOT),
        "base_corpus_sha256": sha256_file(args.base),
        "corpus_v2": os.path.relpath(corpus_path, ROOT),
        "corpus_v2_sha256": sha256_file(corpus_path),
        "production_eligible_v2": os.path.relpath(prod_path, ROOT),
        "production_eligible_v2_sha256": sha256_file(prod_path),
        "counts": {
            "sheet_rows": len(results),
            "verse_ids_found_in_base": sum(item["text_match"] is not None for item in results),
            "verse_text_equals_text_original": sum(item["text_match"] is True for item in results),
            "emotion_decisions": dict(sorted(decisions.items())),
            "imported": sum(item["status"] == IMPORTED for item in results),
            "pending": len(pending),
            "records_changed": len(changed),
            "base_lines_differing": len(differing_lines),
        },
        "imported_verse_ids": [item["verse_id"] for item in results if item["status"] == IMPORTED],
        "pending": [{"verse_id": item["verse_id"], "cells": item["cells"], "reasons": item["reasons"]}
                    for item in pending],
        "validation": {k: {"issues": len(v), "first": v[:5]} for k, v in validation.items()},
        "apcd_zip": os.path.relpath(apcd_zip, ROOT) if apcd_zip else None,
        "corpus_before": corpus_counts(old),
        "corpus_after": corpus_counts(new),
    }
    if sorted(changed) != sorted(summary["imported_verse_ids"]) or \
            len(differing_lines) != len(changed) or len(base_lines) != len(new_lines):
        raise SystemExit("v2 differs from v1 outside the imported records")
    base = os.path.join(REPORTS, f"review_import_{args.out_version}")
    with open(base + ".json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    return summary


if __name__ == "__main__":
    sys.exit(main())
