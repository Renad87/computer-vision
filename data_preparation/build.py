"""Build the manifests and their reports.

    python -m data_preparation.build v0.9 [--emoset-zip external/renad/emoset.zip]
    python -m data_preparation.build v1   [--emoset-zip ...] [--places-dir external/shaden_visual] [--near-dup-decisions ...]

Outputs (all deterministic, relative paths only):
    datasets/manifests/<name>.jsonl + <name>.build.json
    datasets/reports/...   (see reports.py)
"""
import argparse
import os
import subprocess
import sys
from collections import Counter

from contracts.taxonomy import load_taxonomy
from contracts.validate import validate_file

from . import reports
from .cleaning import exact_duplicates, inspect
from .common import (PACKAGE_ROOT, SCHEMA_VERSION, TAXONOMY_VERSION, jsonl_bytes, order_record, rel, sha256_bytes,
                     sha256_file, sort_key, write_bytes, write_json)
from .sources import InputError, iter_emoset, iter_places

DEFAULT_EMOSET = os.path.join("external", "renad", "emoset.zip")
DEFAULT_PLACES = os.path.join("external", "shaden_visual")
MANIFESTS = os.path.join("datasets", "manifests")
REPORTS = os.path.join("datasets", "reports")
NAMES = {"v0.9": "manifest_v0.9_emotion", "v1": "manifest_v1"}


def counts(records):
    out = {}
    for r in records:
        key = f"{r['source_dataset']}|{r['split']}"
        c = out.setdefault(key, Counter())
        c["rows"] += 1
        c[f"scene:{r['scene_label_status']}"] += 1
        c[f"emotion:{r['emotion_label_status']}"] += 1
    return {k: dict(sorted(v.items())) for k, v in sorted(out.items())}


def run_validator(manifest_rel, root):
    """The validator CLI in production mode (run from the package root); returns (exit_code, issue_lines)."""
    target = manifest_rel if os.path.abspath(root) == PACKAGE_ROOT else os.path.join(root, manifest_rel)
    proc = subprocess.run([sys.executable, "-m", "contracts.validate", "image_manifest", target],
                          cwd=PACKAGE_ROOT, capture_output=True, text=True, encoding="utf-8")
    lines = [ln for ln in proc.stdout.splitlines() if ln.strip()]
    return proc.returncode, lines


def write_manifest(name, records, inputs, extra, root, command):
    recs = [order_record(r) for r in sorted(records, key=sort_key)]
    data = jsonl_bytes(recs)
    path = os.path.join(root, MANIFESTS, f"{name}.jsonl")
    write_bytes(path, data)
    issues = validate_file("image_manifest", path, mode="production")
    build = {
        "manifest": f"{MANIFESTS.replace(os.sep, '/')}/{name}.jsonl",
        "manifest_sha256": sha256_bytes(data),
        "records": len(recs),
        "schema_version": SCHEMA_VERSION, "taxonomy_version": TAXONOMY_VERSION,
        "command": command,
        "inputs": inputs,
        "counts_per_source_split_status": counts(recs),
        "validator": {"mode": "production", "issues": len(issues)},
        **extra,
    }
    write_json(os.path.join(root, MANIFESTS, f"{name}.build.json"), build)
    return recs, issues, build


def input_entry(path, role, root):
    return {"role": role, "path": rel(path, root), "sha256": sha256_file(path), "bytes": os.path.getsize(path)}


def build_v09(emoset_zip, root):
    tax = load_taxonomy()
    records, inventory, excluded, flagged = inspect(iter_emoset(emoset_zip, tax))
    kept, quarantine, escalations, groups = exact_duplicates(records)
    if escalations:
        raise InputError(f"{len(escalations)} exact duplicates between evaluation splits: report to Omar "
                         f"{escalations[:3]}")
    inputs = [input_entry(emoset_zip, "R1 emoset.zip (Renad)", root)]
    extra = {"excluded_images": len(excluded), "quarantined_images": len(quarantine),
             "exact_duplicate_groups": len(groups), "near_duplicate_search": "not run in v0.9 (method 3.1)",
             "scene_approach": "none in v0.9: scene unavailable, no metadata joined"}
    command = "python -m data_preparation.build v0.9 --emoset-zip " + rel(emoset_zip, root)
    recs, issues, build = write_manifest(NAMES["v0.9"], kept, inputs, extra, root, command)
    state = {"version": "v0.9", "inventory": inventory, "excluded": excluded, "flagged": flagged,
             "quarantine": quarantine, "exact_groups": groups, "inputs": inputs, "near": None,
             "taxonomy": tax}
    return recs, issues, build, state


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", choices=sorted(NAMES))
    ap.add_argument("--workdir", default=PACKAGE_ROOT,
                    help="folder holding external/ (inputs) and datasets/ (outputs); default: the package root")
    ap.add_argument("--emoset-zip", default=None, help="default: <workdir>/" + DEFAULT_EMOSET.replace(os.sep, "/"))
    ap.add_argument("--places-dir", default=None, help="default: <workdir>/" + DEFAULT_PLACES.replace(os.sep, "/"))
    ap.add_argument("--clip-features", default=None, help="v1: npz of CLIP embeddings (paths = image_path)")
    ap.add_argument("--near-dup-decisions", default=None, help="v1: reviewed near_duplicate_candidates.csv")
    a = ap.parse_args(argv)
    root = os.path.abspath(a.workdir)
    a.emoset_zip = a.emoset_zip or os.path.join(root, DEFAULT_EMOSET)
    a.places_dir = a.places_dir or os.path.join(root, DEFAULT_PLACES)
    try:
        if a.version == "v0.9":
            recs, issues, build, state = build_v09(a.emoset_zip, root)
        else:
            from .build_v1 import ReviewPending, build_v1
            from .reports_v1 import near_markdown
            try:
                recs, issues, build, state = build_v1(a, root)
            except ReviewPending as rp:
                state = rp.args[0]
                state["near"] = {"markdown": near_markdown(state)}
                reports.inventory(state, root)
                reports.duplicates(state, root)
                print(f"REVIEW NEEDED: {state['pending']} of {len(state['pairs'])} near-duplicate candidate pairs "
                      f"have no decision. Fill `decision` (same_image / different), `reviewer_id` and `date` in "
                      f"{state['decisions_path']} (pages: python -m data_preparation.review --workdir <W>), then "
                      f"re-run this build. No manifest_v1 was written.")
                return 3
            state["near"] = {"markdown": near_markdown(state)}
    except InputError as e:
        print("STOP:", e, file=sys.stderr)
        return 2
    code, lines = run_validator(build["manifest"], root)
    reports.write_all(state, root, run_validator)
    print(f"{build['manifest']}: {build['records']} records, validator exit {code}, issues {len(lines)}")
    for ln in lines[:20]:
        print("  ", ln)
    return 0 if code == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
