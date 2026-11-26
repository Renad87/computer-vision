# Visual module - evaluation results

Model version: `visual-1.0.0+clip-vitb32-openai+scene16bg+tags34+yolov8n`

All numbers are computed by `evaluate.py` on held-out splits (never used for training or calibration).

## Scene classification (16 classes, Places365 test split)

| Model | Accuracy (95% CI) | Macro-F1 | Top-3 acc | n |
|---|---|---|---|---|
| zero_shot_clip (no training) | 0.766 (0.737-0.795) | 0.761 | 0.952 | 860 |
| mobilenetv2_imagenet + trained head | 0.678 (0.645-0.709) | 0.669 | 0.908 | 860 |
| clip_vitb32 + trained head, 16 classes | 0.810 (0.784-0.835) | 0.805 | 0.973 | 860 |
| clip_vitb32 + trained head + background class (deployed) | 0.805 (0.776-0.831) | 0.806 | 0.976 | 860 |

Per-class (deployed head):

| class | precision | recall | F1 | n |
|---|---|---|---|---|
| desert | 0.88 | 0.82 | 0.84 | 60 |
| sea_coast | 0.80 | 0.87 | 0.83 | 60 |
| mountains_valleys | 0.55 | 0.50 | 0.52 | 60 |
| rivers_lakes | 0.76 | 0.78 | 0.77 | 60 |
| forest | 0.81 | 0.80 | 0.81 | 60 |
| garden | 0.89 | 0.83 | 0.86 | 60 |
| farmland_rural | 0.84 | 0.87 | 0.85 | 60 |
| sky | 0.63 | 0.60 | 0.62 | 20 |
| snow_ice | 0.86 | 0.90 | 0.88 | 60 |
| modern_city | 0.76 | 0.85 | 0.80 | 60 |
| old_city_market | 0.84 | 0.80 | 0.82 | 60 |
| historic_monument | 0.87 | 0.77 | 0.81 | 60 |
| place_of_worship | 0.86 | 0.83 | 0.85 | 60 |
| home_interior | 0.93 | 0.93 | 0.93 | 60 |
| camp_tents | 0.88 | 0.75 | 0.81 | 20 |
| library_books | 0.97 | 0.80 | 0.88 | 40 |

Top confusions: desert -> mountains_valleys (8); place_of_worship -> modern_city (6); old_city_market -> modern_city (6); mountains_valleys -> snow_ice (6); mountains_valleys -> rivers_lakes (6); mountains_valleys -> sea_coast (5); modern_city -> old_city_market (5); library_books -> (other) (5); sky -> sea_coast (4); mountains_valleys -> forest (4)

In-taxonomy test images predicted as the background class: 18

## Rejection of out-of-taxonomy scenes (`supported`)

Held-out set: 20 Places365 categories never used in training (600 images). Threshold keeps 95% of in-taxonomy validation images.

| head | AUROC | in-taxonomy accepted | accuracy on accepted | out-of-taxonomy rejected |
|---|---|---|---|---|
| deployed (with background class) | 0.940 | 0.944 | 0.837 | 0.800 |
| without background class | 0.825 | 0.962 | 0.831 | 0.373 |

Most common false accepts (deployed): swimming_pool/indoor -> home_interior (13), parking_lot -> modern_city (10), supermarket -> old_city_market (10), construction_site -> modern_city (7), classroom -> library_books (6), gas_station -> modern_city (5)

## Indoor / outdoor (zero-shot CLIP, Places365 IO labels)

- accuracy 0.939 on 1676 images

## Visual tags (Open Images V7 verified labels, test split)

Before training (zero-shot CLIP): mean AP 0.767, mean F1 0.748. After training (per-tag head): mean AP 0.863, mean F1 0.766.

Validation bar: n_pos>=15, precision>=0.75, recall>=0.5 at the calibrated threshold, and fires on <=40% of generic Places365 test scenes. Negatives are human-verified hard negatives. `fires` = share of 1676 generic Places365 test scenes where the tag is emitted (over-firing check; some scenes legitimately contain trees, clouds, etc.).

