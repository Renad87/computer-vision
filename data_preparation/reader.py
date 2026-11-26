"""Standard-library reader: manifest -> training rows with class indices (method section 8).

    from data_preparation.reader import read_rows
    for image_path, scene_index, emotion_index, split in read_rows("datasets/manifests/manifest_v1.jsonl"):
        ...

scene_index is 0-16 (taxonomy class_order, ending with scene.other) only when scene_label_status == "labeled";
emotion_index is 0-7 (amusement, awe, contentment, excitement, anger, disgust, fear, sadness) only when
emotion_label_status == "labeled". Otherwise None: that task's loss is masked. `labeled_set` (PV-Test) is
evaluation only and gives None here.

    python -m data_preparation.reader <manifest>      # prints counts per split and mask
"""
import json
import sys
from collections import Counter

from contracts.taxonomy import load_taxonomy


def class_indices(taxonomy=None):
    tax = taxonomy or load_taxonomy()
    return ({c: i for i, c in enumerate(tax.class_order["scene"])},
            {c: i for i, c in enumerate(tax.class_order["img_emotion"])})


def read_rows(manifest_path, splits=None, taxonomy=None):
    scene_idx, emo_idx = class_indices(taxonomy)
    with open(manifest_path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if splits and r["split"] not in splits:
                continue
            s = scene_idx[r["scene_label"]] if r["scene_label_status"] == "labeled" else None
            e = emo_idx[r["emotion_label"]] if r["emotion_label_status"] == "labeled" else None
            yield r["image_path"], s, e, r["split"]


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 1:
        print(__doc__)
        return 2
    c = Counter((split, s is not None, e is not None) for _, s, e, split in read_rows(args[0]))
    for (split, sm, em), n in sorted(c.items()):
        print(f"{split:9s} scene_mask={int(sm)} emotion_mask={int(em)}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
