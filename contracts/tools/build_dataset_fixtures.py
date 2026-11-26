"""Build the synthetic image_manifest fixtures for dataset engineering (no data-preparation logic here).

    python3 -m contracts.tools.build_dataset_fixtures

Writes under <repo>/fixtures/dataset/:
  valid/*.jsonl            manifests that pass `python3 -m contracts.validate image_manifest <file> --mode fixture`
  invalid/*.jsonl          manifests that fail with exactly the error codes listed for them
  reports_examples/        example of the quarantine list format (not a validated contract)
  expected_outcomes.json   expected exit code, error codes and issue paths per file and mode
  INDEX.md                 the same table for people

Every record is SYNTHETIC test data: "fixture": true, every source_image_id and file name starts with
"fixture_", image_sha256 is the SHA-256 of a text label (there is no image behind it), annotator ids are
placeholders, and license_terms says so. None of it is training or evaluation data, and the validator
rejects every file here in production mode (E_FIXTURE_IN_PRODUCTION).

The intended error codes below are written by hand. The build runs the unchanged validator and stops if
any file does not produce exactly its intended codes, so the files, the index and the validator agree.
"""
import hashlib
import json
import os
import sys

from ..taxonomy import load_taxonomy
from ..validate import Context, validate_records

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "fixtures", "dataset")
VERSIONS = {"schema_version": "1.0.0", "taxonomy_version": "1.0.0"}
LICENSE = "synthetic fixture record; no real image"
DATE = "2026-11-25"
ABSENT = object()  # marks a field that is left out of the record

EMOSET = {"protocol": "SYNTHETIC FIXTURE, no real annotation. Shape of an EmoSet-118K emotion label: "
                      "10 annotators per image, label kept above 7 of 10 yes votes (EmoSet paper)",
          "annotators": [], "date": None}
EMOSET_SCENE = {"protocol": "SYNTHETIC FIXTURE, no real annotation. Shape of an EmoSet-118K emotion label "
                            "plus its scene attribute (Places365 model prediction verified yes/no by annotators, "
                            "EmoSet paper), mapped with taxonomy v1 and checked in the metadata audit",
                "annotators": [], "date": None}
PLACES = {"protocol": "SYNTHETIC FIXTURE, no real annotation. Shape of a Places365 validation category label "
                      "sampled and re-split 60/20/20 with seed 42 (prepare_data.py)",
          "annotators": [], "date": None}
PV_TEST = {"protocol": "SYNTHETIC FIXTURE, no real annotation. Shape of a PV-Test label: two independent team "
                       "annotators, union of acceptable emotion sets, scene by consensus",
           "annotators": ["fixture_annotator_A", "fixture_annotator_B"], "date": DATE}


def fake_sha(name):
    return hashlib.sha256(f"poetry-vision-dataset-fixture:{name}".encode("utf-8")).hexdigest()


def emotion_of(sid):
    for name in ("amusement", "awe", "contentment", "excitement", "anger", "disgust", "fear", "sadness"):
        if f"_{name}_" in sid:
            return name
    return None


def record(source, sid, split, *, scene=(None, "unavailable", None), raw=ABSENT,
           emotion=(None, "unavailable", None), group=None, review="dataset_original", provenance=None,
           size=(256, 256), sha=None, path=None, origin=None, **extra):
    """One synthetic manifest record. scene/emotion are (label, status, source)."""
    if path is None:
        folder = {"emoset118k": f"emoset/{split}/{emotion_of(sid) or 'unknown'}", "places365_sample": "places365",
                  "pv_test": "pv_test"}[source]
        path = f"datasets/images/{folder}/{sid}.jpg"
    if origin is None:
        origin = {"emoset118k": "hf_mirror_split", "places365_sample": "reconstructed_from_official_val_seed42",
                  "pv_test": "independent_test"}[source]
    if provenance is None:
        provenance = {"emoset118k": EMOSET, "places365_sample": PLACES, "pv_test": PV_TEST}[source]
    out = {**VERSIONS, "fixture": True, "image_id": f"img:{source}:{sid}", "source_dataset": source,
           "source_image_id": sid, "image_path": path, "image_sha256": sha or fake_sha(sid),
           "width": size[0], "height": size[1], "split": split, "split_origin": origin, "near_dup_group": group,
           "scene_label": scene[0], "scene_label_status": scene[1], "scene_label_source": scene[2]}
    if raw is not ABSENT:
        out["scene_source_raw"] = raw
    out.update({"emotion_label": emotion[0], "emotion_label_status": emotion[1], "emotion_label_source": emotion[2]})
    out.update(extra)
    out.update({"annotation_provenance": provenance, "review_status": review, "license_terms": LICENSE})
    return out