| tag | AP zero-shot | AP trained | P | R | F1 | pos/neg | fires | validated |
|---|---|---|---|---|---|---|---|---|
| camel | 0.918 | 0.935 | 0.74 | 0.93 | 0.82 | 45/24 | 0.2% | no - precision/recall below bar |
| horse | 0.779 | 0.947 | 0.89 | 0.85 | 0.87 | 95/76 | 0.6% | yes |
| falcon | 0.884 | 0.920 | 0.80 | 0.89 | 0.85 | 37/38 | 0.0% | yes |
| bird | 0.936 | 0.971 | 0.98 | 0.84 | 0.91 | 115/56 | 0.1% | yes |
| palm_tree | 0.636 | 0.853 | 0.68 | 0.90 | 0.78 | 52/43 | 2.8% | no - precision/recall below bar |
| tree | 0.697 | 0.935 | 0.84 | 0.88 | 0.86 | 744/398 | 51.7% | no - fires on >40% of generic scenes (uninformative) |
| flower | 0.898 | 0.930 | 0.93 | 0.75 | 0.83 | 155/146 | 0.6% | yes |
| rose | 0.678 | 0.786 | 0.60 | 0.66 | 0.62 | 38/48 | 0.0% | no - precision/recall below bar |
| tent | 0.453 | 0.783 | 0.55 | 0.97 | 0.70 | 40/39 | 35.4% | no - precision/recall below bar |
| sword_dagger | 0.664 | 0.712 | 0.58 | 0.47 | 0.52 | 32/31 | 0.0% | no - precision/recall below bar |
| moon | 0.905 | 0.934 | 0.86 | 0.89 | 0.87 | 35/22 | 0.1% | yes |
| stars | 0.853 | 0.896 | 0.85 | 0.66 | 0.74 | 35/20 | 0.1% | yes |
| sun | 0.662 | 0.820 | 0.61 | 0.85 | 0.71 | 39/45 | 0.9% | no - precision/recall below bar |
| candle | 0.724 | 0.864 | 0.71 | 0.78 | 0.74 | 37/46 | 0.0% | no - precision/recall below bar |
| lantern | 0.673 | 0.711 | 0.59 | 0.96 | 0.73 | 45/30 | 37.1% | no - precision/recall below bar |
| fire | 0.759 | 0.847 | 0.69 | 0.77 | 0.73 | 43/35 | 0.0% | no - precision/recall below bar |
| book | 0.705 | 0.814 | 0.53 | 0.94 | 0.68 | 70/72 | 24.8% | no - precision/recall below bar |
| teapot | 0.811 | 0.826 | 0.86 | 0.51 | 0.64 | 37/21 | 0.0% | yes |
| boat_ship | 0.845 | 0.888 | 0.82 | 0.83 | 0.82 | 128/71 | 0.7% | yes |
| sea | 0.855 | 0.968 | 0.94 | 0.86 | 0.90 | 143/64 | 4.4% | yes |
| sand | 0.753 | 0.868 | 0.75 | 0.89 | 0.81 | 102/36 | 12.9% | no - precision/recall below bar |
| mountain | 0.752 | 0.835 | 0.70 | 0.98 | 0.82 | 103/43 | 38.7% | no - precision/recall below bar |
| river | 0.637 | 0.776 | 0.67 | 0.80 | 0.73 | 93/52 | 2.6% | no - precision/recall below bar |
| waterfall | 0.834 | 0.879 | 0.64 | 0.82 | 0.72 | 45/39 | 1.2% | no - precision/recall below bar |
| snow | 0.602 | 0.803 | 0.62 | 0.91 | 0.74 | 82/88 | 6.9% | no - precision/recall below bar |
| rain | 0.678 | 0.771 | 0.49 | 0.95 | 0.65 | 39/42 | 3.7% | no - precision/recall below bar |
| clouds | 0.786 | 0.909 | 0.82 | 0.98 | 0.89 | 197/44 | 62.7% | no - fires on >40% of generic scenes (uninformative) |
| fog | 0.938 | 0.938 | 0.79 | 0.90 | 0.84 | 69/29 | 1.4% | yes |
| mosque | 0.922 | 0.935 | 0.94 | 0.91 | 0.92 | 32/12 | 0.5% | yes |
| castle | 0.797 | 0.860 | 0.85 | 0.49 | 0.62 | 35/19 | 0.5% | no - precision/recall below bar |
| arch | 0.845 | 0.875 | 0.72 | 0.80 | 0.76 | 59/39 | 2.0% | no - precision/recall below bar |
| tower | 0.633 | 0.731 | 0.66 | 0.61 | 0.64 | 67/58 | 2.1% | no - precision/recall below bar |
| road | 0.716 | 0.914 | 0.86 | 0.77 | 0.82 | 137/47 | 13.5% | yes |
| child | 0.840 | 0.913 | 0.84 | 0.73 | 0.78 | 51/31 | 2.5% | yes |

## Objects (YOLOv8n COCO, image-level presence on Open Images verified labels)

conf threshold 0.25

| class | precision | recall | F1 | pos/neg |
|---|---|---|---|---|
| person | 0.97 | 0.89 | 0.93 | 548/362 |
| car | 0.96 | 0.81 | 0.87 | 160/97 |
| dog | 0.79 | 0.89 | 0.83 | 71/45 |
| cat | 0.73 | 0.89 | 0.80 | 45/31 |
| horse | 0.80 | 0.97 | 0.88 | 95/76 |
| bird | 0.90 | 0.87 | 0.89 | 115/56 |
| boat | 0.77 | 0.83 | 0.80 | 114/79 |
| book | 0.73 | 0.43 | 0.54 | 70/72 |

## Latency (CPU): median 0.218 s per image (first call incl. model loading 5.31 s)
