# PoetryVisionNet v1.0.0: integration handoff

Generated from the run reports in `evaluation/vision/`. Status: released by the project owner on 2026-11-26.

- **Architecture:** Stage 1 is final for this submission, and Stage 2 is future work.
- **Frozen:** no retraining and no re-extraction. The classifier, calibration and thresholds are fixed.

## 1. What it is

One frozen CLIP ViT-B/32 image encoder (`ViT-B-32-quickgelu`, `openai` weights) produces one 512-d L2-normalised embedding per image. Three linear heads read that same embedding:

| head | output | activation | origin | temperature |
|---|---|---|---|---|
| scene | 17 classes (16 scenes + `scene.other`) | softmax / T | reused from the previous visual module | 0.889981 |
| emotion | 8 image emotions | softmax / T | trained in this workspace (run `emotion-s1-20261125T220720Z-efd7de`) | 0.775623 |
| tags | 34 scores, 13 exposed | linear score ≥ per-tag threshold | reused from the previous visual module | none |

There is one model: no YOLO, no ResNet50 and no LLM at runtime.

## 2. Artifacts and checksums

All paths are relative to the workspace root. The previous project is reached through the symlink `external/poetry_vision_old`; it is read-only.

| artifact | path | bytes | sha256 |
|---|---|---|---|
| CLIP ViT-B/32 weights (read in place, never copied) | `external/poetry_vision_old/product/models/hf/models--timm--vit_base_patch32_clip_224.openai/snapshots/a6f597a30f7b82c51704746581f9a4e41421e878/open_clip_model.safetensors` | 605,143,284 | `e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31` |
| scene head W,b (reused) | `external/poetry_vision_old/product/vendor/visual_module/ml/visual/weights/scene_head_clip.npz` | 36,776 | `f39e083cfa639616563a0cd53f62fa9139558c991b9a0f44b6f0cef1c45cd376` |
| tag head W,b (reused) | `external/poetry_vision_old/product/vendor/visual_module/ml/visual/weights/tag_heads.npz` | 72,128 | `a94f7d145af7f4789383c9ba5583d382842ec53142fdbf457573118a9be5384a` |
| tag thresholds, previous scene threshold (reused) | `external/poetry_vision_old/product/vendor/visual_module/ml/visual/weights/calibration.json` | 11,730 | `873497a35cbae6486988c7781e7ca6a4350dd239948d4c4cdbc01a521978d1df` |
| emotion head W,b,T (trained here) | `artifacts/heads/emotion_head_v1.npz` | 19,490 | `328ec7416afc3bf11045db4291b2cc6680e5c4549a4de062575862f66e9a1c95` |
| scene temperature + rejection threshold (fitted here) | `artifacts/heads/scene_calibration_v1.json` | 319 | `e875a3596ec1e59cc2729936504d421547bc055dec5182892c487b020e33df89` |
| model card v1.0.0 (released) | `artifacts/model_card_v1.json` | 8,442 | `8d4f8622be4548e6707b9baf3fa4a4167583df2216ae2f52bc6fe446b256552d` |
| EmoSet embedding cache | `artifacts/features/emoset_clip_vitb32.npz` | 24,657,508 | `12598f71f459708282c16e1517770085d811ad5414695327234cd96db216e755` |
| Places365 embedding cache | `artifacts/features/places_clip_vitb32.npz` | 14,998,840 | `60fd5fe7552eaa386ccc4d478c7c1fe0abe51f9cd48c0466b3de713da933d146` |
| emotion run report | `evaluation/vision/emotion-s1-20261125T220720Z-efd7de.json` | 7,110 | `1b56a8a9d7eb1e29975bccffc590bf0983ea66401c3e50f25c15c49a0e46fe1e` |
| scene run report | `evaluation/vision/scene-s1-20261125T220832Z-f1bbea.json` | 6,742 | `26fbfd36e76da55a21d15ace246bfd068291f83e2c566fa109bd204301ba579c` |
| compatibility report | `evaluation/vision/compat_report.json` | 2,657 | `8bb8fa92a1c20d57682640c279296aa3ceaf8fd893eb85cd41bac18ac91089d2` |
| benchmark report | `evaluation/vision/benchmark_arm64.json` | 975 | `91e6f12a31d3a23af2e4a6645b2396fba32c7845419090f814347a7b505493db` |
| emotion manifest v0.9 (Shaden) | `datasets/manifests/manifest_v0.9_emotion.jsonl` | 12,463,985 | `7df0416fbeb6e9810cc2b3fff4b6cad09600552661bd8beb7a7b5bd4428c0892` |
| unified manifest v1 (Shaden) | `datasets/manifests/manifest_v1.jsonl` | 19,583,297 | `efdf33b153a900ecf3524569907b316b349e4860bab249d10b6efd630310b501` |

