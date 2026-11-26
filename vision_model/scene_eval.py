"""Scene head on Shaden's Places365 sample: embedding cache, temperature, rejection threshold, evaluation.

    .venv/bin/python -B -m vision_model.scene_eval --manifest datasets/manifests/manifest_v1.jsonl

1. Reads the places365_sample rows of a manifest that passes production validation. Each image is read
   from external/shaden_visual/data/places365/<folder>/<file> and must match the manifest sha256.
2. Leakage check: the reused scene head was trained by the previous visual module on the split in
   external/shaden_visual/data/places_manifest.csv. Every image must have the same split in the new
   manifest, or the run stops.
3. Temperature: fitted on val NLL (labelled rows, 17-way).
4. Rejection threshold, re-derived after temperature with the contract rule
   "max in-taxonomy probability of the 17-way softmax": the value that keeps 95% of the in-taxonomy
   val images (label not scene.other) supported.
5. Test is scored once: 17-way accuracy and macro-F1 with bootstrap CIs; the 16-class in-taxonomy subset;
   calibration before/after; rejection of ood_test images (AUROC, rejected share) and of background
   (scene.other) test images.
Writes artifacts/features/places_clip_vitb32.npz, artifacts/heads/scene_calibration_v1.json and
evaluation/vision/scene_eval_<run_id>.json.
"""
import argparse
import csv
import datetime
import json
import ntpath
import os
import uuid

import numpy as np

from . import calibration, config, metrics
from .heads import load_old_scene_head, softmax
from .train_emotion import file_sha256, load_validated_manifest

PLACES_DIR = os.path.join(config.REPO, "external", "shaden_visual", "data")
PLACES_CACHE = os.path.join(config.FEATURES_DIR, "places_clip_vitb32.npz")
CALIB_PATH = os.path.join(config.HEADS_DIR, "scene_calibration_v1.json")
TPR_TARGET = 0.95


def places_rows(records):
    rows = [r for r in records if r["source_dataset"] == "places365_sample"]
    for r in rows:
        folder, name = r["image_path"].split("/")[-2:]
        r["_file"] = os.path.join(PLACES_DIR, "places365", folder, name)
    return rows


def old_splits():
    with open(os.path.join(PLACES_DIR, "places_manifest.csv"), encoding="utf-8", newline="") as fh:
        return {ntpath.basename(r["path"])[:-4]: r["split"] for r in csv.DictReader(fh)}


def leakage_check(rows):
    old = old_splits()
    allowed = {"train": {"train"}, "val": {"val"}, "test": {"test"}, "ood_test": {"test"}}  # old OOD rows sat in test
    diff = [(r["source_image_id"], old.get(r["source_image_id"]), r["split"]) for r in rows
            if old.get(r["source_image_id"]) not in allowed[r["split"]]]
    moved = sum(1 for r in rows if r["split"] == "ood_test")
    return {"rows": len(rows), "in_old_manifest": sum(r["source_image_id"] in old for r in rows),
            "split_differs": len(diff), "examples": diff[:5], "old_test_moved_to_ood_test": moved,
            "old_split_values": sorted(set(old.values()))}


def build_cache(rows, device="auto", force=False):
    import hashlib

    from .backbone import ClipEncoder
    from .features import extract

    shas = np.array([r["image_sha256"] for r in rows])
    if os.path.exists(PLACES_CACHE) and not force:
        with np.load(PLACES_CACHE, allow_pickle=False) as d:
            if len(d["sha256"]) == len(shas) and (d["sha256"] == shas).all():
                return d["feats"]
    items = []
    for r in rows:
        with open(r["_file"], "rb") as fh:
            data = fh.read()
        if hashlib.sha256(data).hexdigest() != r["image_sha256"]:
            raise RuntimeError(f"sha256 mismatch for {r['_file']}")
        items.append({"bytes": data})
    feats, _, _ = extract(items, ClipEncoder(device))
    os.makedirs(config.FEATURES_DIR, exist_ok=True)
    np.savez(PLACES_CACHE, feats=feats, sha256=shas, image_ids=np.array([r["image_id"] for r in rows]),
             split=np.array([r["split"] for r in rows]))
    return feats


