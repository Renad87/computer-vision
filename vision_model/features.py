"""Shared feature extraction and the embedding cache.

Every head reads the same cached 512-d embedding, so CLIP runs once per image.

    .venv/bin/python -B -m vision_model.features emoset --device mps

writes artifacts/features/emoset_clip_vitb32.npz (feats float32 N x 512, L2-normalised; image_ids;
sha256 of the image bytes; split and folder emotion as found in the archive) and a JSON sidecar
with the device, versions and timings. An existing cache is reused when every image sha256 matches.
"""
import argparse
import concurrent.futures
import hashlib
import json
import os
import platform
import time
import zipfile

from . import config
from .backbone import ClipEncoder, decode_image

import numpy as np  # noqa: E402
import torch  # noqa: E402

EMOSET_CACHE = os.path.join(config.FEATURES_DIR, "emoset_clip_vitb32.npz")


def emoset_items(zip_path=config.EMOSET_ZIP):
    """Yields dicts for every image in Renad's archive: emoset/<split>/<emotion>/<source_id>.jpg."""
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(n for n in z.namelist() if n.lower().endswith(".jpg")):
            _, split, emotion, filename = name.split("/")
            data = z.read(name)
            yield {"image_id": f"img:emoset118k:{filename[:-4]}", "zip_path": name, "split": split,
                   "folder_emotion": emotion, "sha256": hashlib.sha256(data).hexdigest(), "bytes": data}


def extract(items, encoder, batch_size=64, workers=8):
    """items: list of dicts with 'bytes'. Returns (feats, seconds_decode, seconds_forward)."""
    preprocess = encoder.preprocess
    feats, t_dec, t_fwd = [], 0.0, 0.0

    def prep(item):
        return preprocess(decode_image(item["bytes"]))

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        for i in range(0, len(items), batch_size):
            t0 = time.perf_counter()
            batch = torch.stack(list(pool.map(prep, items[i:i + batch_size])))
            t1 = time.perf_counter()
            feats.append(encoder.encode_tensors(batch))
            t2 = time.perf_counter()
            t_dec, t_fwd = t_dec + (t1 - t0), t_fwd + (t2 - t1)
    return np.concatenate(feats), t_dec, t_fwd


def load_cache(path=EMOSET_CACHE):
    with np.load(path, allow_pickle=False) as d:
        cache = {k: d[k] for k in d.files}
    with open(path[:-4] + ".json", encoding="utf-8") as fh:
        cache["meta"] = json.load(fh)
    return cache


def build_emoset_cache(device="auto", batch_size=64, path=EMOSET_CACHE, zip_path=config.EMOSET_ZIP, force=False):
    items = list(emoset_items(zip_path))
    shas = np.array([it["sha256"] for it in items])
    if os.path.exists(path) and not force:
        cache = load_cache(path)
        if len(cache["sha256"]) == len(shas) and (cache["sha256"] == shas).all():
            print(f"cache up to date: {path} ({len(shas)} images)")
            return cache
    encoder = ClipEncoder(device)
    t0 = time.perf_counter()
    feats, t_dec, t_fwd = extract(items, encoder, batch_size)
    total = time.perf_counter() - t0
    norms = np.linalg.norm(feats, axis=1)
    if feats.shape != (len(items), config.EMBEDDING_DIM) or not np.allclose(norms, 1.0, atol=1e-4):
        raise RuntimeError("embedding cache failed its shape/normalisation check")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    np.savez(path, feats=feats, image_ids=np.array([it["image_id"] for it in items]), sha256=shas,
             zip_path=np.array([it["zip_path"] for it in items]), split=np.array([it["split"] for it in items]),
             folder_emotion=np.array([it["folder_emotion"] for it in items]))
    import open_clip
    meta = {"source": os.path.relpath(zip_path, config.REPO), "images": len(items), "device": encoder.device,
            "batch_size": batch_size, "arch": config.CLIP_ARCH, "pretrained": config.CLIP_PRETRAINED,
            "weights_sha256": config.WEIGHTS_SHA256, "open_clip": open_clip.__version__, "torch": torch.__version__,
            "python": platform.python_version(), "machine": platform.machine(),
            "seconds_total": round(total, 2), "seconds_decode_preprocess": round(t_dec, 2),
            "seconds_forward": round(t_fwd, 2), "images_per_second": round(len(items) / total, 1),
            "norm_min": float(norms.min()), "norm_max": float(norms.max()),
            "note": "labels here are the archive folder names; training reads labels from the validated manifest"}
    with open(path[:-4] + ".json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=1)
        fh.write("\n")
    print(json.dumps(meta, indent=1))
    return load_cache(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", choices=["emoset"])
    parser.add_argument("--device", default="auto")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    build_emoset_cache(args.device, args.batch_size, force=args.force)


if __name__ == "__main__":
    main()