Every load checks the CLIP weights and the three reused head files against these sha256 values (`vision_model/config.py`).

## 3. Public inference interface

```python
from contracts.taxonomy import load_taxonomy
from vision_model.model import load_default

net = load_default(load_taxonomy(), device="auto")   # "mps" on Apple silicon, else "cpu"
doc = net.analyze(image_bytes)                      # dict = contracts `inference_output` v1.0.0
```

- **`load_default(taxonomy, device="auto")`:** loads CLIP offline, the reused scene and tag heads, the trained emotion head, and the scene temperature and threshold. It takes about 1 s on MPS and 3.3 s on CPU. Create the model once per process and reuse it.
- **`net.analyze(image_bytes) -> dict`:** never raises for bad images. It returns either:
  - `status: "ok"`, with `scene`, `scene_groups`, `emotion`, `tags`, `suggested_lit_emotions` and `timings_ms`; or
  - `status: "error"`, with `error.code` (`invalid_image`, `unsupported_format` or `too_small`) and `error.message_ar`.
- **`net.outputs_from_embedding(z)`:** the same prediction blocks from a cached 512-d embedding, with no image input or output.
- **`net.model_version`:** `1.0.0`, read from the model card.
- **Validation:** every document validates against `contracts.validate inference_output`. The tests in `tests/vision_model/` check this.
- **Concurrency:** one torch model per process. Serialise calls with a lock if the web server runs requests in threads.

## 4. Preprocessing (identical to the contract)

1. Decode the bytes, apply the EXIF orientation, convert to RGB. Images with a shorter side under 32 px are rejected as `too_small`.
2. Resize the shorter side to 224 (bicubic, antialias), then centre-crop 224×224.
3. Convert to a tensor; normalise with mean `[0.48145466, 0.4578275, 0.40821073]` and std `[0.26862954, 0.26130258, 0.27577711]`.
4. Run CLIP `encode_image` in fp32, then L2-normalise.

This is open_clip 4.2.2's own evaluation transform, checked in `compat_report.json` (`matches_contract: True`).

## 5. Class orderings (taxonomy v1.0.0)

- **scene (17):** `scene.desert`, `scene.sea_coast`, `scene.mountains_valleys`, `scene.rivers_lakes`, `scene.forest`, `scene.garden`, `scene.farmland_rural`, `scene.sky`, `scene.snow_ice`, `scene.modern_city`, `scene.old_city_market`, `scene.historic_monument`, `scene.place_of_worship`, `scene.home_interior`, `scene.camp_tents`, `scene.library_books`, `scene.other`
- **emotion (8):** `img_emotion.amusement`, `img_emotion.awe`, `img_emotion.contentment`, `img_emotion.excitement`, `img_emotion.anger`, `img_emotion.disgust`, `img_emotion.fear`, `img_emotion.sadness`
- **tags (34):** `tag.camel`, `tag.horse`, `tag.falcon`, `tag.bird`, `tag.palm_tree`, `tag.tree`, `tag.flower`, `tag.rose`, `tag.tent`, `tag.sword_dagger`, `tag.moon`, `tag.stars`, `tag.sun`, `tag.candle`, `tag.lantern`, `tag.fire`, `tag.book`, `tag.teapot`, `tag.boat_ship`, `tag.sea`, `tag.sand`, `tag.mountain`, `tag.river`, `tag.waterfall`, `tag.snow`, `tag.rain`, `tag.clouds`, `tag.fog`, `tag.mosque`, `tag.castle`, `tag.arch`, `tag.tower`, `tag.road`, `tag.child`
- **exposed tags (13):** `tag.horse`, `tag.falcon`, `tag.bird`, `tag.flower`, `tag.moon`, `tag.stars`, `tag.teapot`, `tag.boat_ship`, `tag.sea`, `tag.fog`, `tag.mosque`, `tag.road`, `tag.child`