def auroc(pos, neg):
    """P(score_pos > score_neg) with ties counted half (Mann-Whitney)."""
    scores = np.concatenate([pos, neg])
    ranks = np.empty(len(scores))
    order = scores.argsort()
    ranks[order] = np.arange(1, len(scores) + 1)
    for v in np.unique(scores):
        m = scores == v
        ranks[m] = ranks[m].mean()
    return float((ranks[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def run(manifest, device="auto"):
    from contracts.taxonomy import load_taxonomy

    taxonomy = load_taxonomy()
    rows = places_rows(load_validated_manifest(manifest, taxonomy))
    leak = leakage_check(rows)
    if leak["split_differs"] or leak["in_old_manifest"] != len(rows):
        raise SystemExit(f"split differs from the reused head's training split: {leak}")
    feats = build_cache(rows, device)
    head = load_old_scene_head(taxonomy)
    ids = head.output_ids
    other = ids.index("scene.other")
    in_tax = [i for i in range(len(ids)) if i != other]
    split = np.array([r["split"] for r in rows])
    labeled = np.array([r["scene_label_status"] == "labeled" for r in rows])
    y = np.array([ids.index(r["scene_label"]) if r["scene_label"] else -1 for r in rows])
    logits = head.logits(feats)

    val = (split == "val") & labeled
    temperature, fit = calibration.fit_temperature(logits[val], y[val])
    probs = softmax(logits / temperature)
    max_in = probs[:, in_tax].max(1)
    val_in = val & (y != other)
    threshold = float(np.quantile(max_in[val_in], 1 - TPR_TARGET))

    test = (split == "test") & labeled
    test_in = test & (y != other)
    ood = split == "ood_test"
    report = {
        "manifest_sha256": file_sha256(manifest), "leakage_check": leak, "temperature_fit": fit,
        "threshold": {"rule": "max_in_taxonomy_prob_of_17way_softmax", "value": threshold, "tpr_target": TPR_TARGET,
                      "fitted_on": f"Places365 sample val, in-taxonomy images (n={int(val_in.sum())}), after temperature",
                      "previous_value_before_temperature": 0.3608365058898926},
        "sizes": {s: int(((split == s) & labeled).sum()) for s in ("train", "val", "test")} | {"ood_test": int(ood.sum())},
        "test_17way": metrics.classification_report(y[test], probs[test], ids),
        "test_17way_calibration": calibration.calibration_table(y[test], logits[test], temperature),
        "test_in_taxonomy_16": {
            "n": int(test_in.sum()),
            "accuracy_argmax_over_16": metrics.accuracy(y[test_in], np.array(in_tax)[probs[test_in][:, in_tax].argmax(1)]),
            "macro_f1_argmax_over_16": metrics.macro_f1(
                np.array([in_tax.index(v) for v in y[test_in]]), probs[test_in][:, in_tax].argmax(1), len(in_tax)),
            "supported_rate": float((max_in[test_in] >= threshold).mean())},
        "rejection": {
            "auroc_in_taxonomy_test_vs_ood_test": auroc(max_in[test_in], max_in[ood]),
            "ood_test_rejected": float((max_in[ood] < threshold).mean()), "ood_n": int(ood.sum()),
            "background_test_rejected": float((max_in[test & (y == other)] < threshold).mean()),
            "background_test_n": int((test & (y == other)).sum())},
    }
    return temperature, threshold, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args(argv)
    run_id = f"scene-s1-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    temperature, threshold, report = run(args.manifest, args.device)
    report["run_id"] = run_id
    os.makedirs(config.HEADS_DIR, exist_ok=True)
    with open(CALIB_PATH, "w", encoding="utf-8") as fh:
        json.dump({"run_id": run_id, "temperature": temperature, "scene_supported": threshold,
                   "tpr_target": TPR_TARGET, "fitted_on": report["threshold"]["fitted_on"],
                   "manifest_sha256": report["manifest_sha256"]}, fh, indent=1)
        fh.write("\n")
    path = os.path.join(config.REPORTS_DIR, f"{run_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    t = report["test_17way"]
    print(json.dumps({"run_id": run_id, "temperature": temperature, "threshold": threshold, "sizes": report["sizes"],
                      "leakage_check": report["leakage_check"]["split_differs"]}))
    print(f"test 17-way: acc {t['accuracy']:.4f} {t['accuracy_ci95']}  macro-F1 {t['macro_f1']:.4f} {t['macro_f1_ci95']}"
          f"  top2 {t['top2_accuracy']:.4f}")
    print("in-taxonomy 16:", json.dumps(report["test_in_taxonomy_16"]))
    print("calibration:", json.dumps(report["test_17way_calibration"]))
    print("rejection:", json.dumps(report["rejection"]))
    print("report", path)


if __name__ == "__main__":
    main()
