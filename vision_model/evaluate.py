"""Score a saved emotion head on one split of a validated manifest, from cached embeddings.

    .venv/bin/python -B -m vision_model.evaluate --manifest datasets/manifests/manifest_v0.9_emotion.jsonl --split test

Reports accuracy and macro-F1 with bootstrap 95% intervals, per-class scores, the confusion matrix and
NLL / ECE / Brier with and without the head's temperature. Use the test split once, after training.
"""
import argparse
import json
import os

from . import calibration, config, metrics
from .heads import LinearHead, softmax
from .train_emotion import HEAD_PATH, assemble, emotion_rows, file_sha256, load_validated_manifest


def evaluate(head, data_split, class_ids):
    logits = head.logits(data_split["X"])
    t = head.temperature or 1.0
    return {"report": metrics.classification_report(data_split["y"], softmax(logits / t), class_ids),
            "calibration": calibration.calibration_table(data_split["y"], logits, t)}


def main(argv=None):
    from contracts.taxonomy import load_taxonomy

    from .features import EMOSET_CACHE, load_cache

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--split", choices=["val", "test"], required=True)
    parser.add_argument("--head", default=HEAD_PATH)
    parser.add_argument("--cache", default=EMOSET_CACHE)
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    class_ids = taxonomy.class_order["img_emotion"]
    head = LinearHead.load(args.head)
    manifest_sha = file_sha256(args.manifest)
    if head.trained_on and head.trained_on != manifest_sha:
        print(f"warning: head trained on manifest {head.trained_on[:12]}, evaluating on {manifest_sha[:12]}")
    data = assemble(emotion_rows(load_validated_manifest(args.manifest, taxonomy)), load_cache(args.cache), class_ids)
    result = evaluate(head, data[args.split], class_ids)
    r = result["report"]
    print(f"{args.split}: n {r['n']}  acc {r['accuracy']:.4f} {r['accuracy_ci95']}  "
          f"macro-F1 {r['macro_f1']:.4f} {r['macro_f1_ci95']}")
    print(json.dumps(result["calibration"]))
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    path = os.path.join(config.REPORTS_DIR, f"emotion_eval_{args.split}_{manifest_sha[:12]}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"head": os.path.relpath(args.head, config.REPO), "manifest_sha256": manifest_sha, **result}, fh,
                  indent=1)
        fh.write("\n")
    print("report", path)


if __name__ == "__main__":
    main()
