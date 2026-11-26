"""Workbook version of the priority_v2 review sheet, in the same format as the priority_v1 package.

    python3 -m poetry_corpus.review_packages.priority_v2.make_xlsx

Reads the 24 ids from priority_v2_manifest.json and builds the rows and the workbook with the priority_v1 builder
(stdlib xlsx writer, dropdown validation, instructions and emotion sheets). Every decision cell stays empty.
"""
import os
import sys

from contracts.taxonomy import load_taxonomy
from contracts.validate import load_jsonl
from poetry_corpus.review.build_priority_review import CORPUS, SCOPE_BOTH, SCOPE_VISUAL, build_rows, write_workbook

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "Poetry_Review_Priority_v2_24.xlsx")
RETURN_NAME = "review_priority_v2_v1.xlsx"


def main():
    import json
    manifest = json.load(open(os.path.join(HERE, "priority_v2_manifest.json"), encoding="utf-8"))
    records, issues = load_jsonl(CORPUS)
    if issues:
        sys.exit(f"corpus unreadable: {issues[0]}")
    by_id = {r["verse_id"]: r for _, r in records}
    taxonomy = load_taxonomy()
    chosen = []
    for row in manifest["rows"]:
        r = by_id[row["verse_id"]]
        scope = SCOPE_VISUAL if row["scope"] == "visual_only" else SCOPE_BOTH
        chosen.append((r, row["group"], scope))
    rows = build_rows(chosen, taxonomy)
    for row, (r, _, _) in zip(rows, chosen):
        assert row["text_original"] == r["text_original"]
        assert not any(row[f] for f in ("decision", "corrected_primary", "corrected_secondary", "visual_decision", "note"))
    write_workbook(rows, taxonomy, OUT, RETURN_NAME)
    print(len(rows), "rows ->", OUT)


if __name__ == "__main__":
    main()
