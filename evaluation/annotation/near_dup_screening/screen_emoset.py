"""Near-duplicate screening of the recovered EmoSet sample (candidates only; nothing is moved or deleted).

Provisional thresholds approved by the owner on 2026-11-26 as screening rules:
  - perceptual hash (64-bit DCT pHash) Hamming distance <= 6, or
  - CLIP ViT-B/32 cosine similarity >= 0.95 (embeddings from artifacts/features/emoset_clip_vitb32.npz).

Every candidate pair needs a human decision. For a confirmed cross-split pair the proposed action keeps
the held-out image (test > val > train) and quarantines the other record; a confirmed within-split pair
gets a shared near_dup_group. Exact byte duplicates were already ruled out (0 groups).

    .venv/bin/python -B evaluation/annotation/near_dup_screening/screen_emoset.py
"""
import csv
import io
import json
import os
import sys
import zipfile

import numpy as np
from PIL import Image
from scipy.fft import dctn

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(REPO, "artifacts", "features", "emoset_clip_vitb32.npz")
ZIP = os.path.join(REPO, "external", "renad", "emoset.zip")
PHASH_MAX = 6
COSINE_MIN = 0.95
PRIORITY = {"test": 3, "val": 2, "train": 1}


def phash(img):
    g = np.asarray(img.convert("L").resize((32, 32), Image.Resampling.LANCZOS), dtype=np.float64)
    low = dctn(g, norm="ortho")[:8, :8].flatten()
    bits = low > np.median(low[1:])
    return int(np.packbits(bits).view(">u8")[0])


def main():
    with np.load(CACHE, allow_pickle=False) as d:
        feats, ids, paths, splits, emos = d["feats"], d["image_ids"], d["zip_path"], d["split"], d["folder_emotion"]
    n = len(ids)
    with zipfile.ZipFile(ZIP) as z:
        hashes = np.array([phash(Image.open(io.BytesIO(z.read(str(p))))) for p in paths], dtype=np.uint64)
    pairs = {}
    for i in range(n - 1):
        dist = np.bitwise_count(hashes[i] ^ hashes[i + 1:])
        for j in np.nonzero(dist <= PHASH_MAX)[0] + i + 1:
            pairs[(i, int(j))] = {"hamming": int(dist[j - i - 1])}
    for start in range(0, n, 1024):
        sims = feats[start:start + 1024] @ feats.T
        for a, b in zip(*np.nonzero(sims >= COSINE_MIN)):
            i, j = start + int(a), int(b)
            if i < j:
                pairs.setdefault((i, j), {})["cosine"] = float(sims[a, b])
    rows = []
    for (i, j), hit in sorted(pairs.items()):
        cos = hit.get("cosine", float(feats[i] @ feats[j]))
        ham = hit.get("hamming", int(np.bitwise_count(hashes[i] ^ hashes[j])))
        cross = splits[i] != splits[j]
        keep, other = (i, j) if PRIORITY[str(splits[i])] >= PRIORITY[str(splits[j])] else (j, i)
        if cross:
            action = f"if confirmed: keep {ids[keep]} ({splits[keep]}), quarantine {ids[other]} ({splits[other]})"
        else:
            action = "if confirmed: same near_dup_group (no removal)"
        rows.append({"image_id_a": str(ids[i]), "split_a": str(splits[i]), "emotion_a": str(emos[i]),
                     "image_id_b": str(ids[j]), "split_b": str(splits[j]), "emotion_b": str(emos[j]),
                     "phash_hamming": ham, "clip_cosine": round(cos, 5),
                     "by_phash": ham <= PHASH_MAX, "by_clip": cos >= COSINE_MIN, "cross_split": bool(cross),
                     "label_conflict": str(emos[i]) != str(emos[j]), "proposed_action": action,
                     "decision": "", "reviewer_id": "", "date": ""})
    out_csv = os.path.join(HERE, "emoset_near_dup_candidates_v1.csv")
    with open(out_csv, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) if rows else ["image_id_a"])
        w.writeheader()
        w.writerows(rows)
    images = {r["image_id_a"] for r in rows} | {r["image_id_b"] for r in rows}
    summary = {"images_screened": n, "thresholds": {"phash_hamming_max": PHASH_MAX, "clip_cosine_min": COSINE_MIN},
               "candidate_pairs": len(rows), "images_in_candidates": len(images),
               "by_phash": sum(r["by_phash"] for r in rows), "by_clip": sum(r["by_clip"] for r in rows),
               "by_both": sum(r["by_phash"] and r["by_clip"] for r in rows),
               "cross_split_pairs": sum(r["cross_split"] for r in rows),
               "cross_split_types": {}, "label_conflict_pairs": sum(r["label_conflict"] for r in rows),
               "decisions": "pending human review; no record moved, deleted or quarantined"}
    for r in rows:
        if r["cross_split"]:
            key = "|".join(sorted((r["split_a"], r["split_b"])))
            summary["cross_split_types"][key] = summary["cross_split_types"].get(key, 0) + 1
    with open(os.path.join(HERE, "emoset_near_dup_summary_v1.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1)
        fh.write("\n")
    json.dump(summary, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
