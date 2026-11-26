# Dataset fixtures (synthetic)

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
| Images with scene labels only | V01, V07 |
| Images with emotion labels only | V02 |
| Images with both labels | V03 |
| Missing scene metadata | V04, I18 |
| Unmapped scenes | V05, I08 |
| Unsupported scenes (OOD list) | V06, I09, I10 |
| Exact duplicate cases | I01, I02, I23 |
| Cross-split leakage cases | V10, I03, I04, I05, I27 |
| Near-duplicates inside one split | V09 |
| Invalid annotations | I06, I07, I11, I13, I15, I16, I17, I19, I20, I21, I22, I24, I25, I26, I28 |
| Independent PV-Test shape | V08, I12, I14 |
| Unified manifest shape | V11 |

## Files

| Id | File | Case | Expected in fixture mode |
|---|---|---|---|
| V01 | `valid/V01_scene_only_places365.jsonl` | Places365 rows: scene labeled from the category (normalized names such as '/l/lake/natural'), emotion unavailable | valid (exit 0) |
| V02 | `valid/V02_emotion_only_emoset_v09_shape.jsonl` | EmoSet rows as in manifest_v0.9_emotion: emotion labeled, scene unavailable, no metadata joined (scene_source_raw absent) | valid (exit 0) |
| V03 | `valid/V03_both_labels_emoset_scene_mapped.jsonl` | EmoSet rows with emotion plus a mapped scene attribute; a background category maps to scene.other | valid (exit 0) |
| V04 | `valid/V04_missing_scene_metadata.jsonl` | Scene unavailable: metadata row without a scene value (scene_source_raw null) and image not found in the metadata (field absent) | valid (exit 0) |
| V05 | `valid/V05_unmapped_scene.jsonl` | Raw scene outside every taxonomy list: status unmapped, no label; the emotion still trains | valid (exit 0) |
| V06 | `valid/V06_unsupported_scene_excluded_ood.jsonl` | Raw scene on the OOD list: excluded_ood; Places OOD rows go to split ood_test | valid (exit 0) |
| V07 | `valid/V07_background_scene_other.jsonl` | Places background categories are labeled scene.other (supported 'other', not excluded) | valid (exit 0) |
| V08 | `valid/V08_pv_test_labeled_set.jsonl` | PV-Test shape: human scene label, labeled_set emotions with acceptable sets, scene_ambiguous | valid (exit 0) |
| V09 | `valid/V09_near_duplicates_within_one_split.jsonl` | Two near-duplicates confirmed in the same split share a near_dup_group; allowed | valid (exit 0) |
| V10 | `valid/V10_leak_resolved_by_quarantine.jsonl` | I04 after quarantine: the test copy stays; the train copy is removed and listed in reports_examples/quarantine_example.jsonl | valid (exit 0) |
| V11 | `valid/V11_mini_unified_manifest_v1_shape.jsonl` | A small manifest_v1 shape mixing Places and EmoSet rows and every scene status | valid (exit 0) |
| I01 | `invalid/I01_E_DUP_ID__same_image_listed_twice.jsonl` | The same record twice: duplicate image_id and duplicate content in one split | E_DUP_ID |
| I02 | `invalid/I02_E_DUP_ID__identical_content_same_split.jsonl` | Two image ids, identical sha256, same split (keep one, list the other in the duplicate report) | E_DUP_ID |
| I03 | `invalid/I03_E_SPLIT_LEAK__identical_content_train_and_test.jsonl` | Identical sha256 in train and test | E_SPLIT_LEAK |
| I04 | `invalid/I04_E_SPLIT_LEAK__identical_content_across_sources.jsonl` | An EmoSet train image identical to a Places365 test image (cross-dataset leakage) | E_SPLIT_LEAK |
| I05 | `invalid/I05_E_SPLIT_LEAK__near_duplicate_group_across_splits.jsonl` | Different files confirmed as near-duplicates (same near_dup_group) in train and val | E_SPLIT_LEAK |
| I06 | `invalid/I06_E_STATUS_CONFLICT__emotion_label_with_unavailable_status.jsonl` | An emotion label is present but the status says unavailable | E_STATUS_CONFLICT |
| I07 | `invalid/I07_E_STATUS_CONFLICT__scene_label_contradicts_raw_mapping.jsonl` | Raw scene 'coast' maps to scene.sea_coast, the record says scene.desert | E_STATUS_CONFLICT |
| I08 | `invalid/I08_E_STATUS_CONFLICT__unmapped_scene_guessed_as_other.jsonl` | An unmapped raw scene ('volcano') labeled scene.other: guessing a label is not allowed | E_STATUS_CONFLICT |
| I09 | `invalid/I09_E_STATUS_CONFLICT__ood_scene_labeled_other.jsonl` | An OOD-list raw scene ('airport_terminal') labeled scene.other instead of excluded_ood | E_STATUS_CONFLICT |
| I10 | `invalid/I10_E_STATUS_CONFLICT__ood_test_row_not_excluded.jsonl` | A row in split ood_test whose scene status is not excluded_ood | E_STATUS_CONFLICT |
| I11 | `invalid/I11_E_STATUS_CONFLICT__train_row_without_any_label.jsonl` | A training row with neither a labeled scene nor a labeled emotion | E_STATUS_CONFLICT |
| I12 | `invalid/I12_E_STATUS_CONFLICT__pv_test_image_in_train_split.jsonl` | A PV-Test image placed in the train split | E_STATUS_CONFLICT |
| I13 | `invalid/I13_E_STATUS_CONFLICT__acceptable_set_outside_pv_test.jsonl` | An EmoSet row carrying a PV-Test acceptable set | E_STATUS_CONFLICT |
| I14 | `invalid/I14_E_STATUS_CONFLICT__labeled_set_without_human_annotation.jsonl` | A PV-Test labeled_set whose source is not human_annotation | E_STATUS_CONFLICT |
| I15 | `invalid/I15_E_UNKNOWN_ID__unknown_scene_id.jsonl` | A scene id that is not in taxonomy v1 | E_UNKNOWN_ID |
| I16 | `invalid/I16_E_UNKNOWN_ID__literary_emotion_as_image_emotion.jsonl` | A literary emotion id used as the image emotion label | E_UNKNOWN_ID |
| I17 | `invalid/I17_E_FORMAT__old_scene_name_not_converted.jsonl` | The old manifest label 'desert' copied without converting it to 'scene.desert'; it also contradicts the mapping of the raw category | E_FORMAT, E_STATUS_CONFLICT |
| I18 | `invalid/I18_E_ENUM__invented_status_value.jsonl` | An invented status 'missing' instead of 'unavailable' | E_ENUM |
| I19 | `invalid/I19_E_ENUM__unknown_source_dataset.jsonl` | source_dataset 'emoset' is not an allowed value (use 'emoset118k') | E_ENUM |
| I20 | `invalid/I20_E_FORMAT__windows_path.jsonl` | A Windows-style path copied from the old places_manifest.csv | E_FORMAT |
| I21 | `invalid/I21_E_FORMAT__absolute_path.jsonl` | An absolute path instead of a path relative to the repository root | E_FORMAT |
| I22 | `invalid/I22_E_FORMAT__image_id_does_not_match_source.jsonl` | image_id is not img:<source_dataset>:<source_image_id> | E_FORMAT |
| I23 | `invalid/I23_E_FORMAT__md5_instead_of_sha256.jsonl` | A 32-hex MD5 digest where the full SHA-256 is required | E_FORMAT |
| I24 | `invalid/I24_E_RANGE__image_side_below_64_px.jsonl` | A thumbnail whose short side is below the 64 px minimum | E_RANGE |
| I25 | `invalid/I25_E_REQUIRED__missing_annotation_provenance.jsonl` | A record without annotation_provenance | E_REQUIRED |
| I26 | `invalid/I26_E_UNKNOWN_FIELD__pseudo_label_columns.jsonl` | Pseudo-label columns from an earlier model are not part of the contract | E_UNKNOWN_FIELD |
| I27 | `invalid/I27_E_UNKNOWN_FIELD__quarantine_flag_inside_manifest.jsonl` | Quarantined images leave the manifest; a 'quarantined' flag is not a contract field | E_UNKNOWN_FIELD |
| I28 | `invalid/I28_E_VERSION__taxonomy_major_2.jsonl` | taxonomy_version 2.0.0 does not match the loaded taxonomy 1.0.0 | E_VERSION |

Every valid file is rejected in production mode with one `E_FIXTURE_IN_PRODUCTION` per record.

`reports_examples/quarantine_example.jsonl` shows a proposed line format for `datasets/reports/quarantine.jsonl`. No contract validates that file.
