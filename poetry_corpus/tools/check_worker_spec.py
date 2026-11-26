"""Pre-merge check for one worker output file (labels and APCD row numbers only, never verse text).

    python3 -m poetry_corpus.tools.check_worker_spec WORKER.json [--pool POOL.jsonl] [--apcd-zip PATH]

Every verse is built in memory with build_batch.build_records under a temporary id, so evidence spans are cut
from the APCD text exactly as they will be at merge time, and the drafts are validated with the poetry_record
validator in development mode against APCD. Also checked: rows are eligible (find_candidates.eligible), not used
by any record file, unique in the file and (with --pool) inside the worker's pool; the folded text is not
already in the corpus; each verse has at least one literal or scene_association relation to a scene group.
Prints one line per problem: <index> <apcd_row> <message>. Exit 0 when clean, 1 otherwise.
"""
import argparse
import json
import sys

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, validate_records

from .build_batch import build_records, folded
from .build_p0_drafts import DEFAULT_KB, load_kb
from .coverage import TIER1_RELATIONS, load_records, record_files
from .find_candidates import eligible

TEMP_BASE = 900000
REQUIRED = ("apcd_row", "primary", "secondary", "visual", "meaning", "uncertainty")


def check(path, pool_path=None, zip_path=None):
    with open(path, encoding="utf-8") as fh:
        spec = json.load(fh)
    problems = []
    for key in ("model_id", "date", "verses"):
        if not spec.get(key):
            problems.append((-1, None, f"missing top-level field {key!r}"))
    if problems:
        return problems, 0
    taxonomy = load_taxonomy()
    corpus = [r for _, r in load_records(record_files())]
    used_rows = {r["apcd_row"] for r in corpus}
    used_folded = {folded(r["text_original"]) for r in corpus}
    pool = None
    if pool_path:
        with open(pool_path, encoding="utf-8") as fh:
            pool = {json.loads(line)["row"] for line in fh if line.strip()}
    verses = spec["verses"]
    rows = apcd.get_rows([v.get("apcd_row") for v in verses if isinstance(v.get("apcd_row"), int)], zip_path)
    kb = load_kb(DEFAULT_KB)
    built, seen_rows, seen_folded = [], set(), set()
    for i, v in enumerate(verses):
        row_number = v.get("apcd_row")
        missing = [k for k in REQUIRED if k not in v]
        if missing:
            problems.append((i, row_number, f"missing fields {missing}"))
            continue
        row = rows.get(row_number)
        if row is None:
            problems.append((i, row_number, "APCD row not found"))
            continue
        if row_number in used_rows:
            problems.append((i, row_number, "row already in the corpus"))
        if row_number in seen_rows:
            problems.append((i, row_number, "row repeated in this file"))
        if pool is not None and row_number not in pool:
            problems.append((i, row_number, "row is not in this worker's pool"))
        if not eligible(row):
            problems.append((i, row_number, "row not eligible (hemistich, disputed poet or modern copyright)"))
        key = folded(row[apcd.VERSE])
        if key in used_folded or key in seen_folded:
            problems.append((i, row_number, "same verse (ignoring diacritics) already in corpus or file"))
        seen_rows.add(row_number)
        seen_folded.add(key)
        scene_ok = any(taxonomy.layer(a.get("target")) == "scene_group" and a.get("relation") in TIER1_RELATIONS
                       for a in v.get("visual") or [])
        if not scene_ok:
            problems.append((i, row_number, "needs a literal or scene_association relation to a scene group"))
        one = dict(spec, verses=[dict(v, n=TEMP_BASE + i)])
        try:
            built.append((i, build_records(one, rows, kb)[0]))
        except SystemExit as exc:  # an evidence phrase not found exactly once
            problems.append((i, row_number, str(exc)))
        except (KeyError, TypeError) as exc:
            problems.append((i, row_number, f"malformed entry: {exc!r}"))
    if built:
        issues = validate_records("poetry_record", [(n, r) for n, (_, r) in enumerate(built, 1)],
                                  Context(taxonomy=taxonomy, mode="development", apcd_zip=zip_path or apcd.DEFAULT_ZIP))
        for issue in issues:
            line = int(issue.path.split(":", 1)[0][1:]) if issue.path.startswith("L") else 0
            i = built[line - 1][0] if line else -1
            problems.append((i, verses[i].get("apcd_row") if i >= 0 else None, f"{issue.code} {issue.path.split(':', 1)[-1]}: {issue.message}"))
    return problems, len(verses)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("path")
    parser.add_argument("--pool", default=None)
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    args = parser.parse_args(argv)
    problems, total = check(args.path, args.pool, args.apcd_zip)
    for i, row, message in problems:
        print(f"{i}\t{row}\t{message}")
    bad = len({i for i, _, _ in problems})
    print(json.dumps({"verses": total, "verses_with_problems": bad, "problems": len(problems)}), file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