## 6. Calibration, thresholds and decision rules

| parameter | value | fitted on |
|---|---|---|
| scene temperature T | 0.889981156 | Places365 sample val, 17-way NLL (n=1076) |
| emotion temperature T | 0.775623070 | EmoSet sample val NLL (n=1200) |
| emotion classifier | multinomial logistic regression, C = 3.0 | C chosen on val macro-F1 |
| scene rejection threshold | 0.384658873 | Places365 sample val, in-taxonomy images (n=860), after temperature; keeps 95% of in-taxonomy val |
| scene rule | `supported` = max in-taxonomy probability of the 17-way softmax (other excluded, not renormalised) ≥ threshold | contract |
| scene status | `unsupported` if not supported; `uncertain` if top1 − top2 < 0.1; else `confident` | fixed |
| emotion status | `ambiguous` if top1 − top2 < 0.15; else `clear` | fixed |
| literary suggestions | `suggestion_map` of each top-2 image emotion with p ≥ 0.15 (basis `mapping_v1`, no score) | fixed |
| tag decision | `present` = linear score ≥ the tag's threshold | previous module |

Scene probabilities and `scene_groups` (sums of member scenes) are reported after temperature.

## 7. Loading and runtime

```bash
.venv/bin/python -B -c "from contracts.taxonomy import load_taxonomy; from vision_model.model import load_default; print(load_default(load_taxonomy()).model_version)"
```

- **Environment:** the project `.venv` (Python 3.12.15).
- **Offline:** `vision_model.config` sets `HF_HUB_CACHE` to the previous project's cache and `HF_HUB_OFFLINE=1` before importing open_clip. No network access is needed.
- **Overrides:** `PV_OLD_PROJECT` (previous project root) and `PV_HF_CACHE` (Hugging Face cache).
- **Runtime dependencies (pinned in `requirements.txt`):** torch 2.15.0, torchvision 0.29.2, open_clip_torch 4.2.2, numpy 2.5.5, pillow 12.3.0, safetensors 0.8.0, huggingface_hub 2.4.0.
  - scipy and scikit-learn are needed only for training and calibration; `load_default` imports neither.
  - The `contracts/` package uses the standard library only.
- **Files needed at runtime:** the CLIP weights, `scene_head_clip.npz`, `tag_heads.npz` and `calibration.json` (previous project), plus `artifacts/heads/emotion_head_v1.npz`, `artifacts/heads/scene_calibration_v1.json` and `artifacts/model_card_v1.json`.

## 8. Evaluation results (measured in this workspace)

### Emotion head: EmoSet sample test, n = 3200 (400 per class), scored once

| metric | value |
|---|---|
| accuracy | 0.7834 (95% bootstrap CI 0.770–0.798) |
| macro-F1 | 0.7841 (0.770–0.798) |
| top-2 accuracy | 0.9213 |
| NLL before → after T | 0.6211 → 0.5994 |
| ECE (15 bins) before → after T | 0.0552 → 0.0223 |
| Brier before → after T | 0.3097 → 0.3053 |

- Validation (n=1200): accuracy 0.7875, macro-F1 0.7887.
- Gate A2 (macro-F1 ≥ 0.603): **passed**.

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| amusement | 0.703 | 0.688 | 0.695 | 400 |
| awe | 0.836 | 0.792 | 0.814 | 400 |
| contentment | 0.651 | 0.738 | 0.692 | 400 |
| excitement | 0.799 | 0.805 | 0.802 | 400 |
| anger | 0.888 | 0.855 | 0.871 | 400 |
| disgust | 0.831 | 0.870 | 0.850 | 400 |
| fear | 0.779 | 0.750 | 0.764 | 400 |
| sadness | 0.800 | 0.770 | 0.785 | 400 |

