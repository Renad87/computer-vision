# Split provenance (manifest_v1)

Every image keeps its source split. Nothing was re-split, rebalanced or moved between splits; leakage was fixed only by quarantining the copy in the less protected split (`quarantine.jsonl`).

| source | split | rows in manifest | quarantined from this split |
|---|---|---|---|
| emoset118k | train | 4800 | 0 |
| emoset118k | val | 1200 | 0 |
| emoset118k | test | 3200 | 0 |
| places365_sample | train | 3228 | 0 |
| places365_sample | val | 1076 | 0 |
| places365_sample | test | 1076 | 0 |
| places365_sample | ood_test | 600 | 0 |

## EmoSet-118K sample (`emoset118k`, `split_origin` = `hf_mirror_split`)

- Evidence: the folder split in Renad's `emoset.zip` (input R1, SHA-256 `df604d10fd825dd0d9761e8ccda26c3e7859a2c517f64eae06900f359eb13693`).
- Renad's code (`references/old_emotion_module/emoset_sampling_cells.md`, cell 4) streamed the mirror splits `train`, `val`, `test` of `Woleek/EmoSet-118K` with `shuffle(seed=42, buffer_size=2000)` and kept the first 600 / 150 / 400 per emotion. Her printed counts (4,800 / 1,200 / 3,200) equal the files.
- Not confirmed: Renad's run note (R2: run date, `datasets` version, her SHA-256 of the zip) has not been received; whether the mirror splits equal the official EmoSet split lists is unknown (lists not available).

## Places365 sample (`places365_sample`, `split_origin` = `reconstructed_from_official_val_seed42`)

- Evidence: `places_manifest.csv` (input S1) lists only official Places365 validation files (`Places365_val_<digits>.jpg`).
- `prepare_data.py` (copy in `references/old_visual_module/`) sampled them per category and re-split 60/20/20 with `random.Random(42)`. The counts equal `references/derived/PREPROCESSING_AND_SPLITS.md`: 16 scenes 2,580 / 860 / 860, background → `scene.other` 648 / 216 / 216, OOD 600.
- The 600 OOD rows (old split `test`) were moved to `ood_test` as the method requires; they carry `excluded_ood` and no scene label.

## PV-Test

Pending: no photos yet, so no freeze record.
