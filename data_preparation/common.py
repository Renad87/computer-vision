"""Shared helpers: paths, contract field order, deterministic JSON(L)/CSV writing, hashing, image probing, pHash.

Standard library only, except `probe_image` / `phash64` which need Pillow and numpy (imported lazily).
"""
import csv
import hashlib
import io
import json
import os
import re

PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SCHEMA_VERSION = "1.0.0"
TAXONOMY_VERSION = "1.0.0"
MIN_SIDE = 64                      # contract minimum (width, height >= 64)
SPLIT_ORDER = ["train", "val", "test", "ood_test"]
PROTECTION = {"pv_test": 3, "test": 2, "ood_test": 2, "val": 1, "train": 0}   # quarantine priority (method 6.1)
SOURCE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# Field order of the image_manifest contract (contracts/CONTRACT_FIELDS.md); `fixture` is never written.
FIELD_ORDER = [
    "schema_version", "taxonomy_version", "image_id", "source_dataset", "source_image_id", "image_path",
    "image_sha256", "width", "height", "split", "split_origin", "near_dup_group",
    "scene_label", "scene_label_status", "scene_label_source", "scene_source_raw", "scene_ambiguous",
    "emotion_label", "emotion_label_status", "emotion_label_source",
    "acceptable_img_emotions", "acceptable_lit_emotions", "annotation_provenance", "review_status", "license_terms",
]
OPTIONAL_ABSENT = {"scene_source_raw", "scene_ambiguous", "acceptable_img_emotions", "acceptable_lit_emotions"}

# Licence terms exactly as known (method section 10). Never invent a licence.
LICENSE_EMOSET = ("EmoSet-118K via the Hugging Face mirror Woleek/EmoSet-118K; dataset licence not stated by the "
                  "mirror or the official repository (checked 2026-11-25); internal research use only; images not "
                  "redistributed.")
LICENSE_PLACES = "Places365 terms not verified; internal research use only; images not redistributed"

PROTOCOL_EMOSET = ("EmoSet-118K emotion label (EmoSet paper, ICCV 2023: 10 annotators per image, label kept above "
                   "7 of 10 yes votes). Sample drawn by Renad from the Hugging Face mirror Woleek/EmoSet-118K: "
                   "streaming shuffle seed 42 (buffer 2000), first 600/150/400 images per emotion of the train/val/test "
                   "splits, thumbnails with longer side at most 256 px, JPEG quality 90 (emotion_keras1.ipynb, cell 4).")
PROTOCOL_PLACES = ("Places365 official validation-set category label. Sampled and re-split 60/20/20 (train/val/test) "
                   "per category with seed 42 by prepare_data.py (references/old_visual_module/prepare_data.py); "
                   "OOD categories kept for rejection tests only (ood_test).")


def rel(path, root=PACKAGE_ROOT):
    """Path relative to `root` with forward slashes; the bare file name if it lies outside (never absolute)."""
    ab, root = os.path.abspath(path), os.path.abspath(root)
    if os.path.commonpath([ab, root]) == root:
        return os.path.relpath(ab, root).replace(os.sep, "/")
    return os.path.basename(ab)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def order_record(rec):
    out = {}
    for k in FIELD_ORDER:
        if k in rec:
            out[k] = rec[k]
        elif k not in OPTIONAL_ABSENT:
            raise KeyError(f"record {rec.get('image_id')} misses required field {k}")
    extra = set(rec) - set(FIELD_ORDER)
    if extra:
        raise KeyError(f"unexpected fields {sorted(extra)} in {rec.get('image_id')}")
    return out


def sort_key(rec):
    return (rec["source_dataset"], SPLIT_ORDER.index(rec["split"]), rec["image_id"])


def jsonl_bytes(records):
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    return ("\n".join(lines) + "\n").encode("utf-8") if lines else b""


def write_bytes(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(data)


def write_json(path, obj):
    write_bytes(path, (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def write_jsonl(path, records):
    write_bytes(path, jsonl_bytes(records))


def write_text(path, text):
    write_bytes(path, text.encode("utf-8"))


def write_csv(path, rows, fields):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})
    write_text(path, buf.getvalue())


def read_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return "\n".join(out)


# ------------------------------------------------------------------------------------------------ images
def probe_image(data):
    """Decode check, size, mode, format, luminance statistics. Never modifies the bytes."""
    from PIL import Image
    import numpy as np
    info = {"decodes": False}
    try:
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im.load()
            info.update(decodes=True, format=im.format, mode=im.mode, width=im.width, height=im.height)
            g = np.asarray(im.convert("L").resize((64, 64)), dtype=np.float64) / 255.0
            info.update(mean_luminance=round(float(g.mean()), 4), std_luminance=round(float(g.std()), 4))
    except Exception as e:  # noqa: BLE001
        info["error"] = f"{type(e).__name__}: {e}"
    return info


def _dct_matrix(n):
    import numpy as np
    k = np.arange(n)
    m = np.cos(np.pi * (2 * k[None, :] + 1) * k[:, None] / (2 * n))
    m[0] *= 1 / np.sqrt(2)
    return m * np.sqrt(2 / n)


_DCT32 = None


def phash64(data):
    """64-bit perceptual hash: 32x32 grayscale, 2-D DCT, top-left 8x8 block, median threshold (method 6.2)."""
    global _DCT32
    from PIL import Image
    import numpy as np
    if _DCT32 is None:
        _DCT32 = _dct_matrix(32)
    with Image.open(io.BytesIO(data)) as im:
        g = np.asarray(im.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    d = _DCT32 @ g @ _DCT32.T
    block = d[:8, :8].flatten()
    bits = block > np.median(block)
    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    return f"{value:016x}"


def hamming(a_hex, b_hex):
    return bin(int(a_hex, 16) ^ int(b_hex, 16)).count("1")
