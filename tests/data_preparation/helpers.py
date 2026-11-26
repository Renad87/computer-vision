"""Tiny synthetic inputs for the data-preparation tests. Everything is named fixture_* and lives in a temp dir."""
import csv
import io
import os
import zipfile

try:
    from PIL import Image
    import numpy as np
    HAVE_IMAGING = True
except ImportError:  # pragma: no cover
    HAVE_IMAGING = False

SKIP_MSG = "needs Pillow and numpy (data-preparation image checks)"
PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def jpeg_bytes(seed, size=(96, 80), quality=90):
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, size=(8, 8, 3), dtype=np.uint8)
    img = Image.fromarray(base).resize(size, Image.Resampling.BICUBIC)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def recompress(data, quality=60):
    buf = io.BytesIO()
    Image.open(io.BytesIO(data)).convert("RGB").save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def mini_emoset_zip(path, per_split=None, extra=None):
    """emoset/<split>/<emotion>/fixture_<emotion>_<n>.jpg; `extra` = list of (member, bytes)."""
    per_split = per_split or {"train": 2, "val": 1, "test": 1}
    emotions = ["amusement", "awe", "contentment", "excitement", "anger", "disgust", "fear", "sadness"]
    seed = 0
    with zipfile.ZipFile(path, "w") as z:
        for split, n in per_split.items():
            for emo in emotions:
                for i in range(n):
                    seed += 1
                    z.writestr(f"emoset/{split}/{emo}/fixture_{emo}_{split}_{i}.jpg", jpeg_bytes(seed))
        for member, data in extra or []:
            z.writestr(member, data)
    return path


def mini_places_dir(root, rows):
    """rows: list of (folder, file_stem, label, places_class, split). Writes Windows-style paths like the old file."""
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    with open(os.path.join(root, "data", "places_manifest.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["path", "label", "places_class", "io", "split"])
        for k, (folder, stem, label, pc, split) in enumerate(rows):
            d = os.path.join(root, "data", "places365", folder)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, stem + ".jpg"), "wb") as img:
                img.write(jpeg_bytes(1000 + k, size=(64, 64)))
            w.writerow([f"data\\places365\\{folder}\\{stem}.jpg", label, pc, "outdoor", split])
    return root
