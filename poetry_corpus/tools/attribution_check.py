"""Find corpus verses whose hemistich also appears under another poet anywhere in APCD (attribution conflict).

    python3 -m poetry_corpus.tools.attribution_check [--json]

Hemistichs are compared after folding diacritics, hamza/alef/ya/ta-marbuta spelling and dropping a leading
conjunction و/ف, so small variants (وللدنيا / للدنيا) still match. One APCD pass. A verse with such a
match has uncertain attribution and is excluded from new batches (merge_worker drops it).
"""
import argparse
import collections
import json
import sys

from contracts import apcd

from .coverage import load_records, record_files
from .find_candidates import fold


def norm(text):
    words = fold(text).split()
    words = [w[1:] if len(w) > 3 and w[0] in "وف" else w for w in words]
    return "".join(words)


def words(text):
    out = set()
    for w in fold(text).split():
        if len(w) > 3 and w[0] in "وف":
            w = w[1:]
        if len(w) > 4 and w.startswith("ال"):
            w = w[2:]
        out.add(w)
    return out


def similar(a, b, threshold=0.75):
    """Near-variant verses: most words shared after folding and dropping و/ف and the article."""
    wa, wb = words(a), words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= threshold


COMMENTARIES = ("معجز أحمد",)  # al-Ma'arri's commentary reproduces al-Mutanabbi's verses: not a rival attribution


def conflicts(records, zip_path=None):
    """{verse_id: {"full_verse": [(row, poet)], "one_hemistich": [(row, poet)]}}.
    full_verse = both hemistichs under another poet in the same row: an attribution conflict.
    one_hemistich = a quotation, emulation or shared formula: reported, not an attribution conflict."""
    index = collections.defaultdict(list)
    for r in records:
        h = r.get("hemistichs") or {}
        for side in ("shatr_right", "shatr_left"):
            key = norm(h.get(side) or "")
            if len(key) >= 8:
                index[key].append(r)
    found = collections.defaultdict(lambda: {"full_verse": set(), "one_hemistich": set()})
    for number, row in apcd.iter_rows(zip_path):
        keys = [norm(row[apcd.SHATR_RIGHT]), norm(row[apcd.SHATR_LEFT])]
        hit = collections.Counter(r["verse_id"] for k in keys for r in index.get(k, ()))
        if not hit:
            continue
        by_id = {r["verse_id"]: r for k in keys for r in index.get(k, ())}
        for vid, n in hit.items():
            r = by_id[vid]
            if row[apcd.POET] == r["poet"]["name_apcd"] or row[apcd.POET] in COMMENTARIES:
                continue
            full = n >= 2 or similar(row[apcd.VERSE], r["text_original"])
            found[vid]["full_verse" if full else "one_hemistich"].add((number, row[apcd.POET]))
    return {vid: {k: sorted(v) for k, v in d.items()} for vid, d in found.items()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    records = [r for _, r in load_records(record_files())]
    result = conflicts(records)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=1))
    else:
        full = {v: d["full_verse"] for v, d in result.items() if d["full_verse"]}
        for vid, hits in sorted(full.items()):
            print("FULL", vid, hits[:4])
        print(f"{len(full)} full-verse attribution conflict(s); "
              f"{sum(1 for d in result.values() if d['one_hemistich'] and not d['full_verse'])} one-hemistich "
              "quotation(s)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