def emo(name):
    return (f"img_emotion.{name}", "labeled", "emoset_consensus")


def places_scene(label):
    return (label, "labeled", "places365_category")


def mapped(label):
    return (label, "labeled", "emoset_attribute_mapped")


UNMAPPED, EXCLUDED = (None, "unmapped", None), (None, "excluded_ood", None)
LANDSCAPE, PORTRAIT = (256, 171), (171, 256)


# ------------------------------------------------------------------------------------------- valid cases
def valid_cases():
    v01 = [
        record("places365_sample", "fixture_places_desert_sand_0001", "train", scene=places_scene("scene.desert"),
               raw="desert/sand"),
        record("places365_sample", "fixture_places_coast_0002", "val", scene=places_scene("scene.sea_coast"),
               raw="coast"),
        record("places365_sample", "fixture_places_lake_natural_0003", "test",
               scene=places_scene("scene.rivers_lakes"), raw="/l/lake/natural"),
    ]
    v02 = [
        record("emoset118k", "fixture_emoset_awe_0001", "train", emotion=emo("awe"), size=LANDSCAPE),
        record("emoset118k", "fixture_emoset_fear_0002", "val", emotion=emo("fear"), size=PORTRAIT),
        record("emoset118k", "fixture_emoset_sadness_0003", "test", emotion=emo("sadness"), size=LANDSCAPE),
    ]
    v03 = [
        record("emoset118k", "fixture_emoset_contentment_0004", "train", scene=mapped("scene.sea_coast"), raw="coast",
               emotion=emo("contentment"), review="audit_sampled", provenance=EMOSET_SCENE, size=LANDSCAPE),
        record("emoset118k", "fixture_emoset_awe_0005", "val", scene=mapped("scene.forest"),
               raw="/f/forest/broadleaf", emotion=emo("awe"), provenance=EMOSET_SCENE, size=LANDSCAPE),
        record("emoset118k", "fixture_emoset_amusement_0006", "test", scene=mapped("scene.other"), raw="bar",
               emotion=emo("amusement"), provenance=EMOSET_SCENE, size=PORTRAIT),
    ]
    v04 = [
        record("emoset118k", "fixture_emoset_anger_0007", "train", raw=None, emotion=emo("anger"),
               provenance=EMOSET_SCENE, size=LANDSCAPE),
        record("emoset118k", "fixture_emoset_disgust_0008", "test", emotion=emo("disgust"), size=LANDSCAPE),
    ]
    v05 = [
        record("emoset118k", "fixture_emoset_excitement_0009", "train", scene=UNMAPPED, raw="volcano",
               emotion=emo("excitement"), provenance=EMOSET_SCENE, size=LANDSCAPE),
        record("emoset118k", "fixture_emoset_sadness_0010", "test", scene=UNMAPPED, raw="/h/hot_spring",
               emotion=emo("sadness"), provenance=EMOSET_SCENE, size=LANDSCAPE),
    ]
    v06 = [
        record("emoset118k", "fixture_emoset_fear_0011", "train", scene=EXCLUDED, raw="airport_terminal",
               emotion=emo("fear"), provenance=EMOSET_SCENE, size=LANDSCAPE),
        record("places365_sample", "fixture_places_bowling_alley_0004", "ood_test", scene=EXCLUDED,
               raw="bowling_alley"),
    ]
    v07 = [
        record("places365_sample", "fixture_places_conference_room_0005", "train", scene=places_scene("scene.other"),
               raw="conference_room"),
        record("places365_sample", "fixture_places_bar_0006", "test", scene=places_scene("scene.other"), raw="bar"),
    ]
    v08 = [
        record("pv_test", "fixture_pv_0001", "test", scene=("scene.desert", "labeled", "human_annotation"), raw=None,
               emotion=(None, "labeled_set", "human_annotation"), review="human_double", size=(1024, 768),
               scene_ambiguous=False, acceptable_img_emotions=["img_emotion.awe", "img_emotion.contentment"],
               acceptable_lit_emotions=["lit_emotion.awe", "lit_emotion.serenity", "lit_emotion.longing"]),
        record("pv_test", "fixture_pv_0002", "test", scene=("scene.sky", "labeled", "human_annotation"), raw=None,
               emotion=(None, "labeled_set", "human_annotation"), review="adjudicated", size=(1024, 768),
               scene_ambiguous=True, acceptable_img_emotions=["img_emotion.awe"],
               acceptable_lit_emotions=["lit_emotion.awe", "lit_emotion.fear"]),
        record("pv_test", "fixture_pv_0003", "test", scene=("scene.other", "labeled", "human_annotation"), raw=None,
               emotion=(None, "labeled_set", "human_annotation"), review="human_double", size=(768, 1024),
               scene_ambiguous=False, acceptable_img_emotions=["img_emotion.contentment", "img_emotion.amusement"],
               acceptable_lit_emotions=["lit_emotion.joy"]),
    ]
    v09 = [
        record("emoset118k", "fixture_emoset_awe_0012", "train", emotion=emo("awe"), group="g:fixture_01",
               size=LANDSCAPE),
        record("emoset118k", "fixture_emoset_awe_0013", "train", emotion=emo("awe"), group="g:fixture_01",
               size=LANDSCAPE),
    ]
    v10 = [
        record("places365_sample", "fixture_places_kept_test_0007", "test", scene=places_scene("scene.desert"),
               raw="desert_road"),
        record("emoset118k", "fixture_emoset_contentment_0015", "train", emotion=emo("contentment"),
               size=LANDSCAPE),
    ]
    v11 = v01 + v02 + v03[:2] + v04[:1] + v05[:1] + v06 + v07[:1] + v09
    return [
        ("V01", "valid/V01_scene_only_places365.jsonl", "scene_only",
         "Places365 rows: scene labeled from the category (normalized names such as '/l/lake/natural'), "
         "emotion unavailable", v01),
        ("V02", "valid/V02_emotion_only_emoset_v09_shape.jsonl", "emotion_only",
         "EmoSet rows as in manifest_v0.9_emotion: emotion labeled, scene unavailable, no metadata joined "
         "(scene_source_raw absent)", v02),
        ("V03", "valid/V03_both_labels_emoset_scene_mapped.jsonl", "both_labels",
         "EmoSet rows with emotion plus a mapped scene attribute; a background category maps to scene.other", v03),
        ("V04", "valid/V04_missing_scene_metadata.jsonl", "missing_scene_metadata",
         "Scene unavailable: metadata row without a scene value (scene_source_raw null) and image not found in "
         "the metadata (field absent)", v04),
        ("V05", "valid/V05_unmapped_scene.jsonl", "unmapped_scene",
         "Raw scene outside every taxonomy list: status unmapped, no label; the emotion still trains", v05),
        ("V06", "valid/V06_unsupported_scene_excluded_ood.jsonl", "unsupported_scene",
         "Raw scene on the OOD list: excluded_ood; Places OOD rows go to split ood_test", v06),
        ("V07", "valid/V07_background_scene_other.jsonl", "scene_only",
         "Places background categories are labeled scene.other (supported 'other', not excluded)", v07),
        ("V08", "valid/V08_pv_test_labeled_set.jsonl", "pv_test",
         "PV-Test shape: human scene label, labeled_set emotions with acceptable sets, scene_ambiguous", v08),
        ("V09", "valid/V09_near_duplicates_within_one_split.jsonl", "near_duplicate_same_split",
         "Two near-duplicates confirmed in the same split share a near_dup_group; allowed", v09),
        ("V10", "valid/V10_leak_resolved_by_quarantine.jsonl", "cross_split_leakage",
         "I04 after quarantine: the test copy stays; the train copy is removed and listed in "
         "reports_examples/quarantine_example.jsonl", v10),
        ("V11", "valid/V11_mini_unified_manifest_v1_shape.jsonl", "unified_manifest",
         "A small manifest_v1 shape mixing Places and EmoSet rows and every scene status", v11),
    ]


