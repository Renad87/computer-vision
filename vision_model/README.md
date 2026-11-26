# vision_model: PoetryVisionNet v1 (Stage 1)

One frozen CLIP ViT-B/32 (`ViT-B-32-quickgelu`, OpenAI weights) computes one 512-d L2-normalised embedding per image. Three linear heads read that embedding:

| Head | Output | Origin | Status |
|---|---|---|---|
| scene | 17-way softmax (16 scenes + `scene.other`) | Shaden's `scene_head_clip.npz`, reordered to the taxonomy | reused; temperature 0.890 and rejection threshold 0.385 fitted on Places val by `scene_eval.py` |
| emotion | 8-way softmax | trained here by `train_emotion.py` on Shaden's `manifest_v0.9_emotion.jsonl` | trained; temperature 0.776 |
| tags | 34 linear scores, 13 exposed | Shaden's `tag_heads.npz` and per-tag thresholds | reused |

The CLIP weights are loaded offline from the previous project's Hugging Face cache, and their sha256 is checked. They are never copied. Everything runs from the project `.venv` (Python 3.12).

## Commands

```bash
.venv/bin/python -B -m vision_model.features emoset --device mps
```
Builds the embedding cache `artifacts/features/emoset_clip_vitb32.npz`.

```bash
.venv/bin/python -B -m vision_model.train_emotion --manifest datasets/manifests/manifest_v0.9_emotion.jsonl
```
Trains the emotion head, fits its temperature and scores test once.

```bash
.venv/bin/python -B -m vision_model.scene_eval --manifest datasets/manifests/manifest_v1.jsonl
```
Builds the Places365 embedding cache and fits and evaluates the scene head's temperature and threshold.

```bash
.venv/bin/python -B -m vision_model.evaluate --manifest datasets/manifests/manifest_v0.9_emotion.jsonl --split test
```
Re-scores a saved head.

```bash
.venv/bin/python -B -m vision_model.model_card
```
Writes `artifacts/model_card_v1.json` and validates it against the contract.

```bash
.venv/bin/python -B -m vision_model.compat
```
Writes `evaluation/vision/compat_report.json`.

```bash
.venv/bin/python -B -m vision_model.benchmark
```
Writes `evaluation/vision/benchmark_arm64.json`.

```bash
.venv/bin/python -B -m unittest discover -s tests -t .
```
Runs the tests (13 in `tests/vision_model/`; they skip under a stdlib-only Python).

## Emotion-head protocol

The protocol is fixed in code before any real run.

- **Gate:** training refuses any manifest that fails `contracts.validate image_manifest` in production mode.
- **Data:** labels come from the manifest, not from folder names. Every image must match the cache by sha256.
- **Model:** multinomial logistic regression with `C` chosen from a 9-value grid by validation macro-F1.
- **Calibration:** temperature fitted on validation NLL.
- **Test:** the test split is scored once.
- **Reporting:** accuracy and macro-F1 with bootstrap 95% intervals, plus NLL, ECE and Brier before and after calibration.

## Measured on this machine (2026-11-26, Apple M5, 16 GB)

- **Embedding cache:**
  - 9,200 EmoSet images in 45.9 s on MPS (200 images/s), including decode;
  - norms 1 ± 2e-7.
- **CPU vs MPS:** minimum cosine 0.9999998 and maximum absolute difference 8.1e-6, over 256 images.
- **Per device:**

| | CPU | MPS |
|---|---|---|
| model load | 3.3 s | 1.0 s |
| forward, 1 image (median / p95) | 17.7 / 18.2 ms | 9.1 / 10.0 ms |
| forward, batch 64 | 136 images/s | 227 images/s |
| decode + preprocess | 0.8 ms/image | 0.7 ms/image |

- **Heads:** 0.007 ms per image.
- **Memory:** peak process RSS 1.67 GB; MPS driver memory 1.54 GB.
- **Reused heads:** their outputs equal the previous module's exactly (maximum difference 0.0). The preprocessing matches the contract.
- **Scene agreement:** the reused scene head agrees with EmoSet's official scene attribute on 82.1% of 688 train/val images that have a mapped scene.
  - This is agreement, not accuracy: EmoSet's scene is itself a Places365 model's prediction and is unaudited.
  - Test images were not used.

## Stage 1 results (2026-11-26)

Every number below comes from the run reports in `evaluation/vision/`.

**Emotion head** (run `emotion-s1-20261125T220720Z-efd7de`):
- Data: `manifest_v0.9_emotion.jsonl` (sha256 `7df0416f…`), 4,800 train / 1,200 val / 3,200 test.
- Model: C = 3 (chosen on val macro-F1), temperature 0.776.
- Test results:

| Metric | Value |
|---|---|
| accuracy | 0.783 (95% CI 0.770–0.798) |
| macro-F1 | 0.784 (0.770–0.798) |
| top-2 accuracy | 0.921 |
| ECE (15 bins), before → after temperature | 0.055 → 0.022 |
| NLL, before → after | 0.621 → 0.599 |

- Gate A2 (macro-F1 ≥ 0.603): passed.
- Comparison: Renad's ResNet50 scored 0.6526 macro-F1 on the same 3,200 test images.
- Per-class test F1:

| Class | F1 |
|---|---|
| anger | 0.871 |
| disgust | 0.850 |
| awe | 0.814 |
| excitement | 0.802 |
| sadness | 0.785 |
| fear | 0.764 |
| amusement | 0.695 |
| contentment | 0.692 |

**Scene head** (run `scene-s1-20261125T220832Z-f1bbea`):
- Data: `manifest_v1.jsonl`, Places365 sample rows.
- Leakage check: 0 split differences from the split the reused head was trained on. The 600 old test rows marked OOD now sit in `ood_test`.

| Measurement | Value |
|---|---|
| test, 16 scenes (n = 860), 17-way argmax: accuracy / macro-F1 | 0.8047 / 0.8056 (CI 0.776–0.831); exactly the previous module's published values |
| gate A1 (≥ 0.776) | passed |
| test, all 17 classes incl. background (n = 1,076): accuracy / macro-F1 | 0.802 / 0.788 |
| temperature (val) | 0.890 |
| ECE, before → after | 0.054 → 0.042 |
| rejection threshold, after temperature (95% of in-taxonomy val kept) | 0.385 |
| AUROC, in-taxonomy test vs 600 OOD images | 0.941 |
| OOD rejected | 79.7% |
| background test images rejected | 80.6% |
| in-taxonomy test images kept | 94.4% |

- Embeddings equal Shaden's `places_clip.npz` (minimum cosine 0.9999998 over 5,980 images).

**Tag head:** not re-measured here; it keeps the previous module's thresholds.
