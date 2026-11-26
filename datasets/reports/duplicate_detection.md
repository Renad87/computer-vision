# Duplicate detection (v1)

## Exact duplicates (SHA-256 of the file bytes, method 6.1)

- images hashed: 15180
- groups of identical files: 0
- quarantined: 0 — by reason: {}

## Near duplicates (pHash ≤ 6 or CLIP cosine ≥ 0.95, method 6.2)

- images searched (after exact-duplicate handling): 15180
- thresholds (provisional, fixed before the search): pHash Hamming ≤ 6 of 64 bits, or CLIP cosine ≥ 0.95 (`ViT-B-32-quickgelu`/`openai`, L2-normalized). They only nominate pairs; a person decides each pair.
- candidate pairs: 159 — by method: {'clip': 154, 'phash': 3, 'phash+clip': 2}
- across splits: 90; across sources: 1
- human decisions: same_image 0, different 159, pending 0
- every pair with its decision, reviewer and date: `near_duplicate_candidates.csv`

- confirmed groups: 0; sizes: {}
- quarantined (near_duplicate_across_splits): 0 — per source and split: {}

### Distance distributions (nearest neighbour of every image)

| CLIP cosine to nearest neighbour | images |
|---|---|
| -1–0.7 | 414 |
| 0.7–0.8 | 4031 |
| 0.8–0.85 | 4448 |
| 0.85–0.9 | 4181 |
| 0.9–0.95 | 1924 |
| 0.95–0.98 | 176 |
| 0.98–1.01 | 6 |

| pHash Hamming to nearest neighbour | images |
|---|---|
| 0–3 | 2 |
| 3–7 | 8 |
| 7–11 | 125 |
| 11–16 | 4940 |
| 16–21 | 10105 |
| 21–65 | 0 |

### Candidate pairs per source and split pair

| pair (source/split) | candidates | same_image | different | pending |
|---|---|---|---|---|
| emoset118k/test ↔ emoset118k/test | 22 | 0 | 22 | 0 |
| emoset118k/test ↔ emoset118k/train | 60 | 0 | 60 | 0 |
| emoset118k/test ↔ emoset118k/val | 10 | 0 | 10 | 0 |
| emoset118k/train ↔ emoset118k/train | 43 | 0 | 43 | 0 |
| emoset118k/train ↔ emoset118k/val | 14 | 0 | 14 | 0 |
| emoset118k/train ↔ places365_sample/train | 1 | 0 | 1 | 0 |
| places365_sample/test ↔ places365_sample/train | 5 | 0 | 5 | 0 |
| places365_sample/train ↔ places365_sample/train | 3 | 0 | 3 | 0 |
| places365_sample/train ↔ places365_sample/val | 1 | 0 | 1 | 0 |