# ------------------------------------------------------------------------------------------ invalid cases
def without(d, key):
    return {k: v for k, v in d.items() if k != key}


def invalid_cases():
    awe = record("emoset118k", "fixture_emoset_awe_0101", "train", emotion=emo("awe"), size=LANDSCAPE)
    fear = record("emoset118k", "fixture_emoset_fear_0102", "train", emotion=emo("fear"), size=LANDSCAPE)
    places = record("places365_sample", "fixture_places_desert_sand_0101", "train",
                    scene=places_scene("scene.desert"), raw="desert/sand")
    pv = record("pv_test", "fixture_pv_0101", "test", scene=("scene.desert", "labeled", "human_annotation"), raw=None,
                emotion=(None, "labeled_set", "human_annotation"), review="human_double", size=(1024, 768),
                acceptable_img_emotions=["img_emotion.awe"], acceptable_lit_emotions=["lit_emotion.awe"])
    shared = fake_sha("fixture_same_content_0101")
    leak_train = record("emoset118k", "fixture_emoset_contentment_0103", "train", emotion=emo("contentment"),
                        sha=shared, size=LANDSCAPE)
    leak_test = record("emoset118k", "fixture_emoset_contentment_0104", "test", emotion=emo("contentment"),
                       sha=shared, size=LANDSCAPE)
    cases = [
        ("I01", "E_DUP_ID__same_image_listed_twice", "exact_duplicate",
         "The same record twice: duplicate image_id and duplicate content in one split", [awe, awe], ["E_DUP_ID"]),
        ("I02", "E_DUP_ID__identical_content_same_split", "exact_duplicate",
         "Two image ids, identical sha256, same split (keep one, list the other in the duplicate report)",
         [awe, {**fear, "image_sha256": awe["image_sha256"]}], ["E_DUP_ID"]),
        ("I03", "E_SPLIT_LEAK__identical_content_train_and_test", "cross_split_leakage",
         "Identical sha256 in train and test", [leak_train, leak_test], ["E_SPLIT_LEAK"]),
        ("I04", "E_SPLIT_LEAK__identical_content_across_sources", "cross_split_leakage",
         "An EmoSet train image identical to a Places365 test image (cross-dataset leakage)",
         [record("emoset118k", "fixture_emoset_contentment_0014", "train", emotion=emo("contentment"),
                 sha=fake_sha("fixture_places_kept_test_0007"), size=LANDSCAPE),
          record("places365_sample", "fixture_places_kept_test_0007", "test", scene=places_scene("scene.desert"),
                 raw="desert_road")], ["E_SPLIT_LEAK"]),
        ("I05", "E_SPLIT_LEAK__near_duplicate_group_across_splits", "cross_split_leakage",
         "Different files confirmed as near-duplicates (same near_dup_group) in train and val",
         [{**awe, "near_dup_group": "g:fixture_11"},
          {**record("emoset118k", "fixture_emoset_awe_0105", "val", emotion=emo("awe"), size=LANDSCAPE),
           "near_dup_group": "g:fixture_11"}], ["E_SPLIT_LEAK"]),
        ("I06", "E_STATUS_CONFLICT__emotion_label_with_unavailable_status", "invalid_annotation",
         "An emotion label is present but the status says unavailable",
         [{**awe, "emotion_label_status": "unavailable"}], ["E_STATUS_CONFLICT"]),
        ("I07", "E_STATUS_CONFLICT__scene_label_contradicts_raw_mapping", "invalid_annotation",
         "Raw scene 'coast' maps to scene.sea_coast, the record says scene.desert",
         [record("emoset118k", "fixture_emoset_awe_0106", "train", scene=mapped("scene.desert"), raw="coast",
                 emotion=emo("awe"), provenance=EMOSET_SCENE, size=LANDSCAPE)], ["E_STATUS_CONFLICT"]),
        ("I08", "E_STATUS_CONFLICT__unmapped_scene_guessed_as_other", "unmapped_scene",
         "An unmapped raw scene ('volcano') labeled scene.other: guessing a label is not allowed",
         [record("emoset118k", "fixture_emoset_excitement_0107", "train", scene=mapped("scene.other"), raw="volcano",
                 emotion=emo("excitement"), provenance=EMOSET_SCENE, size=LANDSCAPE)], ["E_STATUS_CONFLICT"]),
        ("I09", "E_STATUS_CONFLICT__ood_scene_labeled_other", "unsupported_scene",
         "An OOD-list raw scene ('airport_terminal') labeled scene.other instead of excluded_ood",
         [record("emoset118k", "fixture_emoset_fear_0108", "train", scene=mapped("scene.other"),
                 raw="airport_terminal", emotion=emo("fear"), provenance=EMOSET_SCENE, size=LANDSCAPE)],
         ["E_STATUS_CONFLICT"]),
        ("I10", "E_STATUS_CONFLICT__ood_test_row_not_excluded", "unsupported_scene",
         "A row in split ood_test whose scene status is not excluded_ood",
         [record("places365_sample", "fixture_places_server_room_0102", "ood_test")], ["E_STATUS_CONFLICT"]),
        ("I11", "E_STATUS_CONFLICT__train_row_without_any_label", "invalid_annotation",
         "A training row with neither a labeled scene nor a labeled emotion",
         [record("emoset118k", "fixture_emoset_unlabeled_0109", "train", scene=UNMAPPED, raw="volcano",
                 path="datasets/images/emoset/train/fixture_emoset_unlabeled_0109.jpg", provenance=EMOSET_SCENE,
                 size=LANDSCAPE)], ["E_STATUS_CONFLICT"]),
        ("I12", "E_STATUS_CONFLICT__pv_test_image_in_train_split", "pv_test",
         "A PV-Test image placed in the train split", [{**pv, "split": "train"}], ["E_STATUS_CONFLICT"]),
        ("I13", "E_STATUS_CONFLICT__acceptable_set_outside_pv_test", "invalid_annotation",
         "An EmoSet row carrying a PV-Test acceptable set",
         [{**awe, "acceptable_img_emotions": ["img_emotion.awe", "img_emotion.contentment"]}], ["E_STATUS_CONFLICT"]),
        ("I14", "E_STATUS_CONFLICT__labeled_set_without_human_annotation", "pv_test",
         "A PV-Test labeled_set whose source is not human_annotation",
         [{**pv, "emotion_label_source": "emoset_consensus"}], ["E_STATUS_CONFLICT"]),
        ("I15", "E_UNKNOWN_ID__unknown_scene_id", "invalid_annotation",
         "A scene id that is not in taxonomy v1", [{**places, "scene_label": "scene.volcano",
                                                   "scene_source_raw": None}], ["E_UNKNOWN_ID"]),
        ("I16", "E_UNKNOWN_ID__literary_emotion_as_image_emotion", "invalid_annotation",
         "A literary emotion id used as the image emotion label",
         [{**awe, "emotion_label": "lit_emotion.longing"}], ["E_UNKNOWN_ID"]),
        ("I17", "E_FORMAT__old_scene_name_not_converted", "invalid_annotation",
         "The old manifest label 'desert' copied without converting it to 'scene.desert'; it also contradicts "
         "the mapping of the raw category",
         [{**places, "scene_label": "desert"}], ["E_FORMAT", "E_STATUS_CONFLICT"]),
        ("I18", "E_ENUM__invented_status_value", "missing_scene_metadata",
         "An invented status 'missing' instead of 'unavailable'",
         [{**awe, "scene_label_status": "missing"}], ["E_ENUM"]),
        ("I19", "E_ENUM__unknown_source_dataset", "invalid_annotation",
         "source_dataset 'emoset' is not an allowed value (use 'emoset118k')",
         [{**awe, "source_dataset": "emoset", "image_id": "img:emoset:fixture_emoset_awe_0101"}], ["E_ENUM"]),
        ("I20", "E_FORMAT__windows_path", "invalid_annotation",
         "A Windows-style path copied from the old places_manifest.csv",
         [{**places, "image_path": "data\\places365\\desert-sand\\fixture_places_desert_sand_0101.jpg"}],
         ["E_FORMAT"]),
        ("I21", "E_FORMAT__absolute_path", "invalid_annotation",
         "An absolute path instead of a path relative to the repository root",
         [{**awe, "image_path": "/data/emoset/train/awe/fixture_emoset_awe_0101.jpg"}], ["E_FORMAT"]),
        ("I22", "E_FORMAT__image_id_does_not_match_source", "invalid_annotation",
         "image_id is not img:<source_dataset>:<source_image_id>",
         [{**awe, "image_id": "img:emoset118k:fixture_emoset_awe_9999"}], ["E_FORMAT"]),
        ("I23", "E_FORMAT__md5_instead_of_sha256", "exact_duplicate",
         "A 32-hex MD5 digest where the full SHA-256 is required",
         [{**awe, "image_sha256": hashlib.md5(b"fixture_emoset_awe_0101").hexdigest()}], ["E_FORMAT"]),
        ("I24", "E_RANGE__image_side_below_64_px", "invalid_annotation",
         "A thumbnail whose short side is below the 64 px minimum", [{**awe, "height": 48}], ["E_RANGE"]),
        ("I25", "E_REQUIRED__missing_annotation_provenance", "invalid_annotation",
         "A record without annotation_provenance", [without(awe, "annotation_provenance")], ["E_REQUIRED"]),
        ("I26", "E_UNKNOWN_FIELD__pseudo_label_columns", "invalid_annotation",
         "Pseudo-label columns from an earlier model are not part of the contract",
         [{**awe, "scene_pseudo_label": "scene.desert", "pseudo_label_model": "scene_head_clip"}],
         ["E_UNKNOWN_FIELD"]),
        ("I27", "E_UNKNOWN_FIELD__quarantine_flag_inside_manifest", "cross_split_leakage",
         "Quarantined images leave the manifest; a 'quarantined' flag is not a contract field",
         [{**leak_train, "quarantined": True}], ["E_UNKNOWN_FIELD"]),
        ("I28", "E_VERSION__taxonomy_major_2", "invalid_annotation",
         "taxonomy_version 2.0.0 does not match the loaded taxonomy 1.0.0", [{**awe, "taxonomy_version": "2.0.0"}],
         ["E_VERSION"]),
    ]
    return [(cid, f"invalid/{cid}_{name}.jsonl", category, description, records, codes)
            for cid, name, category, description, records, codes in cases]


