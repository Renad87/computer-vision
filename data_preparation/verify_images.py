"""Check that every image_path of a manifest exists under the package root and that its SHA-256 matches.

    python -m data_preparation.verify_images datasets/manifests/manifest_v0.9_emotion.jsonl [--workdir DIR]
Exit 0 = all present and identical.
"""
import json
import os
import sys

from .common import PACKAGE_ROOT, sha256_file


def verify(manifest, root=PACKAGE_ROOT):
    missing, mismatch, n = [], [], 0
    with open(manifest, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            n += 1
            path = os.path.join(root, *r["image_path"].split("/"))
            if not os.path.isfile(path):
                missing.append(r["image_path"])
            elif sha256_file(path) != r["image_sha256"]:
                mismatch.append(r["image_path"])
    return n, missing, mismatch


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("--workdir", default=PACKAGE_ROOT, help="folder that holds datasets/images/")
    a = ap.parse_args(argv)
    n, missing, mismatch = verify(a.manifest, os.path.abspath(a.workdir))
    print(f"{n} records; missing images: {len(missing)}; SHA-256 mismatches: {len(mismatch)}")
    for p in (missing + mismatch)[:20]:
        print("  ", p)
    return 0 if not missing and not mismatch else 1


if __name__ == "__main__":
    sys.exit(main())