Confusion matrix (test; rows are the true class):

| true \ pred | amusement | awe | contentment | excitement | anger | disgust | fear | sadness |
|---|---|---|---|---|---|---|---|---|
| **amusement** | 275 | 10 | 63 | 33 | 3 | 5 | 9 | 2 |
| **awe** | 14 | 317 | 34 | 14 | 5 | 2 | 3 | 11 |
| **contentment** | 42 | 28 | 295 | 10 | 3 | 2 | 2 | 18 |
| **excitement** | 42 | 9 | 19 | 322 | 7 | 0 | 0 | 1 |
| **anger** | 2 | 3 | 8 | 15 | 342 | 1 | 16 | 13 |
| **disgust** | 5 | 0 | 1 | 0 | 5 | 348 | 34 | 7 |
| **fear** | 7 | 4 | 4 | 6 | 9 | 45 | 300 | 25 |
| **sadness** | 4 | 8 | 29 | 3 | 11 | 16 | 21 | 308 |

### Scene head: Places365 sample

The leakage check found 0 split differences from the split the reused head was trained on. The 600 old test rows that are OOD now sit in `ood_test`.

| metric | value |
|---|---|
| 16 in-taxonomy scenes, n = 860: accuracy / macro-F1 (17-way argmax) | 0.8047 / 0.8056; identical to the previous module's published values |
| same images, argmax over the 16 scenes only | accuracy 0.8140 / macro-F1 0.8067 |
| all 17 classes incl. background, n = 1076: accuracy | 0.8020 (0.778–0.826) |
| all 17 classes: macro-F1 | 0.7883 (0.760–0.814) |
| all 17 classes: top-2 accuracy | 0.9229 |
| NLL before → after T | 0.6673 → 0.6558 |
| ECE before → after T | 0.0541 → 0.0418 |
| AUROC, in-taxonomy test vs 600 OOD images | 0.9406 |
| OOD rejected / background rejected / in-taxonomy kept | 79.7% / 80.6% (n=216) / 94.4% |

Gate A1 (macro-F1 ≥ 0.776 on the 860 images): **passed** (0.8056).

| class | precision | recall | F1 | support |
|---|---|---|---|---|
| desert | 0.875 | 0.817 | 0.845 | 60 |
| sea_coast | 0.765 | 0.867 | 0.812 | 60 |
| mountains_valleys | 0.545 | 0.500 | 0.522 | 60 |
| rivers_lakes | 0.758 | 0.783 | 0.770 | 60 |
| forest | 0.787 | 0.800 | 0.793 | 60 |
| garden | 0.862 | 0.833 | 0.847 | 60 |
| farmland_rural | 0.754 | 0.867 | 0.806 | 60 |
| sky | 0.600 | 0.600 | 0.600 | 20 |
| snow_ice | 0.831 | 0.900 | 0.864 | 60 |
| modern_city | 0.729 | 0.850 | 0.785 | 60 |
| old_city_market | 0.727 | 0.800 | 0.762 | 60 |
| historic_monument | 0.821 | 0.767 | 0.793 | 60 |
| place_of_worship | 0.833 | 0.833 | 0.833 | 60 |
| home_interior | 0.812 | 0.933 | 0.868 | 60 |
| camp_tents | 0.833 | 0.750 | 0.789 | 20 |
| library_books | 0.941 | 0.800 | 0.865 | 40 |
| other | 0.905 | 0.792 | 0.844 | 216 |

Confusion matrix (test, 17 classes; rows are the true class):

