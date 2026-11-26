# Deployment

## Local (verified 2026-11-26)

```bash
./run.sh
```

- Checks `.venv`, Python packages, the trained heads, the model card, the corpus snapshot and the CLIP weights hash, builds `frontend/dist` if missing, refuses a busy port, starts FastAPI and prints `READY | model … | corpus …` and the URL.
- Default URL `http://127.0.0.1:8010`. Port 8000 is left to the frozen old product. Options: `PV_PORT`, `PV_CORPUS`, `PV_DEVICE`, `PV_DEFAULT_MODE` (see `backend/settings.py`).
- Verified on Apple M5 / macOS: model loads on MPS, corpus `corpus_all_v2` (1,053 records, 35 production-displayable).

## Environment

```bash
UV_OFFLINE=1 uv venv --python 3.12 .venv && UV_OFFLINE=1 uv pip install --offline --python .venv/bin/python -r requirements.txt
```

```bash
cd frontend && npm ci --offline && npm run build
```

## Model and data assets (not in the repository)

| Asset | Where it is read from | How to obtain |
|---|---|---|
| CLIP ViT-B/32 OpenAI weights (`open_clip_model.safetensors`, sha256 `e6d1bd77…7c31`) | `$PV_HF_CACHE` (default `~/.cache/huggingface/hub`) | Hugging Face `timm/vit_base_patch32_clip_224.openai`, revision `a6f597a3…` (MIT licence, OpenAI CLIP) |
| Reused scene and tag heads + calibration (sha256 in `vision_model/config.py`) | `artifacts/heads/reused/` (in the repository) | team-trained in the earlier visual module |
| Trained emotion head, scene calibration, model card | `artifacts/heads/`, `artifacts/model_card_v1.json` | in the repository (small) |
| Corpus snapshot | `poetry_corpus/exports/corpus_all_v2.jsonl` | in the repository; verse text is APCD (public dataset) |
| EmoSet / Places365 images, APCD CSV | `external/`, `datasets/images/` | original sources only, under their licences; never redistributed |

## Container (prepared, not built)

`deployment/Dockerfile` builds a CPU image; mount a Hugging Face cache that holds the CLIP weights:

```bash
docker build -f deployment/Dockerfile -t poetry-vision:1.0.0 .
docker run -p 8010:8010 -v ~/.cache/huggingface/hub:/hf:ro -e PV_HF_CACHE=/hf poetry-vision:1.0.0
```

Not executed: building pulls a base image (a download that needs the owner's approval). No public deployment exists.

## GitHub (prepared, NOT executed — needs the owner's explicit approval)

Review `.gitignore` first (it excludes `.venv`, `external/`, `artifacts/features/`, images, node_modules, dist, zips and the reviewer workbook). Then:

```bash
cd Poetry-Vision-Release
git init -b main
git add -A
git status --short | head -50
git commit -m "Poetry Vision final: unified CLIP model, retrieval engine, FastAPI + React app"
gh repo create poetry-vision-final --private --source . --push
```

Use `--public` only after the release/copyright decision for the corpus is made (owner decision 5, still open).
