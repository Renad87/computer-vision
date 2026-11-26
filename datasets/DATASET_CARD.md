# Dataset card: Poetry Vision unified image dataset

Owner: Shaden (dataset engineering, M2). Contract: `image_manifest` v1.0.0 (draft), taxonomy v1.0.0.
Method: `UNIFIED_DATASET_METHOD.md` v1, **approach B**. Current version: **manifest_v1**.

## Versions

| Version | File | Status | Records |
|---|---|---|---|
| v0.9 | `datasets/manifests/manifest_v0.9_emotion.jsonl` | delivered | 9,200 (EmoSet only) |
| v1 | `datasets/manifests/manifest_v1.jsonl` | delivered | 15,180 (5,980 Places365 + 9,200 EmoSet) |
| pv_test_v1 | `datasets/manifests/pv_test_v1.jsonl` | **pending**: no team photos or annotation sheets yet; tooling and protocol in `evaluation/pv_test/` | — |

## Sources

| Source | `source_dataset` | Images | Labels it gives | `split_origin` |
|---|---|---|---|---|
| Places365 sample made by Shaden (S1 `places_manifest.csv`, S2 image folder) | `places365_sample` | 5,980 | scene: 16 scenes or `scene.other`; 600 OOD-category images carry `excluded_ood` | `reconstructed_from_official_val_seed42` |
| EmoSet-118K sample made by Renad (R1 `emoset.zip`) | `emoset118k` | 9,200 | image emotion (8 classes, EmoSet consensus) | `hf_mirror_split` |

## Licence terms (as known; nothing invented)

- **EmoSet:** EmoSet-118K via the Hugging Face mirror Woleek/EmoSet-118K; dataset licence not stated by the mirror or the official repository (checked 2026-11-25); internal research use only; images not redistributed.
- **Places365:** Places365 terms not verified; internal research use only; images not redistributed.

## Collection and sampling

- **Places365:** `prepare_data.py` (`references/old_visual_module/`) downloaded official Places365 **validation** images from the Hugging Face mirror `rumenguin/places365-val`. Per category it took a seeded sample (`random.Random(42)`) and re-split it 60/20/20:
  - 56 categories make up the 16 scenes;
  - 36 background categories are labeled `scene.other`;
  - 20 OOD categories (30 images each) are kept only for rejection tests.

  Measured on the files: 5,980 JPEGs, all 256 × 256, all decode; 5,966 are RGB and 14 single-channel (L). The loader converts to RGB; files are never rewritten.
- **EmoSet:** Renad's notebook streamed each mirror split with `shuffle(seed=42, buffer_size=2000)` and kept the first 600 / 150 / 400 images per emotion as RGB JPEG quality 90 thumbnails (longer side ≤ 256 px). Measured: 9,200 RGB JPEGs, all decode, width 90–256 px, height 65–256 px.
- **Bytes as delivered:** delivered bytes are used unchanged. Every SHA-256 is in `reports/image_inventory.csv`.

## Label provenance

- **Scene (Places365):** the Places365 category of the official validation file. Old names were converted with the taxonomy (`external_names` → `class_order`). `scene_source_raw` keeps the category verbatim, and the validator re-checked every label against `Taxonomy.map_places365`, with 0 disagreements.
- **Emotion (EmoSet):** EmoSet's consensus label (10 annotators per image, label kept above 7 of 10 yes votes), read from the folder name.
- **Scene on EmoSet images:** none. This is approach B: approval N1 to use EmoSet scene metadata has not been given. Every EmoSet record is `unavailable`, with `scene_source_raw` absent.
- **No label comes from a model.** Every record is `review_status: dataset_original`.

## Status semantics and training masks

| Field | Status | Meaning | Mask | v1 count |
|---|---|---|---|---|
| scene | `labeled` | Places365 category label | 1 | 5,380 |
| scene | `excluded_ood` | OOD category; never trained as a scene, kept for rejection tests | 0 | 600 |
| scene | `unavailable` | no usable scene information (all EmoSet) | 0 | 9,200 |
| scene | `unmapped` | raw Places365 name on no list | 0 | 0 |
| emotion | `labeled` | EmoSet consensus | 1 | 9,200 |
| emotion | `unavailable` | no emotion label (all Places365) | 0 | 5,980 |

