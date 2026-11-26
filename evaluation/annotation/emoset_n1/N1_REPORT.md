# N1: EmoSet-118K metadata (image_id, emotion, scene)

Retrieved 2026-11-26 by `emoset_n1.py fetch`, approved by the owner on the same day. Files are in `external/emoset_metadata/`, which is git-ignored. `PROVENANCE.json` there lists the sha256 of each file.

## Source and provenance

- **Source:** the official EmoSet-118K release. The README of [JingyuanYY/EmoSet](https://github.com/JingyuanYY/EmoSet) (commit `4e3288652a07c7b2334c55d2694f7a1d59692f40`) links a single Dropbox file, `EmoSet-118K.zip`. It is 11,288,914,945 bytes and holds 236,226 entries.
- **What was read:** HTTP range requests fetched only:
  - the zip's central directory, which lists entry names, sizes, offsets and CRC32 values;
  - the contiguous block holding the 118,102 `annotation/*.json` entries, located before every `image/` entry;
  - the official `train.json`, `val.json`, `test.json` and `info.json`.

  Every range is listed in `bytes_ledger.jsonl`, and every entry passed its CRC32 check.
- **Image bytes requested:** none.
- **Transferred:** 49,613,395 bytes from the zip, plus the 51 KB repository `info.json`.
- **Kept:** `image_id`, `emotion`, `scene` and `official_split`. The other attributes in the same JSON files (brightness, colorfulness, object, facial expression, human action) were discarded without being stored.
- **Not used:** the Hugging Face mirror `Woleek/EmoSet-118K`. The official source was available, so the mirror was not needed.
- **Licence:** none stated for the data. The repository's MIT licence covers its code.

## Alignment with the recovered archive

The archive is `external/renad/emoset.zip`, sha256 `df604d10…3eb13693`, holding 9,200 images.

| Check | Result |
|---|---|
| Recovered ids found in the official annotations | 9,200 / 9,200 (unmatched: 0) |
| Folder emotion equals official emotion | 9,200 / 9,200 (mismatches: 0) |
| Renad's split equals the official split | train 4,800 = train, val 1,200 = val, test 3,200 = test |
| Raw scene values outside the official 254-name vocabulary | 0 |

Renad's sample was drawn from the Hugging Face mirror's splits, and these agree exactly with the official split files for all 9,200 images. Test images therefore stay EmoSet test images.

## Scene metadata on the 9,200 images

Across the full dataset, 28,183 of 118,102 official annotations (23.9%) have a scene value.

| Status (via `Taxonomy.map_places365`) | train | val | test | total |
|---|---|---|---|---|
| no scene annotation | 3,673 | 930 | 2,492 | 7,095 |
| labeled (a taxonomy scene or `scene.other`) | 564 | 124 | 340 | 1,028 |
| unmapped | 557 | 143 | 361 | 1,061 |
| excluded_ood | 6 | 3 | 7 | 16 |

Labeled images per class (all splits):

| Class | Images |
|---|---|
| modern_city | 232 |
| other | 220 |
| sea_coast | 189 |
| sky | 116 |
| mountains_valleys | 91 |
| snow_ice | 64 |
| rivers_lakes | 37 |
| historic_monument | 29 |
| forest | 25 |
| farmland_rural | 10 |
| home_interior | 6 |
| old_city_market | 4 |
| camp_tents | 4 |
| garden | 1 |
| desert, place_of_worship, library_books | 0 |

Every value is in `emoset_scene_raw_values.csv`.

## Ambiguous mappings

EmoSet's vocabulary drops the Places365 `/subtype` suffix: `lake` for `lake/natural`, `desert` for `desert/sand` or `desert/vegetation`. Under the unchanged contract, such a value is `unmapped`. Fourteen such names cover 165 recovered images:

| Value | Images | Possible Places365 classes |
|---|---|---|
| lake | 43 | lake/natural (rivers_lakes) |
| field | 39 | field/cultivated (farmland_rural) |
| forest | 25 | forest/broadleaf (forest) |
| stadium | 17 | stadium/soccer (ood) |
| church | 16 | church/outdoor (place_of_worship) |
| desert | 9 | desert/sand or desert/vegetation (desert) |
| swimming_pool | 5 | swimming_pool/indoor (ood) |
| bazaar | 2 | bazaar/outdoor (old_city_market) |
| market | 2 | market/outdoor (old_city_market) |
| subway_station | 2 | subway_station/platform (ood) |
| library | 2 | library/indoor (library_books) |
| garage | 1 | garage/indoor (other) |
| mosque | 1 | mosque/outdoor (place_of_worship) |
| ice_skating_rink | 1 | ice_skating_rink/indoor (other) |

Two things are unknown:
- **Whether a single candidate is the only Places365 match.** For example, `church` may also cover `church/indoor`. Confirming this needs the full Places365 category list (`IO_places365.txt` or `categories_places365.txt`), which is not in the project.
- **Whether to map these names at all.** Mapping them would change the taxonomy or contract and needs owner approval. Until then they stay `unmapped`.

## Scene audit sample (decisions pending)

`scene_audit_sample_v1.csv` lists 250 images: up to 25 per class, seed 42, drawn from all splits, as section 4 of the dataset method specifies. The `decision`, `reviewer_id` and `date` columns are blank. No audit result exists yet, and none may be filled in without a person looking at each image. The provisional rule is precision ≥ 0.80 per class (Wilson 95% interval).

| Class | Sampled |
|---|---|
| sea_coast, mountains_valleys, rivers_lakes, forest, sky, snow_ice, modern_city, historic_monument, other | 25 each |
| farmland_rural | 10 |
| home_interior | 6 |
| old_city_market | 4 |
| camp_tents | 4 |
| garden | 1 |
| desert, place_of_worship, library_books | 0 (no candidate images) |

With fewer than 10 images, a class cannot pass the 0.80 rule with a meaningful interval. If all n answers are "yes", the Wilson lower bound is 0.87 for n = 25, 0.72 for n = 10, 0.61 for n = 6, 0.51 for n = 4 and 0.21 for n = 1.

## Consequence

Approach D (EmoSet scene labels on the emotion images) can add at most 1,028 scene labels, and only after the audit. Most of them are in modern_city, other, sea_coast and sky. The emotion head does not depend on any of this.
