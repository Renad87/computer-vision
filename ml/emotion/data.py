"""EmoSet-118K sampling.

The full dataset is ~30.6 GB, too large to download comfortably in Colab within
the project deadline. We stream the *official* train / val / test splits from
Hugging Face and keep a class-balanced subsample of each, without ever mixing
splits (so the test set stays independent).

Every scanned row (kept or not) is counted, which gives an unbiased estimate of
the natural class distribution for the data report.
"""
from __future__ import annotations

import io
from collections import Counter

from PIL import Image

try:
    from . import config
except ImportError:  # run as a script
    import config


def _decode(image_field, short_side: int):
    """Decode only rows we keep; use JPEG draft mode so 8k-px images are cheap."""
    data = image_field.get("bytes") if isinstance(image_field, dict) else None
    if not data:
        return None
    im = Image.open(io.BytesIO(data))
    try:
        im.draft("RGB", (short_side * 2, short_side * 2))
    except Exception:
        pass
    im = im.convert("RGB")
    w, h = im.size
    s = short_side / min(w, h)
    if s < 1:
        im = im.resize((max(1, round(w * s)), max(1, round(h * s))), Image.BICUBIC)
    return im


def _none_float(v):
    try:
        return float(v) if v is not None else float("nan")
    except (TypeError, ValueError):
        return float("nan")


def stream_balanced(split: str, per_class: int, max_scan: int, seed: int = 42,
                    buffer_size: int = 4000, short_side: int = config.CACHE_SHORT_SIDE):
    """Yield (PIL image, label_idx, meta dict) until every class has `per_class`
    images or `max_scan` rows were read. Returns the scan statistics at the end
    via StopIteration.value (use `collect` below for convenience)."""
    from datasets import Image as HFImage
    from datasets import load_dataset

    ds = load_dataset(config.HF_DATASET, split=split, streaming=True)
    ds = ds.cast_column("image", HFImage(decode=False))
    ds = ds.shuffle(seed=seed, buffer_size=buffer_size)

    # Class names of the integer `label` column, used only as a fallback when
    # the `emotion` column is missing or not a known string.
    label_names = None
    try:
        label_names = [n.lower() for n in ds.features["label"].names]
    except Exception:
        pass

    def resolve(row):
        emo = row.get("emotion")
        if isinstance(emo, int) and label_names:
            emo = label_names[emo]
        emo = str(emo if emo is not None else "").strip().lower()
        if emo not in config.CLASS_TO_IDX and label_names and isinstance(row.get("label"), int):
            emo = label_names[row["label"]]
        return emo

    kept = Counter()
    scanned = Counter()
    unknown = Counter()
    n_scanned = 0
    n_decode_fail = 0
    for row in ds:
        n_scanned += 1
        emo = resolve(row)
        if n_scanned == 2000 and not scanned:
            raise RuntimeError(f"No known emotion labels in the first 2000 rows of '{split}'. "
                               f"Seen values: {dict(unknown.most_common(5))}. Check the dataset schema.")
        if emo not in config.CLASS_TO_IDX:
            unknown[emo] += 1
        else:
            scanned[emo] += 1
            if kept[emo] < per_class:
                try:
                    im = _decode(row["image"], short_side)
                except Exception:
                    im = None
                if im is None:
                    n_decode_fail += 1
                else:
                    kept[emo] += 1
                    meta = {
                        "image_id": str(row.get("image_id", "")),
                        "ds_brightness": _none_float(row.get("brightness")),
                        "ds_colorfulness": _none_float(row.get("colorfulness")),
                        "scene": str(row.get("scene") or ""),
                        "facial_expression": str(row.get("facial_expression") or ""),
                    }
                    yield im, config.CLASS_TO_IDX[emo], meta
        if all(kept[c] >= per_class for c in config.TRAINED_CLASSES) or n_scanned >= max_scan:
            break
        if n_scanned % 5000 == 0:
            print(f"  [{split}] scanned={n_scanned:,} kept={sum(kept.values()):,} "
                  f"min_class={min(kept[c] for c in config.TRAINED_CLASSES)}", flush=True)

    return {
        "split": split,
        "rows_scanned": n_scanned,
        "scanned_per_class": {c: scanned[c] for c in config.TRAINED_CLASSES},
        "kept_per_class": {c: kept[c] for c in config.TRAINED_CLASSES},
        "unknown_labels": dict(unknown),
        "decode_failures": n_decode_fail,
        "quota_per_class": per_class,
        "complete": all(kept[c] >= per_class for c in config.TRAINED_CLASSES),
    }
