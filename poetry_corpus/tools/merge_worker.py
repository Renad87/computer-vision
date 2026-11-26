"""Coordinator: merge one parallel worker's output into the corpus as the next P2 batch.

    python3 -m poetry_corpus.tools.merge_worker poetry_corpus/drafts/p2_workers/<worker>.json [--launched ISO]

1. Re-runs check_worker_spec against the current corpus (so rows or verses merged meanwhile by another worker
   are caught) and drops every verse with a problem; dropped verses are listed in the merge log.
2. Assigns stable ids continuing from the highest id of all record files, in the worker's own order, and names
   the batch p2_bNN by arrival order, so ids always continue across files (build_batch checks this).
3. Writes poetry_corpus/drafts/<batch>_ai_draft_specs_v1.json and builds the records and the batch report with
   build_batch (validator in development mode against APCD; it refuses to write on any problem).
4. Appends a line to poetry_corpus/drafts/p2_workers/merge_log.jsonl.
"""
import argparse
import datetime
import glob
import json
import os
import re
import sys

from contracts import apcd

from . import build_batch
from .attribution_check import conflicts as attribution_conflicts
from .build_p0_drafts import locate
from .check_worker_spec import check
from .coverage import TIER1_RELATIONS
from .find_candidates import MODERN_ERA, fold
from .coverage import RECORDS_DIR, load_records, record_files

ROOT = build_batch.ROOT
WORKERS_DIR = os.path.join(ROOT, "poetry_corpus", "drafts", "p2_workers")
LOG = os.path.join(WORKERS_DIR, "merge_log.jsonl")
QA_PATCHES = os.path.join(ROOT, "poetry_corpus", "drafts", "p2_qa", "qa_patches.json")
PATCHED_DIR = os.path.join(WORKERS_DIR, "patched")
WISH = re.compile(r"(?:^|\s)[وف]?(?:يا\s?)?ليت(?:ني|نا|ها|ه|هم)?(?=\s|$)")


def apply_qa(worker, patches_path=QA_PATCHES):
    """Apply the QA patch file and the two systemic rules; returns (patched worker, log lines).
    Rules: a pre-modern city named in the verse belongs to scene_group.heritage (taxonomy: city = modern streets);
    a scene named only inside a ليت wish is relation.hypothetical. A verse left without a literal or
    scene_association scene-group relation is dropped. The worker's own file is never changed."""
    qa = {"rejects": {}, "patches": {}}
    if os.path.isfile(patches_path):
        with open(patches_path, encoding="utf-8") as fh:
            qa = json.load(fh)
    rows = apcd.get_rows([v["apcd_row"] for v in worker["verses"]])
    out, log = [], []
    for v in worker["verses"]:
        key, row = str(v["apcd_row"]), rows.get(v["apcd_row"])
        if key in qa["rejects"]:
            log.append(f"{key}\treject\t{qa['rejects'][key]}")
            continue
        v = json.loads(json.dumps(v))
        patch = qa["patches"].get(key, {})
        for field in ("primary", "secondary", "meaning", "text_note", "uncertainty"):
            if field in patch:
                v[field] = patch[field]
        for entry in patch.get("visual_set", []):
            v["visual"] = [a for a in v["visual"] if a["target"] != entry["target"]] + [entry]
        for entry in patch.get("visual_add", []):
            if all(a["target"] != entry["target"] for a in v["visual"]):
                v["visual"].append(entry)
        if patch:
            log.append(f"{key}\tpatch\t{sorted(patch)}")
        if row is None:
            out.append(v)
            continue
        if row[apcd.ERA] != MODERN_ERA:
            targets = {a["target"] for a in v["visual"]}
            fixed = []
            for a in v["visual"]:
                if a["target"] == "scene_group.city":
                    if "scene_group.heritage" in targets:
                        continue
                    a = dict(a, target="scene_group.heritage")
                    log.append(f"{key}\tcity->heritage\tpre-modern city")
                fixed.append(a)
            v["visual"] = fixed
        text = row[apcd.VERSE]
        plain = fold(text)
        wish = WISH.search(plain)
        if wish:
            for a in v["visual"]:
                if a.get("evidence") and a["relation"] in TIER1_RELATIONS:
                    try:
                        start = locate(text, a["evidence"])["start"]
                    except SystemExit:
                        continue
                    if len(fold(text[:start])) > wish.start():
                        a["relation"], a["justification"] = "relation.hypothetical", None
                        log.append(f"{key}\twish->hypothetical\t{a['target']}")
        if not any(a["target"].startswith("scene_group.") and a["relation"] in TIER1_RELATIONS for a in v["visual"]):
            log.append(f"{key}\treject\tno literal or scene_association scene left after the rules")
            continue
        out.append(v)
    return dict(worker, verses=out), log
