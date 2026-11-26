# Poetry Vision

Poetry Vision suggests authentic classical and modern Arabic verses for a photo. One computer-vision model reads the image (scene, image emotion, visual tags). The user confirms what they see and chooses the literary emotion. A transparent Arabic retrieval engine then returns up to three verses from a curated corpus, each with a deterministic explanation, or abstains and says why.

The app never generates poetry. Every verse is quoted verbatim, with diacritics, from its row in the Arabic Poem Comprehensive Dataset (APCD).

## Features

- One frozen CLIP ViT-B/32 backbone shared by three linear heads: scene (17 classes), image emotion (8), visual tags (13 shown).
- Calibrated probabilities. Out-of-scope scenes are rejected, and unreliable emotion estimates are flagged rather than hidden.
- The user always chooses the literary emotion and the visual focus. Changing them reruns retrieval only (about 1 ms), not the model.
- Hybrid ranking: emotion match, visual match, TF-IDF text similarity, eligibility tiers, diversity rules and abstention.
- Two modes:
  - **production** shows only verses whose labels a human reviewed;
  - **development** shows AI-draft labels with a permanent disclosure.
- Arabic right-to-left web interface (React) served by a FastAPI backend.

## System Architecture

```
image ─► CLIP ViT-B/32 (frozen, 512-d) ─┬─ scene head   (17-way softmax, calibrated, rejection threshold)
                                        ├─ emotion head (8-way softmax, calibrated)
                                        └─ tag head     (34 linear scores, per-tag thresholds)
          ▼
inference_output ─► user confirms visual items + chooses literary emotion ─► image_profile
          ▼
retrieval engine (stdlib Python): Arabic normalization ─► TF-IDF + cosine ─► Score = 0.45E + 0.35V + 0.20T
          ▼                                               tiers · diversity · abstention · explanations
recommendations (≤ 3 verses, or an abstention with a reason)
```

All data passed between components follows the JSON contracts in `contracts/CONTRACTS.md`. The executable validator is `contracts/validate.py`.

## Datasets

| Dataset | Use | Size | In this repository |
|---|---|---|---|
| EmoSet (Yang et al., 2023) | emotion head training and evaluation | 9,200 images (4,800 / 1,200 / 3,200) | manifests and hashes only |
| Places365 (Zhou et al., 2017), sample | scene head calibration and evaluation | 5,980 images (3,228 / 1,076 / 1,076, plus 600 out-of-scope test) | manifests and hashes only |
| APCD (Yousef et al., 2019) | source of every verse text | 1,053 verses selected | verse texts inside the corpus records; the APCD file itself is not included |

- The unified manifest (`datasets/manifests/manifest_v1.jsonl`) records splits, label status (missing labels are explicit, never treated as negatives), near-duplicate checks and provenance.
- See `datasets/DATASET_CARD.md`. Images are not redistributed. Obtain them from the original sources under their terms.

## Model

- **Backbone:** `ViT-B-32-quickgelu` with OpenAI weights (open_clip 4.2.2), frozen, not fine-tuned.
- **Emotion head:** multinomial logistic regression trained on the cached 512-d embeddings.
  - C = 3, chosen by validation macro-F1.
  - Temperature 0.776, fitted on validation.
- **Scene and tag heads:** reused from the team's earlier visual module (`artifacts/heads/reused/`). The scene temperature (0.89) and the rejection threshold (0.385) were refitted on Places365 validation.
- **Training:** the heads were trained independently on the shared frozen features. This is multi-head inference, not joint multi-task training.
- **Tags:** image-level classifiers, not object detection.

Details are in `docs/MODEL_REPORT.md`, `artifacts/model_card_v1.json` and `vision_model/README.md`.

## Poetry Retrieval

- **Code:** `retrieval/`, Python standard library only, engine version 1.1.0.
- **Text:** Arabic normalization; a bag-of-words / smoothed TF-IDF over the verse and its meaning; cosine similarity against query terms expanded from the confirmed visual items.
- **Score:** `Score = 0.45·E + 0.35·V + 0.20·T`, where
  - E is the emotion match (1.0 primary, 0.6 secondary);
  - V is the visual relation weight (literal 1.0, scene association 0.7, symbolic 0.4);
  - T is the TF-IDF cosine.
- **Tiers:** 1 is a visual match, 2 is symbolic (opt-in), 3 is emotion only (opt-in, at most one item).
- **Diversity:** one verse per poem and per poet.
- **Abstention:** the engine abstains with a reason code rather than return an unrelated verse.

Method: `docs/RETRIEVAL_METHOD.md`; report: `retrieval/RETRIEVAL_REPORT.md`.

## Evaluation Results

**Vision.** Measured once on held-out test splits after all choices were frozen on validation.

| Component | Test set | Result |
|---|---|---|
| Emotion head | EmoSet test, n = 3,200 | accuracy 0.783 [0.770, 0.798]; macro-F1 0.784 [0.770, 0.798]; top-2 0.921; ECE 0.055 → 0.022 after temperature |
| Baseline: ResNet50 fine-tuned (earlier team experiment) | same images | macro-F1 0.653 |
| Scene head | Places365 test, n = 1,076 (17-way) | accuracy 0.802; macro-F1 0.788 |
| Scene head | 16 in-scope classes, n = 860 | macro-F1 0.806 |
| Scene rejection | in-scope vs 600 out-of-scope images | AUROC 0.941; 79.7% of out-of-scope images rejected |
| Speed | one image, Apple M5 | 9.1 ms (MPS) / 17.7 ms (CPU) forward pass |

**Emotion diagnosis.** `evaluation/vision/emotion_diagnosis/REPORT.md`.
- On real landscape photos the emotion head usually predicts "awe" (44.6% of Places365 photos). EmoSet labels most landscapes as awe, and the model has no neutral class.
- This is a data convention, not a bug. No validation-selected alternative was better.
- The app therefore flags unreliable estimates and never preselects the literary emotion.