Missing is never negative. Read the manifest with `data_preparation/reader.py` (`scene_mask = status == "labeled"`, likewise for emotion).

## Splits and leakage

| source | train | val | test | ood_test |
|---|---|---|---|---|
| Places365, 16 scenes | 2,580 | 860 | 860 | 0 |
| Places365, `scene.other` | 648 | 216 | 216 | 0 |
| Places365, OOD | 0 | 0 | 0 | 600 |
| EmoSet | 4,800 | 1,200 | 3,200 | 0 |

- **Splits kept as delivered:** every image keeps its source split, except that the 600 old OOD `test` rows moved to `ood_test`, as the method requires. Nothing was re-split or rebalanced.
- **Exact duplicates (SHA-256), within and across sources and splits:** 0.
- **Near duplicates:** pHash Hamming ≤ 6 or CLIP cosine ≥ 0.95 (provisional thresholds, `ViT-B-32-quickgelu`/`openai`) nominated 159 candidate pairs: 154 by CLIP only, 3 by pHash only, 2 by both. 90 of them crossed splits and 1 crossed sources. A person (reviewer `shaden`, 2026-11-25) looked at every pair and judged all 159 to be different photographs. So there are no groups, `near_dup_group` is null everywhere, and nothing is quarantined. Details: `reports/duplicate_detection.md` and `near_duplicate_candidates.csv`.

## Class balance (v1)

- **Emotion:** perfectly balanced, 600 / 150 / 400 per class (ratio 1.0).
- **Scene:** the largest class is `scene.other` (648 train); the smallest are `scene.sky` and `scene.camp_tents` (60 train each). The ratio is 10.8 in every split. `scene.library_books` has 120 train rows; the other 13 scenes have 180.
- **Class weights:** inverse-frequency weights computed on train only are in `reports/class_distribution.md` (information only; the sampling choice is Omar's).
- **Joint scene × emotion:** none. Under approach B no image carries both labels.

## Cleaning

- Excluded: 0 (all decode; none below 64 px).
- Flagged for a visual check: 83 near-black images (mean luminance < 0.08), 76 EmoSet and 7 Places365. They are kept, because dark scenes are legitimate. The visual check is still open (`reports/flagged_for_visual_check.csv`).
- Colour modes: 14 Places365 files are single-channel and recorded in the inventory; they are not rewritten.

## Known limitations

- **No joint supervision.** Under approach B no image has both labels, so Stage 2 (shared adapter with masked loss) is an experiment without joint labels (method section 11).
- **OOD caveat.** No OOD-category image ever receives a scene label, so the scene rejection test stays valid. Under approach B, EmoSet images are never scene-labeled at all.
- **Small images.** Places365 images are 256 × 256; EmoSet images are thumbnails of at most 256 px.
- **Unconfirmed EmoSet provenance.** Renad's run note (R2) has not been received. Whether the mirror's splits equal the official EmoSet split lists is unknown.
- **Licences.** The Places365 terms have not been verified against the official site.
- **One reviewer.** One person reviewed the near-duplicate pairs (the method requires a person, not two).
- **PV-Test does not exist yet.**

## Intended use

Training and evaluating the Poetry Vision scene head (17 classes) and emotion head (8 classes), and the shared adapter with masked multi-task losses. Internal research use only; images are not redistributed.

## Reproducibility

- **Commands:** `python -m data_preparation.layout`, then `embeddings`, then `build v1`. Rebuilds from the same inputs are byte-identical (checked for v0.9 and v1).
- **Build environment:** Python 3.12.3 on Windows 11 (CPU), Pillow 11.0.0, numpy 2.1.3, torch 2.12.0+cpu, open_clip_torch 4.2.2. CLIP is used only for the near-duplicate search.
- **Original training environment (S4):** the old visual module ran on the same machine. Its `requirements.txt` says "Python 3.12, CPU only (Windows 11)". No `pip freeze` from the training date exists.

## Changelog

- **v0.9 (2026-11-25):** first manifest. Renad's EmoSet sample only; emotion labeled, scene unavailable.
- **v1 (2026-11-25):**
  - adds the Places365 sample (5,980 rows; OOD rows → `ood_test`);
  - near-duplicate search (159 candidates, all human-judged different);
  - approach B for EmoSet scenes;
  - full reports.

  The EmoSet rows are identical to v0.9.
