"""Read the delivered inputs and convert them to contract records (method section 3).

Images are read as delivered (from the zip or the folder); bytes are never re-encoded.
"""
import os
import zipfile

from contracts.taxonomy import load_taxonomy

from .common import (LICENSE_EMOSET, LICENSE_PLACES, PROTOCOL_EMOSET, PROTOCOL_PLACES, SCHEMA_VERSION,
                     SOURCE_ID_RE, TAXONOMY_VERSION, read_csv)

EMOSET_SPLITS = ("train", "val", "test")


class InputError(Exception):
    """A delivered input does not have the expected structure: stop and report."""


def _header():
    return {"schema_version": SCHEMA_VERSION, "taxonomy_version": TAXONOMY_VERSION}


# ---------------------------------------------------------------------------------------------- EmoSet (R1)
def iter_emoset(zip_path, taxonomy=None):
    """Yield (record_without_image_fields, image_bytes, zip_member) for every image in emoset.zip.

    Expected layout: emoset/{train,val,test}/<emotion>/<EmoSet image_id>.jpg
    """
    tax = taxonomy or load_taxonomy()
    emotions = dict(zip(tax.external_names["img_emotion"], tax.class_order["img_emotion"]))
    with zipfile.ZipFile(zip_path) as z:
        members = sorted(n for n in z.namelist() if not n.endswith("/"))
        unexpected = []
        for name in members:
            parts = name.split("/")
            if len(parts) != 4 or parts[0] != "emoset" or parts[1] not in EMOSET_SPLITS or parts[2] not in emotions \
                    or not parts[3].lower().endswith(".jpg"):
                unexpected.append(name)
                continue
            _, split, emotion, fname = parts
            stem = fname[: -len(".jpg")]
            if not SOURCE_ID_RE.match(stem):
                raise InputError(f"EmoSet file name {name!r} is not a valid source_image_id")
            rec = {
                **_header(),
                "image_id": f"img:emoset118k:{stem}",
                "source_dataset": "emoset118k",
                "source_image_id": stem,
                "image_path": f"datasets/images/emoset/{split}/{emotion}/{fname}",
                "split": split,
                "split_origin": "hf_mirror_split",
                "near_dup_group": None,
                "scene_label": None, "scene_label_status": "unavailable", "scene_label_source": None,
                "emotion_label": emotions[emotion], "emotion_label_status": "labeled",
                "emotion_label_source": "emoset_consensus",
                "annotation_provenance": {"protocol": PROTOCOL_EMOSET, "annotators": [], "date": None},
                "review_status": "dataset_original",
                "license_terms": LICENSE_EMOSET,
            }
            yield rec, z.read(name), name
        if unexpected:
            raise InputError(f"emoset.zip has {len(unexpected)} unexpected entries, e.g. {unexpected[:3]}")


# ---------------------------------------------------------------------------------------------- Places365 (S1, S2)
def iter_places(places_dir, taxonomy=None):
    """Yield (record_without_image_fields, image_bytes, source_path) for every row of places_manifest.csv.

    places_dir is the old ml/visual folder (holds data/places_manifest.csv and data/places365/...).
    Old label names -> taxonomy ids via model_outputs.scene.external_names -> class_order (never string surgery).
    """
    tax = taxonomy or load_taxonomy()
    old2new = dict(zip(tax.external_names["scene"], tax.class_order["scene"]))
    rows = read_csv(os.path.join(places_dir, "data", "places_manifest.csv"))
    for r in rows:
        old_path = r["path"].replace("\\", "/")                   # Windows-style in the old file
        if not old_path.startswith("data/places365/"):
            raise InputError(f"unexpected Places365 path {r['path']!r}")
        fname = old_path.rsplit("/", 1)[1]
        stem = fname.rsplit(".", 1)[0]
        if not SOURCE_ID_RE.match(stem):
            raise InputError(f"Places365 file name {fname!r} is not a valid source_image_id")
        raw = r["places_class"]
        label, split = r["label"], r["split"]
        if label == "__ood__":
            scene = {"scene_label": None, "scene_label_status": "excluded_ood", "scene_label_source": None}
            split = "ood_test"                                    # the old file says test (method 3.2)
        elif label in old2new:
            scene = {"scene_label": old2new[label], "scene_label_status": "labeled",
                     "scene_label_source": "places365_category"}
        else:
            raise InputError(f"unknown Places365 label {label!r}")
        rec = {
            **_header(),
            "image_id": f"img:places365_sample:{stem}",
            "source_dataset": "places365_sample",
            "source_image_id": stem,
            "image_path": "datasets/images/" + old_path[len("data/"):],
            "split": split,
            "split_origin": "reconstructed_from_official_val_seed42",
            "near_dup_group": None,
            **scene,
            "scene_source_raw": raw,
            "emotion_label": None, "emotion_label_status": "unavailable", "emotion_label_source": None,
            "annotation_provenance": {"protocol": PROTOCOL_PLACES, "annotators": [], "date": None},
            "review_status": "dataset_original",
            "license_terms": LICENSE_PLACES,
        }
        src = os.path.join(places_dir, *old_path.split("/"))
        if not os.path.isfile(src):
            raise InputError(f"Places365 image listed in the manifest is missing: {old_path}")
        with open(src, "rb") as fh:
            yield rec, fh.read(), old_path
