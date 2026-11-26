"""Stage 1 emotion head: Linear(512 -> 8) on frozen CLIP embeddings, then temperature scaling.

Training refuses to start unless the manifest passes `contracts.validate image_manifest` in
production mode (fixture records, schema errors, split leaks and status conflicts all block it).
Labels come from the manifest, never from folder names; every manifest image must be in the
embedding cache with the same sha256.

    .venv/bin/python -B -m vision_model.train_emotion --manifest datasets/manifests/manifest_v0.9_emotion.jsonl

Protocol (fixed before seeing any result):
  - multinomial logistic regression (scikit-learn, lbfgs, max_iter 5000), seed 42;
  - C chosen from C_GRID by validation macro-F1 (ties: the smaller C);
  - temperature fitted on validation logits;
  - the test split is scored once, after C and T are frozen.
"""
import argparse
import datetime
import hashlib
import json
import os
import uuid

import numpy as np

from . import calibration, config, metrics
from .heads import LinearHead, softmax

C_GRID = (0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
HEAD_PATH = os.path.join(config.HEADS_DIR, "emotion_head_v1.npz")


class ManifestError(RuntimeError):
    pass


def file_sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def load_validated_manifest(path, taxonomy):
    from contracts.validate import validate_file

    issues = validate_file("image_manifest", path, mode="production", taxonomy=taxonomy)
    if issues:
        listed = "\n".join(str(i) for i in issues[:20])
        raise ManifestError(f"{path} failed production validation ({len(issues)} issues):\n{listed}")
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def emotion_rows(records):
    rows = [r for r in records if r["emotion_label_status"] == "labeled" and r.get("emotion_label")]
    if not rows:
        raise ManifestError("no rows with emotion_label_status 'labeled'")
    return rows


def assemble(rows, cache, class_ids):
    """Join manifest rows to cached embeddings by image_id, checking sha256. Returns per-split X, y, ids."""
    index = {str(i): k for k, i in enumerate(cache["image_ids"])}
    missing = [r["image_id"] for r in rows if r["image_id"] not in index]
    if missing:
        raise ManifestError(f"{len(missing)} manifest images are not in the embedding cache, e.g. {missing[:3]}")
    bad = [r["image_id"] for r in rows if str(cache["sha256"][index[r["image_id"]]]) != r["image_sha256"]]
    if bad:
        raise ManifestError(f"{len(bad)} images differ from the cached bytes (sha256), e.g. {bad[:3]}")
    data = {}
    for split in ("train", "val", "test"):
        part = [r for r in rows if r["split"] == split]
        if not part:
            raise ManifestError(f"no labeled emotion rows in split {split!r}")
        idx = np.array([index[r["image_id"]] for r in part])
        data[split] = {"X": cache["feats"][idx], "y": np.array([class_ids.index(r["emotion_label"]) for r in part]),
                       "ids": [r["image_id"] for r in part]}
    return data


def fit_logreg(X, y, C, seed=config.SEED):
    from sklearn.linear_model import LogisticRegression

    clf = LogisticRegression(C=C, max_iter=5000, random_state=seed)
    clf.fit(X, y)
    if len(clf.classes_) != int(y.max()) + 1:
        raise ManifestError("a class has no training example")
    return clf.coef_.astype(np.float32), clf.intercept_.astype(np.float32), int(clf.n_iter_.max())


def select_c(train, val, n_classes, grid=C_GRID):
    results = []
    for C in grid:
        W, b, iters = fit_logreg(train["X"], train["y"], C)
        pred = (val["X"] @ W.T + b).argmax(1)
        results.append({"C": C, "val_macro_f1": metrics.macro_f1(val["y"], pred, n_classes),
                        "val_accuracy": metrics.accuracy(val["y"], pred), "iterations": iters})
    best = max(results, key=lambda r: (round(r["val_macro_f1"], 6), -r["C"]))
    return best["C"], results


def train(data, class_ids, manifest_sha=None, run_id=None, out_path=HEAD_PATH, evaluate_test=True):
    run_id = run_id or f"emotion-s1-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:6]}"
    k = len(class_ids)
    best_c, grid = select_c(data["train"], data["val"], k)
    W, b, iters = fit_logreg(data["train"]["X"], data["train"]["y"], best_c)
    head = LinearHead("emotion", "img_emotion", class_ids, W, b, "softmax", "trained_poetry_vision_v1",
                      trained_on=manifest_sha)
    val_logits = head.logits(data["val"]["X"])
    temperature, fit = calibration.fit_temperature(val_logits, data["val"]["y"])
    head.temperature = temperature
    report = {"run_id": run_id, "protocol": __doc__.split("Protocol")[1].strip(), "class_ids": class_ids,
              "manifest_sha256": manifest_sha, "selected_C": best_c, "iterations": iters, "c_grid": grid,
              "temperature_fit": fit,
              "sizes": {s: int(len(d["y"])) for s, d in data.items()},
              "val": metrics.classification_report(data["val"]["y"], softmax(val_logits / temperature), class_ids),
              "val_calibration": calibration.calibration_table(data["val"]["y"], val_logits, temperature)}
    if evaluate_test:
        test_logits = head.logits(data["test"]["X"])
        report["test"] = metrics.classification_report(data["test"]["y"], softmax(test_logits / temperature), class_ids)
        report["test_calibration"] = calibration.calibration_table(data["test"]["y"], test_logits, temperature)
    if out_path:
        head.save(out_path, extra={"run_id": run_id, "selected_C": best_c})
        report["head_file"] = os.path.relpath(out_path, config.REPO)
    return head, report


def main(argv=None):
    from contracts.taxonomy import load_taxonomy

    from .features import EMOSET_CACHE, load_cache

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--cache", default=EMOSET_CACHE)
    parser.add_argument("--report-dir", default=config.REPORTS_DIR)
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    rows = emotion_rows(load_validated_manifest(args.manifest, taxonomy))
    class_ids = taxonomy.class_order["img_emotion"]
    data = assemble(rows, load_cache(args.cache), class_ids)
    _, report = train(data, class_ids, manifest_sha=file_sha256(args.manifest))
    report["manifest"] = os.path.relpath(os.path.abspath(args.manifest), config.REPO)
    os.makedirs(args.report_dir, exist_ok=True)
    path = os.path.join(args.report_dir, f"{report['run_id']}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)
        fh.write("\n")
    print(json.dumps({k: report[k] for k in ("run_id", "selected_C", "sizes")}))
    for split in ("val", "test"):
        r = report[split]
        print(f"{split}: acc {r['accuracy']:.4f} {r['accuracy_ci95']}  macro-F1 {r['macro_f1']:.4f} {r['macro_f1_ci95']}")
    print("test calibration", json.dumps(report["test_calibration"]))
    print("report", path)


if __name__ == "__main__":
    main()
