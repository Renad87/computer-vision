# Original preprocessing, statistics and splits (reference)

Read-only facts about the data the earlier modules used. Each section names its source in the original project.
These numbers describe the old files; re-measure the real files you receive and report any difference.

## 1. Places365 sample (Shaden's `prepare_data.py`)

Sources: `references/old_visual_module/prepare_data.py` and `docs/visual_methodology.md` sections 2 and 5.

- **Images:** official Places365 validation images, 256×256, read from the Hugging Face copy `rumenguin/places365-val` (one folder per category), because the MIT server was too slow. When read on 2026-11-25, that card showed an MIT licence field and did not state the images' origin.
- **Selection:** `random.Random(42)`. Each scene class is capped at 300 images, spread over its k Places365 categories: `min(100, ceil(300 / k))` per category. In each category's shuffled file list, the first `round(0.6·n)` go to train, the next `round(0.2·n)` to val and the rest to test.
- **Background (`__other__`):** 36 categories × 30 images, split 18/6/6 per category.
- **OOD (`__ood__`):** 20 categories × 30 images. The old manifest marks them `test`; the new manifest uses `ood_test`.
- **Storage:** files are stored as downloaded and only checked with a PIL decode. They are not re-encoded.
- **Indoor/outdoor:** from `IO_places365.txt` (the `io` column). The raw label files come from `github.com/CSAILVision/places365` (methodology section 11).
- **Output:** `data/places_manifest.csv` with columns `path,label,places_class,io,split`. Paths are Windows-style, relative to `ml/visual/`.

Expected counts per scene class (computed from the formula and the taxonomy v1 lists; they add up to the EDA totals below):

| Scene | Arabic | Places365 categories (k) | Per category | Total | train | val | test |
|---|---|---|---|---|---|---|---|
| `scene.desert` | صحراء | 3 | 100 | 300 | 180 | 60 | 60 |
| `scene.sea_coast` | بحر وشاطئ | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.mountains_valleys` | جبال ووديان | 5 | 60 | 300 | 180 | 60 | 60 |
| `scene.rivers_lakes` | أنهار وبحيرات وشلالات | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.forest` | غابة | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.garden` | حديقة وبستان | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.farmland_rural` | حقول وريف | 5 | 60 | 300 | 180 | 60 | 60 |
| `scene.sky` | سماء | 1 | 100 | 100 | 60 | 20 | 20 |
| `scene.snow_ice` | ثلج وجليد | 3 | 100 | 300 | 180 | 60 | 60 |
| `scene.modern_city` | مدينة حديثة | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.old_city_market` | مدينة قديمة وسوق | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.historic_monument` | قلاع وقصور وآثار | 5 | 60 | 300 | 180 | 60 | 60 |
| `scene.place_of_worship` | دور عبادة | 3 | 100 | 300 | 180 | 60 | 60 |
| `scene.home_interior` | داخل المنزل | 4 | 75 | 300 | 180 | 60 | 60 |
| `scene.camp_tents` | مخيم وخيام | 1 | 100 | 100 | 60 | 20 | 20 |
| `scene.library_books` | مكتبة وكتب | 2 | 100 | 200 | 120 | 40 | 40 |
| **16 scenes** | | 56 | | 4,300 | 2,580 | 860 | 860 |

Per-category expected counts are in `places365_category_mapping.csv`.

## 2. Statistics printed by the original EDA notebook (`eda_preprocessing.ipynb`, not included)

| Group | train | val | test | total |
|---|---|---|---|---|
| taxonomy (16 classes) | 2,580 | 860 | 860 | 4,300 |
| background (training "other") | 648 | 216 | 216 | 1,080 |
| held-out OOD (test only) | 0 | 0 | 600 | 600 |
| all Places365 rows | 3,228 | 1,076 | 1,676 | 5,980 |

- **Rows:** Places365 5,980; Open Images 4,677.
- **Imbalance:** the ratio across the 16 scene classes (largest / smallest) is 3.0, that is 300 / 100.
- **Sizes:**
  - Places365: all 5,980 images are 256×256.
  - Open Images, resized to a long side ≤ 640: width mean 608 (min 256, max 640), height mean 492 (min 166, max 640). 76% landscape, 17% portrait.
- **Quality checks on 10,657 files:**
  - exact duplicate files (MD5): 0 groups, so 0 across splits;
  - grayscale images: 1 in Places365, 1 in Open Images;
  - near-black images (brightness < 0.08): 114, kept on purpose (night scenes);
  - source colour modes: RGB 10,643, L 14;
  - every file decodes.
- **Feature space (CLIP class centroids):**
  - most similar pairs: rivers_lakes ~ forest 0.949, desert ~ mountains_valleys 0.949, mountains_valleys ~ snow_ice 0.945, historic_monument ~ place_of_worship 0.945, mountains_valleys ~ rivers_lakes 0.944, forest ~ farmland_rural 0.941;
  - silhouette (cosine): CLIP 0.053, MobileNetV2 0.027.

## 3. Original held-out results (context only; not targets for data preparation)

From `results/metrics.json` and Renad's `results/metrics.json`:

| Model | Test set | Result |
|---|---|---|
| CLIP ViT-B/32 + scene head with background class (deployed) | Places365 test, 860 images | accuracy 0.8047, macro-F1 0.8056, top-3 0.9756 |
| CLIP zero-shot | same 860 images | accuracy 0.7663, macro-F1 0.7609 |
| Scene rejection (deployed) | 860 in-taxonomy vs 600 OOD | AUROC 0.9399, OOD rejected 0.80 |
| Renad's ResNet50, fine-tuned | EmoSet sample test, 3,200 images | accuracy 0.6519 (2,086 of 3,200), macro-F1 0.6526 |

## 4. EmoSet sample (Renad's notebook)

Source: `references/old_emotion_module/emoset_sampling_cells.md`, copied verbatim.

- **Streaming:** `load_dataset('Woleek/EmoSet-118K', split=…, streaming=True)` over the mirror's `train`, `val` and `test` splits, then `shuffle(seed=42, buffer_size=2000)`.
- **Selection:** the first 600 / 150 / 400 images per emotion in stream order.
- **Image processing:**
  1. decode with `draft('RGB', (512, 512))`;
  2. convert to RGB;
  3. `thumbnail((256, 256))`, which only shrinks and keeps the aspect ratio;
  4. save as JPEG quality 90 at `emoset/<split>/<emotion>/<image_id>.jpg`;
  5. zip as `emoset.zip`.
- **Printed counts:** 600 per emotion in train, 150 in val and 400 in test. The Keras loader found 4,800 / 1,200 / 3,200 files in 8 classes.
- **Reproducibility:** the streaming shuffle may select different images in another environment. Renad's original zip is the reference data.

## 5. CLIP preprocessing used by the new model (applied at load time, never to stored files)

`open_clip` 4.2.2 evaluation transform for `ViT-B-32-quickgelu` (`image_size` 224), as printed by the EDA notebook and in the project environment:

1. `Resize(224, bicubic, antialias)` on the shorter side;
2. `CenterCrop(224)`;
3. convert to RGB;
4. `ToTensor`;
5. `Normalize(mean=(0.48145466, 0.4578275, 0.40821073), std=(0.26862954, 0.26130258, 0.27577711))`.

- **Embedding:** 512 values, L2-normalized.
- **Augmentation:** none in the original work. The backbone is frozen and features are cached.
- **Old inference decode:** EXIF orientation fixed, converted to RGB, images below 32 px rejected. The data contract requires at least 64 px for dataset images.
- **Cropping:** CLIP sees only the central square, so the sides of wide images are dropped.
