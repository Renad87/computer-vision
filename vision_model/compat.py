"""Compatibility checks for the reused heads and the shared encoder.

    .venv/bin/python -B -m vision_model.compat

Writes evaluation/vision/compat_report.json:
  1. preprocessing equals the contract (resize 224 bicubic, centre crop 224, CLIP mean/std);
  2. reordered scene/tag heads give exactly the previous module's outputs (same W, b, softmax);
  3. CPU vs MPS embeddings on a fixed sample of EmoSet images (cosine, max abs difference);
  4. agreement between the reused scene head and EmoSet's official scene attribute, on train/val
     images whose raw scene maps to a taxonomy class. EmoSet's scene is itself a Places365 model's
     top-1 prediction (unaudited), so this is agreement, not accuracy. Test images are not used.
"""
import collections
import json
import os
import sys

import numpy as np

from . import config
from .heads import load_old_calibration, load_old_scene_head, load_old_tag_head, softmax

META_FILE = os.path.join(config.REPO, "external", "emoset_metadata", "emoset118k_image_emotion_scene.jsonl")


def check_preprocessing(preprocess):
    from torchvision import transforms as T

    steps = list(preprocess.transforms)
    resize = next(s for s in steps if isinstance(s, T.Resize))
    crop = next(s for s in steps if isinstance(s, T.CenterCrop))
    norm = next(s for s in steps if isinstance(s, T.Normalize))
    return {"steps": [type(s).__name__ for s in steps],
            "resize": resize.size, "interpolation": str(resize.interpolation), "antialias": resize.antialias,
            "center_crop": list(crop.size), "mean": list(norm.mean), "std": list(norm.std),
            "matches_contract": (resize.size == config.IMAGE_SIZE and "BICUBIC" in str(resize.interpolation)
                                 and list(crop.size) == [config.IMAGE_SIZE] * 2
                                 and np.allclose(norm.mean, config.MEAN) and np.allclose(norm.std, config.STD))}


def check_head_equivalence(taxonomy, feats):
    scene = load_old_scene_head(taxonomy)
    tags = load_old_tag_head(taxonomy)
    with np.load(config.OLD_SCENE_HEAD, allow_pickle=False) as d:
        old_classes = [str(c) for c in d["classes"]]
        old_p = softmax(feats @ d["W"].T + d["b"])
    with np.load(config.OLD_TAG_HEAD, allow_pickle=False) as d:
        old_ids = [f"tag.{t}" for t in d["ids"]]
        old_t = feats @ d["W"].T + d["b"]
    new_p = scene.probs(feats)
    perm = [old_classes.index("__other__" if i == "scene.other" else i.split(".", 1)[1]) for i in scene.output_ids]
    tperm = [old_ids.index(i) for i in tags.output_ids]
    calib = load_old_calibration()
    return {"scene_max_abs_diff": float(np.abs(new_p - old_p[:, perm]).max()),
            "tags_max_abs_diff": float(np.abs(tags.logits(feats) - old_t[:, tperm]).max()),
            "scene_order": scene.output_ids, "tag_order_matches_taxonomy": tags.output_ids == taxonomy.class_order["tag"],
            "exposed_tags_with_threshold": all(t in calib["tags"] for t in taxonomy.exposed_tags),
            "scene_supported_threshold": calib["scene_supported"], "n": int(len(feats))}


def check_cpu_vs_mps(items, n=256):
    import torch

    from .backbone import ClipEncoder
    from .features import extract

    sample = items[:: max(1, len(items) // n)][:n]
    out = {"n": len(sample)}
    cpu, _, _ = extract(sample, ClipEncoder("cpu"), 64)
    if not torch.backends.mps.is_available():
        out["mps"] = "not available"
        return out, cpu
    mps, _, _ = extract(sample, ClipEncoder("mps"), 64)
    cos = (cpu * mps).sum(1)
    out.update({"min_cosine": float(cos.min()), "mean_cosine": float(cos.mean()),
                "max_abs_diff": float(np.abs(cpu - mps).max())})
    return out, cpu


def scene_agreement(taxonomy, cache):
    meta = {}
    with open(META_FILE, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            meta["img:emoset118k:" + r["image_id"]] = r
    scene = load_old_scene_head(taxonomy)
    calib = load_old_calibration()
    rows = []
    for k, (iid, split) in enumerate(zip(cache["image_ids"], cache["split"])):
        if split not in ("train", "val"):
            continue
        raw = meta.get(str(iid), {}).get("scene")
        if not raw:
            continue
        label, status = taxonomy.map_places365(raw)
        if status == "labeled":
            rows.append((k, label))
    idx = np.array([k for k, _ in rows])
    probs = scene.probs(cache["feats"][idx])
    ids = scene.output_ids
    pred = [ids[j] for j in probs.argmax(1)]
    in_tax = probs[:, [i for i, s in enumerate(ids) if s != "scene.other"]].max(1)
    per = collections.defaultdict(lambda: [0, 0])
    for (k, label), p in zip(rows, pred):
        per[label][0] += int(p == label)
        per[label][1] += 1
    agree = sum(v[0] for v in per.values())
    return {"n": len(rows), "splits": ["train", "val"], "top1_agreement": agree / len(rows),
            "supported_rate": float((in_tax >= calib["scene_supported"]).mean()),
            "per_class": {k: {"agree": v[0], "n": v[1], "rate": round(v[0] / v[1], 4)}
                          for k, v in sorted(per.items(), key=lambda kv: -kv[1][1])},
            "caveat": "EmoSet scene = Places365-model top-1 prediction, not audited; agreement, not accuracy"}


def main():
    from contracts.taxonomy import load_taxonomy

    from .backbone import load_clip
    from .features import emoset_items, load_cache

    taxonomy = load_taxonomy()
    cache = load_cache()
    _, preprocess = load_clip("cpu")
    report = {"preprocessing": check_preprocessing(preprocess)}
    items = list(emoset_items())
    report["cpu_vs_mps"], cpu_feats = check_cpu_vs_mps(items)
    cached = cache["feats"][:: max(1, len(items) // 256)][:256]
    report["cache_vs_fresh_cpu"] = {"min_cosine": float((cached * cpu_feats).sum(1).min())}
    report["head_equivalence"] = check_head_equivalence(taxonomy, cache["feats"])
    report["scene_agreement_with_emoset_attribute"] = scene_agreement(taxonomy, cache)
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, "compat_report.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    json.dump(report, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
