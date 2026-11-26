"""Independent AI quality audit: draw a stratified sample of merged P2 records with their poem context.

    python3 -m poetry_corpus.tools.qa_sample --out SAMPLE.jsonl [--per-batch 8] [--seed 20261126] [--parts 3]

The sample is deterministic (fixed seed) and stratified by batch. Each line holds the record's verse id, text,
poet, era, labels and up to two neighbouring APCD rows of the same poet on each side. Auditors (AI agents, not
human reviewers) write findings to separate files; findings never change review.status. With --parts N the
sample is split into N disjoint files SAMPLE.partK.jsonl for parallel auditors.
"""
import argparse
import json
import os
import random
import sys

from contracts import apcd

from .coverage import RECORDS_DIR, load_records, record_files


def sample(per_batch=8, seed=20261126):
    rng = random.Random(seed)
    picked = []
    for path in record_files():
        name = os.path.basename(path)
        if not name.startswith("p2_"):
            continue
        records = [r for _, r in load_records([path])]
        picked.extend((name.replace("_ai_drafts_v1.jsonl", ""), r)
                      for r in rng.sample(records, min(per_batch, len(records))))
    need = {n for _, r in picked for n in range(max(0, r["apcd_row"] - 2), r["apcd_row"] + 3)}
    rows = apcd.get_rows(need)
    out = []
    for batch, r in picked:
        context = [[n, rows[n][apcd.VERSE]] for n in range(r["apcd_row"] - 2, r["apcd_row"] + 3)
                   if n != r["apcd_row"] and n in rows and rows[n][apcd.POET] == r["poet"]["name_apcd"]]
        out.append({"verse_id": r["verse_id"], "batch": batch, "text": r["text_original"],
                    "poet": r["poet"]["name_apcd"], "era": r["era_apcd"], "context": context,
                    "primary": [[e["id"], e["basis"], (e.get("evidence_span") or {}).get("text"), e.get("justification_ar")]
                                for e in r["emotions"]["primary"]],
                    "secondary": [[e["id"], e["basis"], (e.get("evidence_span") or {}).get("text"), e.get("justification_ar")]
                                  for e in r["emotions"]["secondary"]],
                    "visual": [[a["target"], a["relation"], (a.get("evidence_span") or {}).get("text"), a.get("justification_ar")]
                               for a in r["visual_associations"]],
                    "meaning": r["meaning_ar"], "uncertainty": r["annotator_uncertainty"]})
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", required=True)
    parser.add_argument("--per-batch", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261126)
    parser.add_argument("--parts", type=int, default=1)
    args = parser.parse_args(argv)
    items = sample(args.per_batch, args.seed)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in items)
    if args.parts > 1:
        base, ext = os.path.splitext(args.out)
        for k in range(args.parts):
            with open(f"{base}.part{k + 1}{ext}", "w", encoding="utf-8") as fh:
                fh.writelines(json.dumps(x, ensure_ascii=False) + "\n" for x in items[k::args.parts])
    print(json.dumps({"sampled": len(items), "parts": args.parts}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