| true \ pred | desert | sea_coast | mountains_valleys | rivers_lakes | forest | garden | farmland_rural | sky | snow_ice | modern_city | old_city_market | historic_monument | place_of_worship | home_interior | camp_tents | library_books | other |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **desert** | 49 | 1 | 8 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **sea_coast** | 0 | 52 | 2 | 2 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 |
| **mountains_valleys** | 4 | 5 | 30 | 6 | 4 | 0 | 2 | 2 | 6 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 |
| **rivers_lakes** | 0 | 3 | 3 | 47 | 0 | 2 | 0 | 0 | 2 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 0 |
| **forest** | 0 | 0 | 3 | 3 | 48 | 3 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| **garden** | 0 | 0 | 1 | 1 | 2 | 50 | 2 | 0 | 0 | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 1 |
| **farmland_rural** | 0 | 0 | 3 | 0 | 3 | 0 | 52 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **sky** | 0 | 4 | 1 | 1 | 0 | 0 | 1 | 12 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| **snow_ice** | 1 | 0 | 3 | 0 | 0 | 0 | 0 | 1 | 54 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| **modern_city** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 51 | 5 | 0 | 1 | 0 | 0 | 0 | 3 |
| **old_city_market** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 48 | 1 | 0 | 2 | 1 | 0 | 2 |
| **historic_monument** | 1 | 0 | 1 | 0 | 0 | 0 | 4 | 0 | 0 | 3 | 1 | 46 | 4 | 0 | 0 | 0 | 0 |
| **place_of_worship** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 3 | 50 | 0 | 0 | 0 | 1 |
| **home_interior** | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 56 | 0 | 0 | 2 |
| **camp_tents** | 1 | 0 | 0 | 2 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 15 | 0 | 0 |
| **library_books** | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 32 | 5 |
| **other** | 0 | 3 | 0 | 0 | 2 | 2 | 7 | 1 | 2 | 3 | 9 | 3 | 2 | 9 | 1 | 1 | 171 |

### Compatibility and consistency

- Reused heads reproduce the previous module's outputs exactly: maximum difference 0.0 (scene) and 0.0 (tags).
- CPU vs MPS embeddings: minimum cosine 0.9999998 (n=256).
- Our Places365 embeddings equal Shaden's `places_clip.npz`: minimum cosine 0.9999998 (n=5,980).

## 9. Historical baselines (previous project; not re-run here unless stated)

| system | data | metric | value |
|---|---|---|---|
| Renad ResNet50, fine-tuned (Keras) | same 3200 EmoSet test images | accuracy / macro-F1 | 0.6519 / 0.6526 |
| Renad ResNet50, feature extraction | same | accuracy / macro-F1 | 0.6341 / 0.6321 |
| **PoetryVisionNet emotion head (this work)** | same | accuracy / macro-F1 | **0.7834 / 0.7841** |
| previous scene module: zero_shot_clip (no training) | Places365 test n=860 | accuracy / macro-F1 | 0.7663 / 0.7609 |
| previous scene module: mobilenetv2_imagenet + trained head | Places365 test n=860 | accuracy / macro-F1 | 0.6779 / 0.6692 |
| previous scene module: clip_vitb32 + trained head, 16 classes | Places365 test n=860 | accuracy / macro-F1 | 0.8105 / 0.8047 |
| previous scene module: clip_vitb32 + trained head + background class (deployed) | Places365 test n=860 | accuracy / macro-F1 | 0.8047 / 0.8056 |

The deployed scene row was re-measured here and reproduced exactly (section 8).

### Tag head: historical evaluation only

These numbers come from the previous module's `tag_metrics.json`; they were **not re-measured** in this workspace.

