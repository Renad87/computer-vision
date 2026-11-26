# Class distribution (manifest_v1)

All counts are from `manifest_v1.jsonl`.

## Status counts per source and split

| source | split | rows | scene status | emotion status |
|---|---|---|---|---|
| emoset118k | train | 4800 | unavailable 4800 | labeled 4800 |
| emoset118k | val | 1200 | unavailable 1200 | labeled 1200 |
| emoset118k | test | 3200 | unavailable 3200 | labeled 3200 |
| places365_sample | train | 3228 | labeled 3228 | unavailable 3228 |
| places365_sample | val | 1076 | labeled 1076 | unavailable 1076 |
| places365_sample | test | 1076 | labeled 1076 | unavailable 1076 |
| places365_sample | ood_test | 600 | excluded_ood 600 | unavailable 600 |

## Scene classes (labeled rows) per source and split

| class | places365_sample / train | places365_sample / val | places365_sample / test |
|---|---|---|---|
| scene.desert | 180 | 60 | 60 |
| scene.sea_coast | 180 | 60 | 60 |
| scene.mountains_valleys | 180 | 60 | 60 |
| scene.rivers_lakes | 180 | 60 | 60 |
| scene.forest | 180 | 60 | 60 |
| scene.garden | 180 | 60 | 60 |
| scene.farmland_rural | 180 | 60 | 60 |
| scene.sky | 60 | 20 | 20 |
| scene.snow_ice | 180 | 60 | 60 |
| scene.modern_city | 180 | 60 | 60 |
| scene.old_city_market | 180 | 60 | 60 |
| scene.historic_monument | 180 | 60 | 60 |
| scene.place_of_worship | 180 | 60 | 60 |
| scene.home_interior | 180 | 60 | 60 |
| scene.camp_tents | 60 | 20 | 20 |
| scene.library_books | 120 | 40 | 40 |
| scene.other | 648 | 216 | 216 |

Imbalance ratio (largest / smallest class among labeled rows):

| split | largest | smallest (non-zero) | ratio | classes with 0 rows |
|---|---|---|---|---|
| train | 648 | 60 | 10.8 | 0 |
| val | 216 | 20 | 10.8 | 0 |
| test | 216 | 20 | 10.8 | 0 |

Inverse-frequency class weights on `train` only (information for Omar; w = N / (K · n_c)):

| class | train rows | weight |
|---|---|---|
| scene.desert | 180 | 1.0549 |
| scene.sea_coast | 180 | 1.0549 |
| scene.mountains_valleys | 180 | 1.0549 |
| scene.rivers_lakes | 180 | 1.0549 |
| scene.forest | 180 | 1.0549 |
| scene.garden | 180 | 1.0549 |
| scene.farmland_rural | 180 | 1.0549 |
| scene.sky | 60 | 3.1647 |
| scene.snow_ice | 180 | 1.0549 |
| scene.modern_city | 180 | 1.0549 |
| scene.old_city_market | 180 | 1.0549 |
| scene.historic_monument | 180 | 1.0549 |
| scene.place_of_worship | 180 | 1.0549 |
| scene.home_interior | 180 | 1.0549 |
| scene.camp_tents | 60 | 3.1647 |
| scene.library_books | 120 | 1.5824 |
| scene.other | 648 | 0.293 |

## Emotion classes (labeled rows) per source and split

| class | emoset118k / train | emoset118k / val | emoset118k / test |
|---|---|---|---|
| img_emotion.amusement | 600 | 150 | 400 |
| img_emotion.awe | 600 | 150 | 400 |
| img_emotion.contentment | 600 | 150 | 400 |
| img_emotion.excitement | 600 | 150 | 400 |
| img_emotion.anger | 600 | 150 | 400 |
| img_emotion.disgust | 600 | 150 | 400 |
| img_emotion.fear | 600 | 150 | 400 |
| img_emotion.sadness | 600 | 150 | 400 |

Imbalance ratio (largest / smallest class among labeled rows):

| split | largest | smallest (non-zero) | ratio | classes with 0 rows |
|---|---|---|---|---|
| train | 600 | 600 | 1.0 | 0 |
| val | 150 | 150 | 1.0 | 0 |
| test | 400 | 400 | 1.0 | 0 |

Inverse-frequency class weights on `train` only (information for Omar; w = N / (K · n_c)):

| class | train rows | weight |
|---|---|---|
| img_emotion.amusement | 600 | 1.0 |
| img_emotion.awe | 600 | 1.0 |
| img_emotion.contentment | 600 | 1.0 |
| img_emotion.excitement | 600 | 1.0 |
| img_emotion.anger | 600 | 1.0 |
| img_emotion.disgust | 600 | 1.0 |
| img_emotion.fear | 600 | 1.0 |
| img_emotion.sadness | 600 | 1.0 |

## Joint scene × emotion

Rows with both labels: 0. Approach B was used (no EmoSet scene metadata; approval N1 not given), so no image carries both labels and there is no joint table.

## EmoSet-derived scene labels

Before the audit: 0. After the audit: 0 (approach B).

## PV-Test

Pending: no team photos or annotation sheets yet (`pv_test_v1.jsonl` not built).
