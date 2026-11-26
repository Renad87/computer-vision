"""Review pages for the near-duplicate decisions: each candidate pair side by side, numbered like the CSV.

    python -m data_preparation.review --workdir <W>      # writes <W>/datasets/review/pages/pairs_NNN.png
Needs the images laid out (python -m data_preparation.layout). Pages are working files for the reviewer; they are
never part of the delivery zip. The decision is typed in datasets/review/near_duplicate_decisions.csv.
"""
import argparse
import os
import sys

from .common import PACKAGE_ROOT, read_csv

PER_PAGE = 8
THUMB = 220


def make_pages(workdir, candidates_csv, out_dir):
    from PIL import Image, ImageDraw, ImageOps
    rows = read_csv(candidates_csv)
    os.makedirs(out_dir, exist_ok=True)
    pages = 0
    for start in range(0, len(rows), PER_PAGE):
        chunk = rows[start:start + PER_PAGE]
        page = Image.new("RGB", (2 * THUMB + 420, len(chunk) * (THUMB + 10) + 10), "white")
        d = ImageDraw.Draw(page)
        for k, r in enumerate(chunk):
            y = 10 + k * (THUMB + 10)
            for col, side in enumerate("ab"):
                im = Image.open(os.path.join(workdir, *r[f"image_path_{side}"].split("/"))).convert("RGB")
                im = ImageOps.contain(im, (THUMB, THUMB))
                page.paste(im, (10 + col * (THUMB + 10), y))
            x = 2 * THUMB + 40
            d.text((x, y), f"pair {r['pair_no']}", fill="black")
            d.text((x, y + 20), f"A {r['image_id_a']}  [{r['split_a']}]", fill="black")
            d.text((x, y + 38), f"B {r['image_id_b']}  [{r['split_b']}]", fill="black")
            d.text((x, y + 60), f"pHash {r['phash_hamming']}   CLIP {r['clip_cosine']}   ({r['nominated_by']})",
                   fill="black")
            d.text((x, y + 84), "same_image  or  different ?", fill="gray")
        pages += 1
        page.save(os.path.join(out_dir, f"pairs_{pages:03d}.png"))
    return pages, len(rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", default=PACKAGE_ROOT)
    a = ap.parse_args(argv)
    w = os.path.abspath(a.workdir)
    pages, n = make_pages(w, os.path.join(w, "datasets", "review", "near_duplicate_decisions.csv"),
                          os.path.join(w, "datasets", "review", "pages"))
    print(f"{n} pairs on {pages} pages in datasets/review/pages/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
