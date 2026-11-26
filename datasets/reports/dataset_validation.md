# Dataset validation

Every manifest validated with the shared validator in production mode (the default).

| manifest | exit code | issues | records | SHA-256 (manifest) | SHA-256 (.build.json) |
|---|---|---|---|---|---|
| `manifest_v0.9_emotion.jsonl` | 0 | 0 | 9200 | `7df0416fbeb6e9810cc2b3fff4b6cad09600552661bd8beb7a7b5bd4428c0892` | `41df61468ce91fe6e832d707b82c19f63189254398f2cf7e0f3e8609acffc2f3` |
| `manifest_v1.jsonl` | 0 | 0 | 15180 | `efdf33b153a900ecf3524569907b316b349e4860bab249d10b6efd630310b501` | `57ee99ef58e038ebb7dd3477a7f2ab7140b1c19084ce4d35f020e5844fd29149` |

### manifest_v0.9_emotion.jsonl

```
python -m contracts.validate image_manifest datasets/manifests/manifest_v0.9_emotion.jsonl
```

- exit code: 0; issues: 0 (must be 0); records: 9200
- per source and split: emoset118k/test: 3200, emoset118k/train: 4800, emoset118k/val: 1200
- build command: `python -m data_preparation.build v0.9 --emoset-zip external/renad/emoset.zip`

### manifest_v1.jsonl

```
python -m contracts.validate image_manifest datasets/manifests/manifest_v1.jsonl
```

- exit code: 0; issues: 0 (must be 0); records: 15180
- per source and split: emoset118k/test: 3200, emoset118k/train: 4800, emoset118k/val: 1200, places365_sample/ood_test: 600, places365_sample/test: 1076, places365_sample/train: 3228, places365_sample/val: 1076
- build command: `python -m data_preparation.build v1 --places-dir external/shaden_visual --emoset-zip external/renad/emoset.zip --near-dup-decisions datasets/review/near_duplicate_decisions.csv`
