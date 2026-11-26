# Emotion head diagnosis (2026-11-26)

Every number below is in `results.json`, produced by `vision_model/diagnose_emotion.py`. Selection used EmoSet validation only. Test was not re-scored, because no candidate was adopted.

## Root cause

There is no bug.
- Class order, labels, preprocessing and runtime embeddings all match the trained setup.
  - 20 EmoSet images re-encoded at runtime: minimum cosine 0.99999988 against the cache, same top class 20/20.
  - The e2e photos reproduce the reported outputs exactly.
- The awe bias comes from the training data. EmoSet labels scenic landscapes as **awe**:
  - in the training sample, 65.6% of images whose EmoSet scene is a landscape type are awe (n=398), against 7.8% for other scenes;
  - in the full 118K set, 57.8% against 8.1%.
- A head-free nearest-neighbour vote in CLIP space shows the same bias: awe majority for 41% of Places photos.
- The softmax has no "neutral" class, and the app mostly sees landscapes, so awe dominates on real photos:
  - 44.6% of all Places365 photos;
  - 73.8% when the predicted scene is natural;
  - 24 of the 26 e2e photos.
- On EmoSet itself there is no over-prediction: awe precision and recall are both 0.807 on val, with 150 predicted for 150 true.

## About 99–100%

These are real model outputs. Three factors add up:
1. **The model is confident on landscapes,** which are in-distribution for EmoSet awe.
2. **The temperature sharpens.** T = 0.776 < 1, fitted correctly on val: ECE 0.068 → 0.022, NLL 0.626 → 0.602.
   - On EmoSet val, predictions with p ≥ 0.985 are 99.5% correct.
   - It raises the share of Places photos shown as 99% or more from 0.9% to 6.1%.
   - The calibration holds for EmoSet, not for the app's domain.
3. **The UI rounds up.** `Math.round` showed p ≥ 0.995 as "100%"; the maximum observed is 0.998.

## Candidates (EmoSet val; Places awe rate is a behaviour diagnostic, not accuracy)

| candidate | val macro-F1 | Δ vs v1 [95% CI] | val NLL | val ECE | Places awe |
|---|---|---|---|---|---|
| v1 (C=3, T=0.776) | 0.789 [0.766, 0.811] | – | 0.602 | 0.022 | 44.6% |
| v1 with T ≥ 1 | 0.789 | 0 | 0.626 | 0.068 | 44.6% |
| C=1 | 0.781 | −0.008 [−0.020, 0.006] | 0.629 | 0.026 | 45.5% |
| C=0.3 | 0.758 | −0.030 [−0.047, −0.015] | 0.692 | 0.018 | 46.8% |
| C=0.1 | 0.737 | −0.052 | 0.762 | 0.025 | 48.5% |
| class_weight balanced | identical (train is exactly 600 per class) | | | | |

- No candidate is better.
- Stronger regularization increases the awe rate.
- Removing the temperature changes no prediction and only worsens calibration.
- **v1 is kept.** No v2 artifact was saved.

## Abstention rules (each threshold set to flag 5% of EmoSet val)

| flag if | threshold | val accuracy kept / flagged | Places awe flagged |
|---|---|---|---|
| max-prob below | 0.4058 | 0.810 / 0.367 | 6.3% |
| entropy above | 1.4335 nats | 0.808 / 0.400 | 9.3% |
| top-2 margin below | 0.0574 | 0.811 / 0.350 | 3.6% |
| max cosine to a class centroid below | 0.6223 | 0.792 / 0.700 | 7.7% |

- The confidence rules catch in-domain errors (AUROC about 0.82).
- None of them catches the landscape-awe convention, because those photos are in-distribution for EmoSet awe.
- Accuracy by confidence: top-3 val accuracy 96.9% (top-1 78.8%); max-prob ≥ 0.70 gives 90.7% accuracy at 67% coverage.

## Adopted (integration, 2026-11-26)

- **The model is unchanged:** the head, the temperature and every score.
- **The literary emotion is no longer auto-selected.** The user chooses it.
- **The top-3 image emotions are shown.**
- **Uncertain emotion:** marked when max-prob < 0.406, or entropy > 1.4335, or the status is ambiguous. No literary emotion is suggested then.
- **Percentages are floored,** never rounded up: 0.998 shows as 99%.
- **A landscape note** shows when the predicted scene is natural and awe is the top emotion.
- **A real fix needs new labelled data:** real in-domain photos with emotion labels, or a neutral class, then a refit.
