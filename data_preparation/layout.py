"""Lay the delivered images out under datasets/images/, byte for byte (no re-encoding, resizing or renaming).

    python -m data_preparation.layout [--workdir DIR] [--emoset-zip PATH] [--places-dir PATH]

EmoSet:    emoset.zip member emoset/<split>/<emotion>/<id>.jpg -> datasets/images/emoset/<split>/<emotion>/<id>.jpg
Places365: <places-dir>/data/places365/<folder>/<file>.jpg      -> datasets/images/places365/<folder>/<file>.jpg
Existing files with the same bytes are left alone; a different file at a target path stops the layout.
"""
import argparse
import os
import shutil
import sys
import zipfile

from .common import PACKAGE_ROOT, sha256_bytes, sha256_file


def _place(data, target):
    if os.path.exists(target):
        if sha256_file(target) != sha256_bytes(data):
            raise SystemExit(f"STOP: {target} exists with different bytes")
        return False
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "wb") as fh:
        fh.write(data)
    return True


def layout_emoset(zip_path, root):
    n = 0
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(z.namelist()):
            if name.endswith("/") or not name.startswith("emoset/"):
                continue
            n += _place(z.read(name), os.path.join(root, "datasets", "images", *name.split("/")))
    return n


def layout_places(places_dir, root):
    src_root = os.path.join(places_dir, "data", "places365")
    n = 0
    for folder in sorted(os.listdir(src_root)):
        for fname in sorted(os.listdir(os.path.join(src_root, folder))):
            src = os.path.join(src_root, folder, fname)
            target = os.path.join(root, "datasets", "images", "places365", folder, fname)
            if os.path.exists(target):
                if sha256_file(target) != sha256_file(src):
                    raise SystemExit(f"STOP: {target} exists with different bytes")
                continue
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copyfile(src, target)          # byte copy
            n += 1
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", default=PACKAGE_ROOT, help="folder holding external/ and datasets/")
    ap.add_argument("--emoset-zip", default=None, help="default: <workdir>/external/renad/emoset.zip")
    ap.add_argument("--places-dir", default=None, help="default: <workdir>/external/shaden_visual")
    a = ap.parse_args(argv)
    a.root = os.path.abspath(a.workdir)
    a.emoset_zip = a.emoset_zip or os.path.join(a.root, "external", "renad", "emoset.zip")
    a.places_dir = a.places_dir or os.path.join(a.root, "external", "shaden_visual")
    if os.path.exists(a.emoset_zip):
        print("emoset: placed", layout_emoset(a.emoset_zip, a.root), "new files")
    else:
        print("emoset: input not found, skipped:", a.emoset_zip)
    if os.path.isdir(os.path.join(a.places_dir, "data", "places365")):
        print("places365: placed", layout_places(a.places_dir, a.root), "new files")
    else:
        print("places365: input not found, skipped:", a.places_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