QUARANTINE_EXAMPLE = [
    {"fixture": True, "image_id": "img:emoset118k:fixture_emoset_contentment_0014",
     "image_sha256": fake_sha("fixture_places_kept_test_0007"), "source_dataset": "emoset118k",
     "removed_from_split": "train", "reason": "exact_duplicate_across_splits",
     "kept_image_id": "img:places365_sample:fixture_places_kept_test_0007", "kept_split": "test",
     "evidence": {"method": "sha256", "match": "identical"},
     "decided_by": "fixture_reviewer", "date": DATE},
    {"fixture": True, "image_id": "img:emoset118k:fixture_emoset_awe_0101",
     "image_sha256": fake_sha("fixture_emoset_awe_0101"), "source_dataset": "emoset118k",
     "removed_from_split": "train", "reason": "near_duplicate_across_splits",
     "kept_image_id": "img:emoset118k:fixture_emoset_awe_0105", "kept_split": "val",
     "evidence": {"method": "phash_and_clip", "phash_hamming": 4, "clip_cosine": 0.97, "human_confirmed": True},
     "decided_by": "fixture_reviewer", "date": DATE},
]

CATEGORIES = {
    "scene_only": "Images with scene labels only",
    "emotion_only": "Images with emotion labels only",
    "both_labels": "Images with both labels",
    "missing_scene_metadata": "Missing scene metadata",
    "unmapped_scene": "Unmapped scenes",
    "unsupported_scene": "Unsupported scenes (OOD list)",
    "exact_duplicate": "Exact duplicate cases",
    "cross_split_leakage": "Cross-split leakage cases",
    "near_duplicate_same_split": "Near-duplicates inside one split",
    "invalid_annotation": "Invalid annotations",
    "pv_test": "Independent PV-Test shape",
    "unified_manifest": "Unified manifest shape",
}


