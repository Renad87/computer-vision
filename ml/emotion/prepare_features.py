"""Step 1 — Data preparation and feature extraction.

For each official split (train / val / test) of EmoSet-118K:
  1. stream a class-balanced subsample (see data.py)
  2. cache every kept image as a small JPEG (shorter side 256 px) so that
     fine-tuning and the ambiguity figures never need to re-download
  3. extract frozen CLIP embeddings (shared encoder) and ResNet50 embeddings
     (comparison backbone), plus hand-crafted visual attributes
Also builds the CLIP text embeddings for zero-shot prompts and writes a data
report with the class distribution plots.

Usage (Colab, GPU):
    python ml/emotion/prepare_features.py
    python ml/emotion/prepare_features.py --per_class_train 800 --skip_resnet   # faster
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from attributes import attribute_vector  # noqa: E402
from data import stream_balanced  # noqa: E402


def extract_split(split, per_class, max_scan, args, clip_enc, resnet_enc):
    cache_dir = os.path.join(args.cache_dir, split)
    os.makedirs(cache_dir, exist_ok=True)

    clip_feats, resnet_feats, attrs, labels, paths = [], [], [], [], []
    metas = {k: [] for k in ["image_id", "ds_brightness", "ds_colorfulness", "scene", "facial_expression"]}
    batch_imgs = []

    def flush():
        if not batch_imgs:
            return
        clip_feats.append(clip_enc.encode(batch_imgs))
        if resnet_enc is not None:
            resnet_feats.append(resnet_enc.encode(batch_imgs))
        batch_imgs.clear()

    t0 = time.time()
    gen = stream_balanced(split, per_class, max_scan, seed=args.seed, buffer_size=args.buffer)
    i = 0
    while True:
        try:
            im, y, meta = next(gen)
        except StopIteration as stop:
            stats = stop.value
            break
        rel = os.path.join(split, f"{i:06d}.jpg")
        im.save(os.path.join(args.cache_dir, rel), quality=90)
        paths.append(rel)
        labels.append(y)
        attrs.append(attribute_vector(im))
        for k in metas:
            metas[k].append(meta[k])
        batch_imgs.append(im)
        i += 1
        if len(batch_imgs) >= args.batch_size:
            flush()
    flush()

    out = {
        "clip": np.concatenate(clip_feats) if clip_feats else np.zeros((0, clip_enc.dim), np.float32),
        "labels": np.array(labels, dtype=np.int64),
        "attributes": np.stack(attrs) if attrs else np.zeros((0, len(config.ATTRIBUTE_KEYS)), np.float32),
        "paths": np.array(paths),
        "ds_brightness": np.array(metas["ds_brightness"], dtype=np.float32),
        "ds_colorfulness": np.array(metas["ds_colorfulness"], dtype=np.float32),
        "image_id": np.array(metas["image_id"]),
        "scene": np.array(metas["scene"]),
        "facial_expression": np.array(metas["facial_expression"]),
    }
    if resnet_enc is not None:
        out["resnet"] = np.concatenate(resnet_feats) if resnet_feats else np.zeros((0, 2048), np.float32)
    np.savez_compressed(os.path.join(args.features_dir, f"{split}.npz"), **out)

    stats["seconds"] = round(time.time() - t0, 1)
    stats["n_kept"] = int(len(labels))
    print(f"[{split}] kept {len(labels):,} images in {stats['seconds']}s "
          f"(scanned {stats['rows_scanned']:,}); complete={stats['complete']}", flush=True)
    return stats


def plot_distribution(report, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 4.5))
    for ax, split in zip(axes, ["train", "val", "test"]):
        s = report["splits"].get(split)
        if not s:
            continue
        scanned = np.array([s["scanned_per_class"][c] for c in config.TRAINED_CLASSES], float)
        share = scanned / max(scanned.sum(), 1)
        ax.bar(config.TRAINED_CLASSES, share, color="#4C72B0")
        ax.set_title(f"{split}: natural class share in {s['rows_scanned']:,} scanned rows")
        ax.set_ylabel("share")
        ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model_name", default=config.DEFAULT_CLIP)
    ap.add_argument("--features_dir", default=config.DEFAULT_FEATURES_DIR)
    ap.add_argument("--cache_dir", default=config.DEFAULT_CACHE_DIR)
    ap.add_argument("--results_dir", default=config.DEFAULT_RESULTS_DIR)
    ap.add_argument("--per_class_train", type=int, default=config.DEFAULT_PER_CLASS["train"])
    ap.add_argument("--per_class_val", type=int, default=config.DEFAULT_PER_CLASS["val"])
    ap.add_argument("--per_class_test", type=int, default=config.DEFAULT_PER_CLASS["test"])
    ap.add_argument("--splits", nargs="+", default=["train", "val", "test"])
    ap.add_argument("--batch_size", type=int, default=128)
    ap.add_argument("--buffer", type=int, default=4000, help="streaming shuffle buffer")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--skip_resnet", action="store_true", help="skip the ResNet50 comparison backbone")
    args = ap.parse_args()

    for d in (args.features_dir, args.cache_dir, args.results_dir):
        os.makedirs(d, exist_ok=True)

    from encoders import ClipImageEncoder, ClipTextEncoder, ResNetEncoder

    print(f"Loading CLIP: {args.model_name}", flush=True)
    clip_enc = ClipImageEncoder(args.model_name)
    resnet_enc = None if args.skip_resnet else ResNetEncoder()

    # Zero-shot text embeddings (trained classes + derived, unvalidated concepts)
    txt = ClipTextEncoder(args.model_name)
    class_text = txt.concept_embeddings(config.CLASS_PHRASES, config.PROMPT_TEMPLATES)
    derived_text = txt.concept_embeddings(
        {k: v["phrases"] for k, v in config.DERIVED_EMOTIONS.items()}, config.PROMPT_TEMPLATES)
    np.savez(os.path.join(args.features_dir, config.TEXT_EMB_FILENAME),
             class_text=class_text, derived_text=derived_text,
             class_names=np.array(config.TRAINED_CLASSES),
             derived_names=np.array(config.DERIVED_CLASSES),
             model_name=np.array(args.model_name),
             logit_scale=np.array(config.CLIP_LOGIT_SCALE, dtype=np.float32))
    del txt

    report_path = os.path.join(args.features_dir, config.DATA_REPORT_FILENAME)
    report = {"dataset": config.HF_DATASET, "model_name": args.model_name, "seed": args.seed,
              "classes": config.TRAINED_CLASSES, "splits": {}}
    if os.path.exists(report_path):  # allow running splits separately
        with open(report_path) as f:
            report["splits"].update(json.load(f).get("splits", {}))

    per_class = {"train": args.per_class_train, "val": args.per_class_val, "test": args.per_class_test}
    for split in args.splits:
        report["splits"][split] = extract_split(
            split, per_class[split], config.DEFAULT_MAX_SCAN[split], args, clip_enc, resnet_enc)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

    plot_distribution(report, os.path.join(args.results_dir, "class_distribution.png"))
    with open(os.path.join(args.results_dir, config.DATA_REPORT_FILENAME), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("Done. Features in", args.features_dir)


if __name__ == "__main__":
    main()
