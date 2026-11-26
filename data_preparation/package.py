"""Assemble the delivery zip for Omar (task prompt section 19). No images, no inputs, no consent records.

    python -m data_preparation.package v0.9 --workdir <W> [--out Shaden_M2_Dataset_v0.9.zip]

Contents: data_preparation/, tests/data_preparation/, datasets/manifests/ (this version's manifests and
.build.json files), datasets/reports/, datasets/DATASET_CARD.md, evaluation/pv_test/ (protocol and blank sheets
only, if present), HANDOFF.md and SHA256SUMS (SHA-256 of every other file in the zip).
"""
import argparse
import os
import sys
import zipfile

from .common import PACKAGE_ROOT, sha256_bytes

MANIFESTS = {"v0.9": ["manifest_v0.9_emotion"], "v1": ["manifest_v0.9_emotion", "manifest_v1", "pv_test_v1"]}
PRIVATE = ("consent", "originals", "private")


def collect(version, workdir):
    files = {}

    def add_tree(base, prefix, keep=lambda rel: True):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                rel = prefix + os.path.relpath(path, base).replace(os.sep, "/")
                if keep(rel) and not any(p in rel.lower() for p in PRIVATE):
                    files[rel] = path

    add_tree(os.path.join(PACKAGE_ROOT, "data_preparation"), "data_preparation/")
    add_tree(os.path.join(PACKAGE_ROOT, "tests", "data_preparation"), "tests/data_preparation/")
    mdir = os.path.join(workdir, "datasets", "manifests")
    for stem in MANIFESTS[version]:
        for ext in (".jsonl", ".build.json", ".jsonl.sha256"):
            p = os.path.join(mdir, stem + ext)
            if os.path.isfile(p):
                files[f"datasets/manifests/{stem}{ext}"] = p
    add_tree(os.path.join(workdir, "datasets", "reports"), "datasets/reports/",
             keep=lambda rel: not rel.lower().endswith((".png", ".jpg", ".jpeg")))
    files["datasets/DATASET_CARD.md"] = os.path.join(workdir, "datasets", "DATASET_CARD.md")
    pv = os.path.join(workdir, "evaluation", "pv_test")
    if os.path.isdir(pv):
        add_tree(pv, "evaluation/pv_test/", keep=lambda rel: rel.endswith((".md", ".csv")) and "photos" not in rel)
    files["HANDOFF.md"] = os.path.join(workdir, "HANDOFF.md")
    return files


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("version", choices=sorted(MANIFESTS))
    ap.add_argument("--workdir", default=PACKAGE_ROOT)
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    workdir = os.path.abspath(a.workdir)
    out = a.out or os.path.join(workdir, f"Shaden_M2_Dataset_{a.version}.zip")
    files = collect(a.version, workdir)
    sums = []
    with zipfile.ZipFile(out + ".tmp", "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(files):
            with open(files[rel], "rb") as fh:
                data = fh.read()
            sums.append(f"{sha256_bytes(data)}  {rel}")
            info = zipfile.ZipInfo(rel, date_time=(2026, 11, 25, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, data)
        info = zipfile.ZipInfo("SHA256SUMS", date_time=(2026, 11, 25, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        z.writestr(info, "\n".join(sums) + "\n")
    os.replace(out + ".tmp", out)
    with open(out, "rb") as fh:
        digest = sha256_bytes(fh.read())
    with open(out + ".sha256", "w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"{digest}  {os.path.basename(out)}\n")
    print(f"{out}: {len(files) + 1} files, SHA-256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