**Retrieval.**
- 6 methods × 24 synthetic development profiles on `corpus_all_v1`. Hybrid result: 20 complete, 3 partial, 1 abstention.
- 0 contract violations; p95 latency 0.89 ms.
- These are coverage diagnostics, not relevance scores: no human relevance judgments have been collected, so no Precision@k or nDCG is reported.
- A behaviour benchmark on 16 real photos is in `evaluation/quality/`.

**Corpus (`corpus_all_v2`).**

| | Verses |
|---|---|
| Total | 1,053 |
| Text verified against the APCD row | 1,053 |
| Attribution verified by an independent source | 16 |
| APCD attribution only | 1,037 |
| Emotion labels reviewed by a human | 35 |
| Visual labels reviewed by a human | 0 |
| Shown in production mode | 35 |

All other labels are AI drafts.

**Tests.** 225 unit and integration tests (`python3 -m unittest discover -s tests -t .`). Tests that need data not distributed here skip with a stated reason.

## Installation

Requirements: Python 3.12, Node.js 18+, and about 1 GB of disk space for the CLIP weights.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd frontend && npm ci && npm run build && cd ..
```

Download the CLIP weights once. The revision is pinned, and the file is sha256-checked at startup:

```bash
.venv/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('timm/vit_base_patch32_clip_224.openai', revision='a6f597a30f7b82c51704746581f9a4e41421e878')"
```

The weights go to `~/.cache/huggingface/hub`, which is the default. If you keep them elsewhere, set `PV_HF_CACHE`.

## Running the Application

```bash
./run.sh
```

- The script checks the environment, model files, corpus and weights, then starts the app at http://127.0.0.1:8010.
- Options:
  - `PV_PORT`: port;
  - `PV_CORPUS`: path to another corpus snapshot;
  - `PV_DEVICE`: `auto`, `mps` or `cpu`;
  - `PV_DEFAULT_MODE`: `production` or `development`.
- The HTTP API is described in `docs/API.md`.
- The presentation (`presentation/Poetry_Vision_Diwan.html`) is a single offline HTML file. Open it in Chrome.

## Project Structure

```
backend/          FastAPI app: loads the model and corpus once, builds profiles and queries, validates every response
frontend/         React + Vite interface (Arabic, right-to-left)
vision_model/     CLIP backbone, heads, emotion-head training, calibration, evaluation, benchmark
artifacts/        trained emotion head, reused scene/tag heads, calibration, model card
retrieval/        retrieval engine (stdlib only)
contracts/        shared JSON contracts, taxonomy and validator
poetry_corpus/    corpus records, AI-draft annotation specs, guidelines, exports, review tooling and pending review sheets
datasets/         dataset manifests, card and data-quality reports (no images)
data_preparation/ dataset build pipeline
evaluation/       vision, retrieval, end-to-end and quality-benchmark results and scripts
tests/            unit and integration tests
fixtures/, references/  synthetic test fixtures and small reference files used by tests
presentation/     final presentation (single offline HTML) with Arabic speaker notes
deployment/       deployment notes and a Dockerfile (not yet built or tested)
docs/             specification, decisions log, API, retrieval method, model report, assets
```

## Limitations

- **Production coverage:** only 35 verses are human-reviewed, for emotion only, so production mode often returns partial results or abstains. The review sheets in `poetry_corpus/review_packages/` are blank and pending; they contain no decisions.
- **AI-draft labels:** 1,018 verses carry AI-draft labels (model `claude-opus-5-5`). They are shown only in development mode, with a disclosure.
- **Attribution:** APCD membership does not prove authorship. Only 16 attributions are independently verified.
- **Image emotion:** it is subjective, and it is biased toward "awe" for landscapes (see above).
- **No independent test:** there is no evaluation on team-collected photos (PV-Test) and no human relevance rating of the retrieved verses.
- **Text matching:** TF-IDF has no synonymy, and some query terms are polysemous.

## Team Members

| Member | Area |
|---|---|
| Omar Al-Faifi | project lead; vision model, corpus construction, integration |
| Shaden | dataset engineering (EmoSet and Places365 manifest, leakage and duplicate checks) |
| Mohammed | Arabic NLP and retrieval (presents and explains the engine) |
| Renad | emotion classification baseline and human review of poetry annotations |

**AI assistance.**
- Much of the code and documentation was written with Claude Code (Anthropic) at the team's direction. The team made and reviewed the design decisions.
- The poetry annotations are AI drafts unless a record's `review` field shows a human decision.

## References and Licenses

- Radford et al., *Learning Transferable Visual Models From Natural Language Supervision* (CLIP), 2021. Weights `timm/vit_base_patch32_clip_224.openai`, MIT License. Library: open_clip, MIT License.
- Yang et al., *EmoSet: A Large-scale Visual Emotion Dataset with Rich Attributes*, ICCV 2023. Images are subject to the dataset's terms and are not redistributed here.
- Zhou et al., *Places: A 10 Million Image Database for Scene Recognition*, TPAMI 2017. Images are subject to the dataset's terms and are not redistributed here.
- Yousef et al., *Learning Meters of Arabic and English Poems With Recurrent Neural Networks*, 2019 (APCD). Verse texts are quoted from APCD. Redistribution terms for the corpus text have not been confirmed; see `docs/ASSETS.md`.
- Fonts: Amiri, Aref Ruqaa and IBM Plex Sans Arabic, all under the SIL Open Font License.
- **Code license:** not yet chosen by the team. Until a LICENSE file is added, all rights are reserved. No license is granted for third-party data, model weights or verse texts.