# -------------------------------------------------------------------------------------------- rendering
def as_jsonl(records):
    return "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records)


def outcome(records, tax, mode):
    issues = validate_records("image_manifest", list(enumerate(records, 1)), Context(taxonomy=tax, mode=mode))
    return {"exit_code": 1 if issues else 0, "codes": sorted({i.code for i in issues}),
            "issues": [[i.code, i.path] for i in issues]}


def check_mapping(tax):
    expected = {"desert/sand": ("scene.desert", "labeled"), "coast": ("scene.sea_coast", "labeled"),
                "/l/lake/natural": ("scene.rivers_lakes", "labeled"), "/f/forest/broadleaf": ("scene.forest", "labeled"),
                "desert_road": ("scene.desert", "labeled"), "bar": ("scene.other", "labeled"),
                "conference_room": ("scene.other", "labeled"), "volcano": (None, "unmapped"),
                "/h/hot_spring": (None, "unmapped"), "airport_terminal": (None, "excluded_ood"),
                "bowling_alley": (None, "excluded_ood"), "server_room": (None, "excluded_ood")}
    for raw, pair in expected.items():
        if tax.map_places365(raw) != pair:
            raise SystemExit(f"taxonomy maps {raw!r} to {tax.map_places365(raw)}, fixtures assume {pair}")


