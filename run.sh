#!/bin/zsh
# Poetry Vision (final): one-command start.  ./run.sh        -> http://127.0.0.1:8010
#   PV_PORT=8020 ./run.sh                 other port (8000 is left to the frozen old product)
#   PV_CORPUS=poetry_corpus/exports/<snapshot>.jsonl ./run.sh   another corpus snapshot, no code change
#   PV_DEFAULT_MODE=development ./run.sh  start the UI in development mode (drafts shown with a disclosure)
set -e
cd "$(dirname "$0")"
PORT="${PV_PORT:-8010}"
PY=.venv/bin/python
fail() { echo "ERROR: $1" >&2; exit 1; }

[ -x "$PY" ] || fail "missing .venv. Create it: UV_OFFLINE=1 uv venv --python 3.12 .venv && UV_OFFLINE=1 uv pip install --offline --python .venv/bin/python -r requirements.txt"
"$PY" -c "import fastapi, uvicorn, multipart, torch, open_clip, numpy, PIL" 2>/dev/null || fail "Python dependencies missing in .venv (see requirements.txt)"
[ -f artifacts/heads/emotion_head_v1.npz ] || fail "missing trained emotion head artifacts/heads/emotion_head_v1.npz"
[ -f artifacts/heads/scene_calibration_v1.json ] || fail "missing artifacts/heads/scene_calibration_v1.json"
[ -f artifacts/model_card_v1.json ] || fail "missing artifacts/model_card_v1.json"
CORPUS="${PV_CORPUS:-poetry_corpus/exports/corpus_all_v2.jsonl}"
[ -f "$CORPUS" ] || fail "corpus snapshot not found: $CORPUS"
"$PY" -B -c "from vision_model.backbone import verify_weights; verify_weights()" || fail "CLIP weights not found or hash mismatch (download them and set PV_HF_CACHE; see README)"

if [ ! -f frontend/dist/index.html ]; then
  command -v npm >/dev/null || fail "frontend/dist missing and npm not installed"
  echo "Building the frontend..."
  (cd frontend && { [ -d node_modules ] || npm ci --no-audit --no-fund; } && npm run build) || fail "frontend build failed"
fi
if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then fail "port $PORT is already in use (choose another with PV_PORT=...)"; fi

export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 TOKENIZERS_PARALLELISM=false
echo "Starting Poetry Vision on http://127.0.0.1:$PORT  (corpus: $CORPUS)"
( for i in {1..60}; do sleep 1; if curl -sf "http://127.0.0.1:$PORT/api/ready" >/tmp/pv_ready.$$ 2>/dev/null; then
    "$PY" -c "import json;d=json.load(open('/tmp/pv_ready.$$'));print('READY' if d['ready'] else 'NOT READY', '| model', d['model'].get('model_version'), d['model'].get('device'), '| corpus', d['corpus'].get('version'), d['corpus'].get('count'), '| production-displayable', (d['corpus'].get('displayable') or {}).get('production'));[print('  model error:', d['model']['error']) for _ in [0] if d['model']['error']];[print('  corpus error:', d['corpus']['error']) for _ in [0] if d['corpus']['error']]"
    echo "Open http://127.0.0.1:$PORT"; rm -f /tmp/pv_ready.$$; break; fi; done ) &
exec "$PY" -B -m uvicorn backend.app:app --host 127.0.0.1 --port "$PORT"
