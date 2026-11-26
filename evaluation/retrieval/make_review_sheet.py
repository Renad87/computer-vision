"""Pooled, blind retrieval judgment sheet, and import of completed sheets as `evaluation_record` JSONL.

Build (union of every method's top 3 per query, shuffled with a fixed seed, method hidden):
    python3 -m evaluation.retrieval.make_review_sheet build --corpus-version p0_ai_drafts_v1 --date 2026-11-26

    -> evaluation/retrieval/review/sheet__<corpus_version>__<date>.csv      (what raters see)
       evaluation/retrieval/review/mapping__<corpus_version>__<date>.json   (kept away from raters)

Import one rater's completed sheet (ratings 0-3 in visual_fit, emotion_fit, overall):
    python3 -m evaluation.retrieval.make_review_sheet import --sheet completed.csv --rater-id R1 \
        --mapping evaluation/retrieval/review/mapping__....json --out evaluation/retrieval/review/ratings_R1.jsonl

The sheet never contains ratings. Ratings come only from real human raters; nothing here creates them.
"""
import argparse
import csv
import datetime
import hashlib
import json
import os
import random
import uuid

from contracts.taxonomy import load_taxonomy
from retrieval.engine import ENGINE_VERSION

from .run_experiments import METHODS, ROOT, RUNS, load_scenarios

REVIEW = os.path.join(ROOT, "evaluation", "retrieval", "review")
SEED = 20261126
SHEET_COLUMNS = ("sheet_item_id", "query_ref", "image_items_ar", "selected_emotion_ar", "symbolic_allowed",
                 "verse_text", "poet", "visual_fit", "emotion_fit", "overall", "notes")
RATING_COLUMNS = ("visual_fit", "emotion_fit", "overall")
SELECTION_AR = {"focus": "تركيز", "primary": "أساسي", "secondary": "ثانوي"}
TAXONOMY = load_taxonomy()


def _uuid4_from(text):
    return str(uuid.UUID(bytes=hashlib.sha256(text.encode()).digest()[:16], version=4))


def item_id(profile_id, verse_id):
    """Depends only on (query, verse): it never reveals which method returned the verse."""
    return "R" + hashlib.sha256(f"{profile_id}|{verse_id}".encode()).hexdigest()[:12]


def load_runs(runs_dir, corpus_version, date, methods=None):
    out = {}
    for _, method, _ in METHODS:
        if methods and method not in methods:
            continue
        path = os.path.join(runs_dir, f"{method}__{corpus_version}__{date}.jsonl")
        with open(path, encoding="utf-8") as fh:
            out[method] = [json.loads(line) for line in fh if line.strip()]
    return out


def build(runs_dir, corpus_version, date, out_dir=REVIEW, seed=SEED, methods=None):
    scenarios = load_scenarios()
    runs = load_runs(runs_dir, corpus_version, date, methods)
    pooled, mapping = {}, {"seed": seed, "corpus_version": corpus_version, "date": date, "queries": {}, "items": {}}
    for qn, s in enumerate(scenarios, 1):
        ref = f"Q{qn:02d}"
        profile = s["profile"]
        mapping["queries"][ref] = {"scenario": s["name"], "profile_id": profile["profile_id"]}
        visual = "؛ ".join(f"{TAXONOMY.labels[x['id']]['name_ar']} ({SELECTION_AR[x['user_selection']]})"
                           for x in profile["confirmed_visual_items"]) or "لا عنصر بصري"
        for method, docs in runs.items():
            doc = docs[qn - 1]
            if doc["profile_id"] != profile["profile_id"]:
                raise ValueError(f"{method}: run order does not match the scenarios at {ref}")
            for it in doc["items"][:3]:
                iid = item_id(profile["profile_id"], it["verse_id"])
                if iid not in pooled:
                    pooled[iid] = {"sheet_item_id": iid, "query_ref": ref, "image_items_ar": visual,
                                   "selected_emotion_ar": TAXONOMY.labels[profile["selected_lit_emotion"]]["name_ar"],
                                   "symbolic_allowed": "نعم" if profile["symbolic_allowed"] else "لا",
                                   "verse_text": it["text_original"], "poet": it["poet_name_apcd"],
                                   "visual_fit": "", "emotion_fit": "", "overall": "", "notes": ""}
                    mapping["items"][iid] = {"query_ref": ref, "profile_id": profile["profile_id"],
                                             "verse_id": it["verse_id"], "methods": {}}
                mapping["items"][iid]["methods"][method] = it["rank"]
    rows = sorted(pooled.values(), key=lambda r: r["sheet_item_id"])
    random.Random(seed).shuffle(rows)
    os.makedirs(out_dir, exist_ok=True)
    sheet = os.path.join(out_dir, f"sheet__{corpus_version}__{date}.csv")
    with open(sheet, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    mapping_path = os.path.join(out_dir, f"mapping__{corpus_version}__{date}.json")
    with open(mapping_path, "w", encoding="utf-8") as fh:
        json.dump(mapping, fh, ensure_ascii=False, indent=2)
    return sheet, mapping_path, len(rows)


def import_sheet(sheet_path, rater_id, mapping_path, timestamp=None):
    """Completed sheet -> (evaluation_record list, number of incomplete rows). Rows missing any rating are skipped."""
    with open(mapping_path, encoding="utf-8") as fh:
        mapping = json.load(fh)
    timestamp = timestamp or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records, incomplete = [], 0
    with open(sheet_path, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            iid = row["sheet_item_id"]
            if iid not in mapping["items"]:
                raise ValueError(f"{iid}: not in the mapping")
            values = [row.get(c, "").strip() for c in RATING_COLUMNS]
            if not all(values):
                incomplete += 1
                continue
            rating = {c: int(v) for c, v in zip(RATING_COLUMNS, values)}
            if not all(0 <= v <= 3 for v in rating.values()):
                raise ValueError(f"{iid}: ratings must be 0-3")
            records.append({
                "schema_version": "1.0.0", "taxonomy_version": TAXONOMY.version,
                "eval_id": _uuid4_from(f"{rater_id}|{iid}|{mapping['corpus_version']}|{mapping['date']}"),
                "layer": "retrieval",
                "test_set": {"id": f"dev_profiles__{mapping['corpus_version']}__{mapping['date']}", "manifest_sha256": None},
                "system": {"model_version": None, "corpus_version": mapping["corpus_version"],
                           "engine_version": ENGINE_VERSION, "method": None},
                "item_id": iid, "rater_id": rater_id, "blind": True,
                "rating": {**rating, "explanation_correct": None, "text_authentic": None, "judgment": None},
                "notes": row.get("notes") or None, "timestamp": timestamp})
    return records, incomplete


def main(argv=None):
    parser = argparse.ArgumentParser(description="Blind pooled retrieval judgment sheet")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--runs-dir", default=RUNS)
    b.add_argument("--corpus-version", default="p0_ai_drafts_v1")
    b.add_argument("--date", required=True)
    b.add_argument("--out-dir", default=REVIEW)
    i = sub.add_parser("import")
    i.add_argument("--sheet", required=True)
    i.add_argument("--rater-id", required=True)
    i.add_argument("--mapping", required=True)
    i.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        sheet, mapping, n = build(args.runs_dir, args.corpus_version, args.date, args.out_dir)
        print(f"{n} pooled items\n{sheet}\n{mapping} (keep this file away from raters)")
        return 0
    records, incomplete = import_sheet(args.sheet, args.rater_id, args.mapping)
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in records:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(records)} complete ratings -> {args.out}; {incomplete} incomplete rows skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
