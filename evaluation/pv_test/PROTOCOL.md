# PV-Test protocol (independent final test, method section 3.4)

Status on 2026-11-25: **pending**. No photos have been collected, so there is no `pv_test_v1.jsonl`. This folder holds the protocol and the blank sheets only. It never contains photos, consent records or the private name map.

## 1. Composition (fixed before annotating)

- **Total:** 30–40 photos taken by team members.
- **Pilot scene groups:** about 5–7 photos each of `desert`, `sea`, `greenery`, `heritage` and `sky_night` (taxonomy `pilot.scene_groups`).
- **Unsupported scenes:** 5 photos of scenes outside the 16 (for example an office, a kitchen, a gym). These are labeled `scene.other`.
- **Fixed in advance:** write the planned group of every photo in `intake.csv` before anyone annotates.

## 2. Consent and privacy

- **Consent:** every photo needs its photographer's written consent for this project. The consent record stays private with the originals (`external/pv_test_originals/`) and never goes into a zip.
- **Faces:** no identifiable faces. A person checks every photo and answers `no_identifiable_faces = yes` in `intake.csv`. No model is used.
- **Privacy export, done once by `python -m data_preparation.pv_test intake --workdir <W>`:**
  - EXIF orientation is applied;
  - every metadata field (location, device, time) is removed;
  - the photo is saved as `pv_0001.jpg`, `pv_0002.jpg`, …;
  - the bytes are then frozen.
- **Private name map:** the map from original file names stays private, in `pv_id_map_private.csv` next to the originals.

`intake.csv` columns: `original_file, photographer_id, written_consent, no_identifiable_faces, planned_group, notes`. `planned_group` is one of `desert, sea, greenery, heritage, sky_night, unsupported`.

## 3. Annotation (two people, independently, blind)

- `python -m data_preparation.pv_test sheets --workdir <W>` writes `annotation_sheet_A.csv` and `annotation_sheet_B.csv`.
- **Annotators:** two different people fill one sheet each, without seeing the other sheet or any model output. One of them may be Shaden; the other must be someone else.
- **Columns:**
  - `scene`: one of the 17 scene ids (`scene.desert` … `scene.library_books`, `scene.other`) or `ambiguous`;
  - `acceptable_img_emotions`: one or more of `img_emotion.amusement, img_emotion.awe, img_emotion.contentment, img_emotion.excitement, img_emotion.anger, img_emotion.disgust, img_emotion.fear, img_emotion.sadness`, separated by `;`;
  - `acceptable_lit_emotions`: one or more of `lit_emotion.sadness, lit_emotion.longing, lit_emotion.loneliness, lit_emotion.awe, lit_emotion.serenity, lit_emotion.joy, lit_emotion.pride, lit_emotion.fear`, separated by `;`;
  - `annotator_id` (the same on every row of one sheet), `date` (YYYY-MM-DD) and `notes`.

## 4. Merge, adjudication and freeze

`python -m data_preparation.pv_test merge --workdir <W> --date YYYY-MM-DD`:

- **Acceptable sets:** the union of both annotators' sets.
- **Scene, when both agree:** that label, with `review_status` `human_double`.
- **Scene, when they disagree or say `ambiguous`:** the photo goes to `adjudication.csv`. Omar fills `scene`, `adjudicator_id` and `date`. The record gets `adjudicated` and `scene_ambiguous: true`.
- **Validate and freeze:** the result must pass the validator in production mode. Then `pv_test_v1.jsonl` is written, together with `pv_test_v1.sha256`, which holds the SHA-256 of the manifest and of every photo. Both are never changed; a correction is `pv_test_v2` with a changelog.
- **Duplicate check:** after the freeze, compare PV-Test against all training data (SHA-256 and pHash). Any match removes the training copy, which is quarantined in a new manifest version.

## 5. Rules

- Nobody runs a model on PV-Test before the freeze.
- Nothing is ever tuned on PV-Test.
- Original annotations are kept as filled. Disagreements are not hidden: both sheets stay with the record.
