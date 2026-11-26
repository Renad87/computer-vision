"""Coverage of the pilot scene-emotion matrix, measured from the poetry records themselves.

    python3 -m poetry_corpus.tools.coverage [--mode development] [--target 8] [--json]

The pilot matrix is the taxonomy's `pilot` block (5 scene groups x 5 literary emotions). A record counts for
the cell (scene group G, literary emotion E) when it is displayable in the chosen mode (contracts.validate.
display_allowed) and, following docs/RETRIEVAL_METHOD.md sections 3-4:

- tier 1: E is a primary emotion of the record and the record relates to G by relation.literal or
  relation.scene_association. This is the number compared with the per-cell target, counted as distinct
  poems because the engine returns at most one verse per poem;
- secondary: E is a secondary emotion with the same tier-1 relation (eligible with E = 0.6, reported apart);
- symbolic: E is primary and the relation to G is relation.symbolic (tier 2, only when the user allows it).

The poem key is (poet, meter, rhyme) for every record (guidelines/poem_identity.md).
The per-cell target is provisional: docs/SPEC.md sets about 1,000 verses over P1-P3 but no number per cell.
"""
import argparse
import collections
import glob
import json
import os
import sys

from contracts.taxonomy import load_taxonomy
from contracts.validate import display_allowed, load_jsonl

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RECORDS_DIR = os.path.join(ROOT, "poetry_corpus", "records")
TIER1_RELATIONS = ("relation.literal", "relation.scene_association")
DEFAULT_TARGET = 8  # provisional per-cell target (distinct poems at tier 1); see the module docstring


def record_files(records_dir=RECORDS_DIR):
    """Every record file of the corpus (P0 first, then the batches in name order)."""
    return sorted(glob.glob(os.path.join(records_dir, "*.jsonl")))


def load_records(paths):
    """Return [(path, record)] in file order; unreadable lines raise SystemExit."""
    out = []
    for path in paths:
        records, issues = load_jsonl(path)
        if issues:
            raise SystemExit(f"{path}: {'; '.join(str(i) for i in issues)}")
        out.extend((path, r) for _, r in records)
    return out


def poem_key(record):
    """(poet, meter, rhyme) as in APCD, for every record. poem_id is not used: a poem may have one verse
    verified in the history KB (poem_id set) and another apcd_only (no poem_id), and the two must count once.
    See poetry_corpus/guidelines/poem_identity.md."""
    source = record.get("source") or {}
    return ((record.get("poet") or {}).get("name_apcd"), source.get("meter_apcd"), source.get("rhyme_apcd"))


def pilot_cells(taxonomy):
    pilot = taxonomy.pilot
    return [(g, e) for g in pilot["scene_groups"] for e in pilot["lit_emotions"]]


def cell_members(records, taxonomy, mode="development"):
    """{(group, emotion): {"tier1": [...], "secondary": [...], "symbolic": [...]}} of displayable records."""
    cells = collections.defaultdict(lambda: {"tier1": [], "secondary": [], "symbolic": []})
    for record in records:
        if not display_allowed(record, mode) or record.get("emotion_status") != "has_emotion":
            continue
        primary = [e["id"] for e in record["emotions"]["primary"]]
        secondary = [e["id"] for e in record["emotions"]["secondary"]]
        for assoc in record.get("visual_associations") or []:
            target, relation = assoc["target"], assoc["relation"]
            if taxonomy.layer(target) != "scene_group":
                continue
            if relation in TIER1_RELATIONS:
                for emotion in primary:
                    cells[(target, emotion)]["tier1"].append(record)
                for emotion in secondary:
                    cells[(target, emotion)]["secondary"].append(record)
            elif relation == "relation.symbolic":
                for emotion in primary:
                    cells[(target, emotion)]["symbolic"].append(record)
    return cells


def summarize(records, taxonomy, mode="development", target=DEFAULT_TARGET):
    """Per-cell counts for the pilot matrix plus the cells outside it that already have tier-1 records."""
    cells = cell_members(records, taxonomy, mode)
    pilot = set(pilot_cells(taxonomy))

    def stats(key):
        block = cells.get(key) or {"tier1": [], "secondary": [], "symbolic": []}
        tier1 = block["tier1"]
        return {
            "tier1_records": len(tier1),
            "tier1_poems": len({poem_key(r) for r in tier1}),
            "tier1_poets": len({r["poet"]["name_apcd"] for r in tier1}),
            "secondary_records": len(block["secondary"]),
            "symbolic_records": len(block["symbolic"]),
            "tier1_verse_ids": sorted(r["verse_id"] for r in tier1),
        }

    matrix = {f"{g}|{e}": stats((g, e)) for g, e in pilot_cells(taxonomy)}
    outside = {f"{g}|{e}": stats((g, e)) for (g, e), block in sorted(cells.items())
               if (g, e) not in pilot and block["tier1"]}
    gaps = {key: target - s["tier1_poems"] for key, s in matrix.items() if s["tier1_poems"] < target}
    displayable = [r for r in records if display_allowed(r, mode)]
    return {
        "mode": mode,
        "target_tier1_poems_per_cell": target,
        "records": len(records),
        "displayable_records": len(displayable),
        "pilot_cells": len(matrix),
        "pilot_cells_at_target": len(matrix) - len(gaps),
        "pilot_cells_empty": sum(1 for s in matrix.values() if s["tier1_poems"] == 0),
        "pilot_gap_total": sum(gaps.values()),
        "matrix": matrix,
        "gaps": gaps,
        "outside_pilot": outside,
    }


def matrix_table(summary, taxonomy, field="tier1_poems"):
    """Markdown table: rows are pilot scene groups, columns pilot literary emotions."""
    pilot = taxonomy.pilot
    names = lambda i: taxonomy.labels[i]["name_ar"]
    lines = ["| المجموعة | " + " | ".join(names(e) for e in pilot["lit_emotions"]) + " |",
             "|---" * (len(pilot["lit_emotions"]) + 1) + "|"]
    for g in pilot["scene_groups"]:
        cells = [str(summary["matrix"][f"{g}|{e}"][field]) for e in pilot["lit_emotions"]]
        lines.append(f"| {names(g)} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--records-dir", default=RECORDS_DIR)
    parser.add_argument("--mode", default="development", choices=("production", "development"))
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--json", action="store_true", help="print the full summary as JSON")
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    records = [r for _, r in load_records(record_files(args.records_dir))]
    summary = summarize(records, taxonomy, args.mode, args.target)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    print(f"records {summary['records']}, displayable in {args.mode} mode {summary['displayable_records']}")
    print(f"pilot cells at target ({args.target} tier-1 poems): {summary['pilot_cells_at_target']}/25, "
          f"empty {summary['pilot_cells_empty']}, missing {summary['pilot_gap_total']}")
    print(matrix_table(summary, taxonomy))
    return 0


if __name__ == "__main__":
    sys.exit(main())
