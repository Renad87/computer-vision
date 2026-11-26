"""Build a small, reproducible data sample instead of downloading full datasets.

1. Places365 (official validation images, 256px, 100 per category) via a Hugging Face
   mirror with one folder per category. Only the categories mapped in taxonomy.json are
   fetched, plus a set of out-of-taxonomy categories used to test rejection (`supported`).
   The pool is re-split 60/20/20 (train/val/test), stratified by Places365 category.
2. Open Images V7 human-verified image-level labels (validation + test subsets). For each
   visual tag we sample verified positives and verified negatives and download only those
   images (resized to 640px). The pool is split 40/60 into calibration/test by image id.

Usage:  python ml/visual/prepare_data.py
Raw label files must already exist in data/raw (see docs/visual_methodology.md).
"""
import csv
import hashlib
import io
import json
import math
import random
import sys
import time
import urllib.request
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RAW = DATA / "raw"
TAX = json.loads((ROOT / "taxonomy.json").read_text(encoding="utf-8"))

HF_REPO = "https://huggingface.co/datasets/rumenguin/places365-val"
OI_URL = "https://open-images-dataset.s3.amazonaws.com/{subset}/{image_id}.jpg"

SEED = 42
MAX_PER_SCENE = 300      # cap per macro scene class (spread evenly over its Places365 categories)
OOD_PER_CLASS = 30
OI_POS, OI_NEG = 60, 60  # per tag, verified positives / verified negatives


def fetch(url, retries=4, timeout=60):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "visual-research-script"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                print("FAILED", url, e, file=sys.stderr)
                return None
            time.sleep(1.5 * (i + 1))


def list_hf_folder(folder):
    data = fetch(f"https://huggingface.co/api/datasets/rumenguin/places365-val/tree/main/images/{folder}")
    return sorted(f["path"] for f in json.loads(data) if f["path"].endswith(".jpg"))


def io_labels():
    out = {}
    for line in (RAW / "places365" / "IO_places365.txt").read_text().splitlines():
        name, v = line.rsplit(" ", 1)
        out[name[3:]] = "indoor" if v == "1" else "outdoor"
    return out


def save_places(path):
    dst = DATA / "places365" / Path(path).relative_to("images")
    if dst.exists():
        return str(dst.relative_to(ROOT)), True
    blob = fetch(f"{HF_REPO}/resolve/main/{path}")
    if blob is None:
        return None, False
    Image.open(io.BytesIO(blob)).convert("RGB")  # validate
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(blob)
    return str(dst.relative_to(ROOT)), True


def build_places():
    rng = random.Random(SEED)
    io_map = io_labels()
    jobs = []  # (path, scene_id, places_class, split)
    for sc in TAX["scenes"]:
        k = len(sc["places365"])
        per_sub = min(100, math.ceil(MAX_PER_SCENE / k))
        for pc in sc["places365"]:
            files = list_hf_folder(pc.replace("/", "-"))
            rng.shuffle(files)
            files = files[:per_sub]
            n = len(files)
            n_tr, n_va = int(round(n * 0.6)), int(round(n * 0.2))
            for i, f in enumerate(files):
                split = "train" if i < n_tr else ("val" if i < n_tr + n_va else "test")
                jobs.append((f, sc["id"], pc, split))
    for pc in TAX["ood_places365"]:
        files = list_hf_folder(pc.replace("/", "-"))
        rng.shuffle(files)
        for f in files[:OOD_PER_CLASS]:
            jobs.append((f, "__ood__", pc, "test"))
    # training-only background ("other") class, disjoint from the OOD test categories
    for pc in TAX.get("background_places365", []):
        files = list_hf_folder(pc.replace("/", "-"))
        rng.shuffle(files)
        files = files[:OOD_PER_CLASS]
        for i, f in enumerate(files):
            split = "train" if i < 18 else ("val" if i < 24 else "test")
            jobs.append((f, "__other__", pc, split))
    print(f"Places365: downloading {len(jobs)} images")
    with ThreadPoolExecutor(24) as ex:
        res = list(ex.map(lambda j: save_places(j[0]), jobs))
    rows = []
    for (f, sid, pc, split), (p, ok) in zip(jobs, res):
        if ok and p:
            rows.append({"path": p, "label": sid, "places_class": pc, "io": io_map[pc], "split": split})
    with open(DATA / "places_manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Places365 manifest: {len(rows)} rows")


def save_oi(subset, image_id):
    dst = DATA / "openimages" / f"{image_id}.jpg"
    if dst.exists():
        return True
    blob = fetch(OI_URL.format(subset=subset, image_id=image_id))
    if blob is None:
        return False
    try:
        im = Image.open(io.BytesIO(blob)).convert("RGB")
    except Exception:  # noqa: BLE001
        return False
    im.thumbnail((640, 640))
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst, quality=90)
    return True


def build_openimages():
    rng = random.Random(SEED)
    names = {r[0]: r[1] for r in csv.reader(open(RAW / "openimages" / "class-descriptions.csv", encoding="utf-8"))}
    wanted = set()
    for t in TAX["tags"]:
        wanted.update(t["oi"])
    wanted.update(TAX["yolo_eval_oi"].values())
    mid2name = {m: n for m, n in names.items() if n in wanted}

    labels = defaultdict(dict)   # image_id -> {oi_name: 0/1}
    subset_of = {}
    for subset, fname in [("validation", "val-imagelabels.csv"), ("test", "test-imagelabels.csv")]:
        with open(RAW / "openimages" / fname, encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                n = mid2name.get(r["LabelName"])
                if n is None:
                    continue
                v = 1 if float(r["Confidence"]) >= 0.5 else 0
                # positive wins if the same name appears twice (e.g. two MIDs)
                labels[r["ImageID"]][n] = max(v, labels[r["ImageID"]].get(n, 0))
                subset_of[r["ImageID"]] = subset

    groups = [(t["id"], t["oi"]) for t in TAX["tags"]] + [(f"yolo:{k}", [v]) for k, v in TAX["yolo_eval_oi"].items()]
    chosen = set()
    for gid, oi_names in groups:
        pos = sorted(i for i, d in labels.items() if any(d.get(n) == 1 for n in oi_names))
        neg = sorted(i for i, d in labels.items()
                     if any(d.get(n) == 0 for n in oi_names) and not any(d.get(n) == 1 for n in oi_names))
        rng.shuffle(pos)
        rng.shuffle(neg)
        chosen.update(pos[:OI_POS])
        chosen.update(neg[:OI_NEG])
        print(f"  {gid:18s} available pos={len(pos):5d} neg={len(neg):5d}")
    chosen = sorted(chosen)
    print(f"Open Images: downloading {len(chosen)} images")
    with ThreadPoolExecutor(32) as ex:
        ok = list(ex.map(lambda i: save_oi(subset_of[i], i), chosen))
    rows = []
    for i, good in zip(chosen, ok):
        if not good:
            continue
        h = int(hashlib.md5(i.encode()).hexdigest(), 16) % 100
        rows.append({"path": f"data/openimages/{i}.jpg", "image_id": i, "oi_subset": subset_of[i],
                     "split": "calib" if h < 40 else "test", "labels": json.dumps(labels[i], ensure_ascii=False)})
    with open(DATA / "openimages_manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Open Images manifest: {len(rows)} rows")


if __name__ == "__main__":
    which = sys.argv[1:] or ["places", "openimages"]
    if "places" in which:
        build_places()
    if "openimages" in which:
        build_openimages()