INDEX_HEAD = """# Dataset fixtures (synthetic)

Every file here is SYNTHETIC test data for the `image_manifest` contract. It is not training, validation or
evaluation data and must never be merged into a real manifest.

- Every record has `"fixture": true`. Every `source_image_id` and file name starts with `fixture_`.
- `image_sha256` is the SHA-256 of a text label. No image exists behind any record.
- Annotator ids are placeholders, and `license_terms` reads "synthetic fixture record; no real image".
- In production mode the validator rejects every file here with `E_FIXTURE_IN_PRODUCTION`.

Rebuild with `python3 -m contracts.tools.build_dataset_fixtures`. The build stops if the validator disagrees with
the intended codes below. Machine-readable expectations, including issue paths, are in `expected_outcomes.json`.

Check one file:

```bash
python3 -m contracts.validate image_manifest fixtures/dataset/valid/V11_mini_unified_manifest_v1_shape.jsonl --mode fixture
```

Exit code 0 means valid; 1 means issues were printed as `CODE<TAB>path<TAB>message`.

## Coverage

| Requested case | Files |
|---|---|
"""


def render():
    tax = load_taxonomy()
    check_mapping(tax)
    files, cases, rows = {}, [], []
    for cid, relative, category, description, records in valid_cases():
        fixture, production = outcome(records, tax, "fixture"), outcome(records, tax, "production")
        if fixture["issues"]:
            raise SystemExit(f"{relative} should be valid: {fixture['issues']}")
        if production["codes"] != ["E_FIXTURE_IN_PRODUCTION"] or len(production["issues"]) != len(records):
            raise SystemExit(f"{relative}: production mode should only report E_FIXTURE_IN_PRODUCTION")
        files[relative] = as_jsonl(records)
        cases.append({"id": cid, "file": relative, "category": category, "description": description,
                      "records": len(records), "expected": {"fixture": fixture, "production": production}})
        rows.append((cid, relative, category, description, "valid (exit 0)"))
    for cid, relative, category, description, records, codes in invalid_cases():
        fixture = outcome(records, tax, "fixture")
        if fixture["codes"] != sorted(codes):
            raise SystemExit(f"{relative}: intended {codes}, validator reports {fixture['issues']}")
        files[relative] = as_jsonl(records)
        cases.append({"id": cid, "file": relative, "category": category, "description": description,
                      "records": len(records), "expected": {"fixture": fixture}})
        rows.append((cid, relative, category, description, ", ".join(codes)))
    files["reports_examples/quarantine_example.jsonl"] = as_jsonl(QUARANTINE_EXAMPLE)
    files["expected_outcomes.json"] = json.dumps({
        "description": "Synthetic image_manifest fixtures for dataset engineering. Not training data.",
        "contract": "image_manifest", "schema_version": "1.0.0", "taxonomy_version": tax.version,
        "command": "python3 -m contracts.validate image_manifest <file> --mode <fixture|production>",
        "generated_by": "python3 -m contracts.tools.build_dataset_fixtures",
        "categories": CATEGORIES,
        "not_validated": {"reports_examples/quarantine_example.jsonl":
                          "format proposal for datasets/reports/quarantine.jsonl; no contract validates it"},
        "cases": cases}, ensure_ascii=False, indent=2) + "\n"
    coverage = []
    for category, label in CATEGORIES.items():
        ids = [r[0] for r in rows if r[2] == category]
        coverage.append(f"| {label} | {', '.join(ids)} |")
    table = ["", "## Files", "", "| Id | File | Case | Expected in fixture mode |", "|---|---|---|---|"]
    for cid, relative, _, description, expected in rows:
        table.append(f"| {cid} | `{relative}` | {description} | {expected} |")
    tail = ["", "Every valid file is rejected in production mode with one `E_FIXTURE_IN_PRODUCTION` per record.",
            "", "`reports_examples/quarantine_example.jsonl` shows a proposed line format for "
            "`datasets/reports/quarantine.jsonl`. No contract validates that file.", ""]
    files["INDEX.md"] = INDEX_HEAD + "\n".join(coverage + table + tail)
    return files


def main():
    files = render()
    for relative, text in files.items():
        path = os.path.join(OUT, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"wrote {len(files)} dataset fixture files under {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
