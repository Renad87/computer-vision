"""Candidate discovery over APCD for one (visual target, literary emotion) cell.

    python3 -m retrieval.discover --cell scene_group.desert:lit_emotion.longing \
        --apcd-extract handoff/mohammed_m5/data/apcd/apcd_extract_v1.csv --limit 200 --out candidates.csv
    python3 -m retrieval.discover --cell tag.moon:lit_emotion.awe --apcd-zip PATH --limit 200 --out candidates.csv

Output columns: apcd_row, poet, era, text, matched_terms, hint_labels, hint_source.

- A verse is a candidate when its preprocessed tokens contain a query term of the visual target (taxonomy
  `query_terms_ar`, same preprocessing). Order: number of distinct matched terms (descending), then apcd_row.
- The emotion cannot be read from word matches: it is the cell a human is looking for, never a label.
- Candidates are suggestions for human selection and annotation. This tool never writes a corpus, and APCD is
  never a recommendation corpus. Text and metadata are copied verbatim from the APCD row.
"""
import argparse
import csv
import heapq
import sys

from contracts import apcd
from contracts.taxonomy import load_taxonomy

from .preprocess import DEFAULT_VARIANT, VARIANTS, tokenize

COLUMNS = ("apcd_row", "poet", "era", "text", "matched_terms", "hint_labels", "hint_source")


def parse_cell(cell, taxonomy):
    try:
        target, emotion = cell.split(":")
    except ValueError:
        raise ValueError("--cell must look like scene_group.desert:lit_emotion.longing")
    if taxonomy.layer(target) not in ("scene_group", "tag") or not (taxonomy.labels[target].get("query_terms_ar")):
        raise ValueError(f"{target}: not a scene group or exposed tag with query terms")
    if taxonomy.layer(emotion) != "lit_emotion":
        raise ValueError(f"{emotion}: not a literary emotion id")
    return target, emotion


def term_index(target, taxonomy, variant):
    """{normalized token: original taxonomy term}."""
    out = {}
    for term in taxonomy.labels[target]["query_terms_ar"]:
        for tok in tokenize(term, variant):
            out.setdefault(tok, term)
    return out


def iter_extract(path):
    """(apcd_row, row of the 8 APCD columns) from an extract CSV with an extra leading `apcd_row` column."""
    with open(path, encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if header[0] != "apcd_row" or tuple(header[1:]) != apcd.COLUMNS:
            raise ValueError(f"{path}: unexpected header {header!r}")
        for row in reader:
            yield int(row[0]), row[1:]


def discover(rows, target, emotion, taxonomy, variant=DEFAULT_VARIANT, limit=200, exclude_rows=()):
    terms = term_index(target, taxonomy, variant)
    exclude = set(exclude_rows)
    heap = []  # keep the best `limit` as a min-heap on (n_matched, -row)
    for row_number, row in rows:
        if row_number in exclude:
            continue
        verse = row[apcd.VERSE]
        matched = sorted({terms[t] for t in tokenize(verse, variant) if t in terms})
        if not matched:
            continue
        entry = (len(matched), -row_number, row, matched)
        if len(heap) < limit:
            heapq.heappush(heap, entry)
        elif entry[:2] > heap[0][:2]:
            heapq.heapreplace(heap, entry)
    best = sorted(heap, key=lambda e: (-e[0], -e[1]))
    return [{
        "apcd_row": -neg_row,
        "poet": row[apcd.POET],
        "era": row[apcd.ERA],
        "text": row[apcd.VERSE],
        "matched_terms": "|".join(matched),
        "hint_labels": target,
        "hint_source": f"query_terms_ar:{variant}; emotion {emotion} not inferred, for human judgment",
    } for _, neg_row, row, matched in best]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--cell", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--apcd-extract")
    source.add_argument("--apcd-zip")
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--variant", choices=VARIANTS, default=DEFAULT_VARIANT)
    parser.add_argument("--exclude-corpus", help="poetry_record JSONL whose apcd_rows are skipped")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    try:
        target, emotion = parse_cell(args.cell, taxonomy)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    exclude = []
    if args.exclude_corpus:
        from .engine import load_corpus
        exclude = [r["apcd_row"] for r in load_corpus(args.exclude_corpus)]
    rows = iter_extract(args.apcd_extract) if args.apcd_extract else apcd.iter_rows(args.apcd_zip)
    found = discover(rows, target, emotion, taxonomy, args.variant, args.limit, exclude)
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(found)
    print(f"{len(found)} candidates -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
