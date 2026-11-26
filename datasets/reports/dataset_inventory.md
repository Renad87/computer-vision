# Dataset inventory (v1)

Every number below was measured on the delivered files (bytes as delivered, never re-encoded).

## Input archives

| role | file | SHA-256 | bytes |
|---|---|---|---|
| S1 places_manifest.csv | external/shaden_visual/data/places_manifest.csv | `dfd29aea3310ffe7f14a2ad596bc94bc8f863c0d43acc0080b6195fd51de1f92` | 542806 |
| S6 IO_places365.txt | external/shaden_visual/data/raw/places365/IO_places365.txt | `49f8c7fbeeb70deb055c040a1807a95b234bbac92902e1b6edfffbdd8411e1f1` | 6214 |
| S3 places_clip.npz (near-duplicate search only) | external/shaden_visual/data/features/places_clip.npz | `363b684b1a34cca8b67fd162c849fe5ec1e0818262081055cc69edf6fe323fcf` | 11440329 |
| R1 emoset.zip (Renad) | external/renad/emoset.zip | `df604d10fd825dd0d9761e8ccda26c3e7859a2c517f64eae06900f359eb13693` | 160925142 |
| CLIP embeddings (near-duplicate search only) | datasets/cache/clip_embeddings.npz | `7fd2f960ee4abd9b1e201042350d8d6352af164993a365344b688adf27d5a100` | 35764586 |

## emoset118k

- files: 9200; decoded: 9200; undecodable: 0
- width min/median/max: 90/256.0/256; height: 65/192.0/256
- smaller than 64 px: 0
- colour modes: {'RGB': 9200}; formats: {'JPEG': 9200}; extension/format mismatches: 0
- file size (bytes) min/median/max: 4370/17183.0/45110

Files per split and class:

| class | train | val | test | total |
|---|---|---|---|---|
| img_emotion.amusement | 600 | 150 | 400 | 1150 |
| img_emotion.anger | 600 | 150 | 400 | 1150 |
| img_emotion.awe | 600 | 150 | 400 | 1150 |
| img_emotion.contentment | 600 | 150 | 400 | 1150 |
| img_emotion.disgust | 600 | 150 | 400 | 1150 |
| img_emotion.excitement | 600 | 150 | 400 | 1150 |
| img_emotion.fear | 600 | 150 | 400 | 1150 |
| img_emotion.sadness | 600 | 150 | 400 | 1150 |
| **total** | 4800 | 1200 | 3200 | 9200 |

## places365_sample

- files: 5980; decoded: 5980; undecodable: 0
- width min/median/max: 256/256.0/256; height: 256/256.0/256
- smaller than 64 px: 0
- colour modes: {'L': 14, 'RGB': 5966}; formats: {'JPEG': 5980}; extension/format mismatches: 0
- file size (bytes) min/median/max: 2799/13408.0/28733

Files per split and class:

| class | train | val | test | ood_test | total |
|---|---|---|---|---|---|
| excluded_ood | 0 | 0 | 0 | 600 | 600 |
| scene.camp_tents | 60 | 20 | 20 | 0 | 100 |
| scene.desert | 180 | 60 | 60 | 0 | 300 |
| scene.farmland_rural | 180 | 60 | 60 | 0 | 300 |
| scene.forest | 180 | 60 | 60 | 0 | 300 |
| scene.garden | 180 | 60 | 60 | 0 | 300 |
| scene.historic_monument | 180 | 60 | 60 | 0 | 300 |
| scene.home_interior | 180 | 60 | 60 | 0 | 300 |
| scene.library_books | 120 | 40 | 40 | 0 | 200 |
| scene.modern_city | 180 | 60 | 60 | 0 | 300 |
| scene.mountains_valleys | 180 | 60 | 60 | 0 | 300 |
| scene.old_city_market | 180 | 60 | 60 | 0 | 300 |
| scene.other | 648 | 216 | 216 | 0 | 1080 |
| scene.place_of_worship | 180 | 60 | 60 | 0 | 300 |
| scene.rivers_lakes | 180 | 60 | 60 | 0 | 300 |
| scene.sea_coast | 180 | 60 | 60 | 0 | 300 |
| scene.sky | 60 | 20 | 20 | 0 | 100 |
| scene.snow_ice | 180 | 60 | 60 | 0 | 300 |
| **total** | 3228 | 1076 | 1076 | 600 | 5980 |

## Cleaning

- excluded (undecodable or < 64 px): 0 — listed in `excluded_images.jsonl`
- flagged for a visual check (near-black mean luminance < 0.08, near-white > 0.95, or near-uniform std < 0.02; provisional thresholds; kept unless broken): 83 — listed in `flagged_for_visual_check.csv`
  - by flag: {'near_black': 83}
- per-image record (SHA-256, size, mode, luminance): `image_inventory.csv`