MODEL_ID = re.compile(r"claude-[a-z0-9.-]+")


def next_batch():
    taken = [os.path.basename(p) for p in glob.glob(os.path.join(RECORDS_DIR, "p2_b*_ai_drafts_v1.jsonl"))]
    numbers = [int(re.match(r"p2_b(\d+)_", name).group(1)) for name in taken]
    return f"p2_b{max(numbers, default=0) + 1:02d}"


def merge(worker_path, launched=None):
    with open(worker_path, encoding="utf-8") as fh:
        worker = json.load(fh)
    name = worker.get("worker") or os.path.splitext(os.path.basename(worker_path))[0]
    if not MODEL_ID.fullmatch(str(worker.get("model_id", ""))):
        raise SystemExit(f"{name}: model_id {worker.get('model_id')!r} is not a model id; not merged")
    total_original = len(worker["verses"])
    worker, qa_log = apply_qa(worker)
    os.makedirs(PATCHED_DIR, exist_ok=True)
    patched_path = os.path.join(PATCHED_DIR, f"{name}.json")
    with open(patched_path, "w", encoding="utf-8") as fh:
        json.dump(worker, fh, ensure_ascii=False, indent=1)
    problems, total = check(patched_path)
    bad = {i for i, _, _ in problems}
    # attribution: drop verses whose text (or a near variant) appears under another poet in APCD
    candidates = [(i, v) for i, v in enumerate(worker["verses"]) if i not in bad]
    rows = apcd.get_rows([v["apcd_row"] for _, v in candidates])
    temp = build_batch.build_records(dict(worker, verses=[dict(v, n=900000 + i) for i, v in candidates]), rows, {})
    clashes = attribution_conflicts(temp)
    for (i, v), rec in zip(candidates, temp):
        if clashes.get(rec["verse_id"], {}).get("full_verse"):
            bad.add(i)
            problems.append((i, v["apcd_row"], f"same verse under another poet: {clashes[rec['verse_id']]['full_verse'][:3]}"))
    keep = [v for i, v in enumerate(worker["verses"]) if i not in bad]
    if not keep:
        raise SystemExit(f"{name}: no verse passed the check; nothing merged")
    corpus = [r for _, r in load_records(record_files())]
    start = max(int(r["verse_id"].rsplit(":", 1)[1]) for r in corpus) + 1
    batch = next_batch()
    finished = datetime.datetime.fromtimestamp(os.path.getmtime(worker_path)).isoformat(timespec="seconds")
    minutes = None
    if launched:
        delta = datetime.datetime.fromisoformat(finished) - datetime.datetime.fromisoformat(launched)
        minutes = max(1, round(delta.total_seconds() / 60))
    spec = {
        "batch": batch,
        "description": (f"P2 parallel worker {name} ({worker.get('group', '')}): AI draft annotations by "
                        f"{worker['model_id']} on a disjoint candidate pool from poetry_corpus/tools/"
                        "build_candidate_index.py, pre-checked with check_worker_spec and merged by "
                        "poetry_corpus/tools/merge_worker.py. Verse text is not stored here; build_batch copies "
                        "it from APCD. Labels are drafts pending human review."),
        "model_id": worker["model_id"],
        "date": worker.get("date") or datetime.date.today().isoformat(),
        "worker": name,
        "work_log": {"started": launched, "finished": finished, "minutes": minutes,
                     "basis": "worker launch time to the worker file time; 18 workers ran in parallel, so "
                              "this is wall time per worker, not total effort",
                     "candidates_listed": None, "read_in_context": None},
        "verses": [dict(v, n=start + i) for i, v in enumerate(keep)],
    }
    spec_path = os.path.join(ROOT, "poetry_corpus", "drafts", f"{batch}_ai_draft_specs_v1.json")
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    build_batch.main([spec_path])
    entry = {"worker": name, "worker_file": os.path.relpath(worker_path, ROOT), "batch": batch,
             "verses_in_worker_file": total_original, "after_qa_rules": total, "qa_log": qa_log,
             "merged": len(keep), "dropped": sorted(bad),
             "drop_reasons": [f"{i}\t{row}\t{msg}" for i, row, msg in problems],
             "ids": [f"pv:verse:{start:06d}", f"pv:verse:{start + len(keep) - 1:06d}"],
             "merged_at": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("worker")
    parser.add_argument("--launched", default=None, help="worker launch time (ISO), for throughput")
    args = parser.parse_args(argv)
    entry = merge(args.worker, args.launched)
    print(json.dumps({k: entry[k] for k in ("worker", "batch", "verses_in_worker_file", "merged", "ids")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