| tag | exposed | historical precision | historical recall | historical F1 | positives / negatives |
|---|---|---|---|---|---|
| camel | no | 0.737 | 0.933 | 0.824 | 45 / 24 |
| horse | yes | 0.890 | 0.853 | 0.871 | 95 / 76 |
| falcon | yes | 0.805 | 0.892 | 0.846 | 37 / 38 |
| bird | yes | 0.980 | 0.844 | 0.906 | 115 / 56 |
| palm_tree | no | 0.681 | 0.904 | 0.777 | 52 / 43 |
| tree | no | 0.843 | 0.875 | 0.859 | 744 / 398 |
| flower | yes | 0.928 | 0.748 | 0.829 | 155 / 146 |
| rose | no | 0.595 | 0.658 | 0.625 | 38 / 48 |
| tent | no | 0.549 | 0.975 | 0.703 | 40 / 39 |
| sword_dagger | no | 0.577 | 0.469 | 0.517 | 32 / 31 |
| moon | yes | 0.861 | 0.886 | 0.873 | 35 / 22 |
| stars | yes | 0.852 | 0.657 | 0.742 | 35 / 20 |
| sun | no | 0.611 | 0.846 | 0.710 | 39 / 45 |
| candle | no | 0.707 | 0.784 | 0.744 | 37 / 46 |
| lantern | no | 0.589 | 0.956 | 0.729 | 45 / 30 |
| fire | no | 0.688 | 0.767 | 0.725 | 43 / 35 |
| book | no | 0.532 | 0.943 | 0.680 | 70 / 72 |
| teapot | yes | 0.864 | 0.513 | 0.644 | 37 / 21 |
| boat_ship | yes | 0.815 | 0.828 | 0.822 | 128 / 71 |
| sea | yes | 0.939 | 0.860 | 0.898 | 143 / 64 |
| sand | no | 0.746 | 0.892 | 0.812 | 102 / 36 |
| mountain | no | 0.701 | 0.981 | 0.818 | 103 / 43 |
| river | no | 0.673 | 0.796 | 0.729 | 93 / 52 |
| waterfall | no | 0.638 | 0.822 | 0.718 | 45 / 39 |
| snow | no | 0.625 | 0.915 | 0.743 | 82 / 88 |
| rain | no | 0.493 | 0.949 | 0.649 | 39 / 42 |
| clouds | no | 0.821 | 0.980 | 0.893 | 197 / 44 |
| fog | yes | 0.795 | 0.899 | 0.844 | 69 / 29 |
| mosque | yes | 0.935 | 0.906 | 0.921 | 32 / 12 |
| castle | no | 0.850 | 0.486 | 0.618 | 35 / 19 |
| arch | no | 0.723 | 0.797 | 0.758 | 59 / 39 |
| tower | no | 0.661 | 0.612 | 0.636 | 67 / 58 |
| road | yes | 0.862 | 0.774 | 0.815 | 137 / 47 |
| child | yes | 0.841 | 0.726 | 0.779 | 51 / 31 |

## 10. Benchmarks (Apple M5, 16 GB, macOS 27.0.1, torch 2.15.0)

| | CPU | MPS |
|---|---|---|
| model load | 3.323 s | 0.998 s |
| decode + preprocess | 0.807 ms/image | 0.709 ms/image |
| forward, 1 image (median / p95) | 17.667 / 18.219 ms | 9.1 / 9.999 ms |
| forward, batch 64 | 136.5 images/s | 227.4 images/s |

- Heads: 0.0072 ms/image. Peak RSS: 1672.4 MB. MPS driver memory: 1538.7 MB.
- End-to-end `analyze()` on MPS: about 10 ms per image after a first warm-up call (about 96 ms).

## 11. Known limitations

- **No PV-Test evaluation.** The independent team photo set (30–40 images, two annotators) has not been collected. Every number above is in-distribution: EmoSet test or Places365 test.
- **Tag head:** only historical evaluation exists (section 9). It was not re-measured here.
- **N1 scene metadata:** the official EmoSet scene attribute is unaudited. It is not used as a training or evaluation label. The 250-image human audit has not been done.
- **Scene head:** reused, not retrained.
  - Weakest classes: `mountains_valleys` (F1 0.52) and `sky` (F1 0.60, only 20 test images).
  - `sky` and `camp_tents` have only 20 test images each.
  - The background class rejection works via the threshold, not via `scene.other` alone.
- **Emotion labels:** EmoSet's crowd consensus on web images. Not validated on Arabic or heritage imagery. Weakest classes: amusement and contentment (F1 about 0.69).
- **Single training run:** the intervals are bootstrap intervals over test images, not over training seeds.
- **Contracts v1.0.0:** still a draft, without sign-off from Shaden or Mohammed.
- **Licences:** none stated for the EmoSet data; Places365 terms are not verified. The model is internal only and must not be published.
- **Dependency on the previous project:** the CLIP weights and the reused heads are read from it. Copy them only with the owner's approval.
- **Open dataset item:** the visual check of the 83 near-black images flagged by Shaden is still open.
