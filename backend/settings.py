"""Runtime settings for the final Poetry Vision app. Paths are relative to the repository; override with env vars.

    PV_CORPUS       corpus snapshot (JSONL of poetry_record)       default: poetry_corpus/exports/corpus_all_v2.jsonl
    PV_CORPUS_VERSION  label stored in queries/recommendations     default: file stem (corpus_all_v2)
    PV_DEVICE       auto | mps | cpu                              default: auto
    PV_DEFAULT_MODE production | development                      default: production
    PV_PORT         used by run.sh only                            default: 8010
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_VERSION = "1.0.0"


def _repo_path(value):
    return value if os.path.isabs(value) else os.path.join(REPO, value)


CORPUS_PATH = _repo_path(os.environ.get("PV_CORPUS", "poetry_corpus/exports/corpus_all_v2.jsonl"))
CORPUS_VERSION = os.environ.get("PV_CORPUS_VERSION") or os.path.splitext(os.path.basename(CORPUS_PATH))[0]
DEVICE = os.environ.get("PV_DEVICE", "auto")
DEFAULT_MODE = os.environ.get("PV_DEFAULT_MODE", "production")
MODEL_CARD_PATH = os.path.join(REPO, "artifacts", "model_card_v1.json")
FRONTEND_DIST = os.path.join(REPO, "frontend", "dist")
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
ANALYSIS_CACHE_SIZE = 256
MODES = ("production", "development")

# Production query of the retrieval engine (docs/RETRIEVAL_METHOD.md): Score = 0.45E + 0.35V + 0.20T.
QUERY_DEFAULTS = {
    "method": "hybrid",
    "preprocessing_variant": "N1",
    "weights": {"emotion": 0.45, "visual": 0.35, "text": 0.20, "semantic": 0.0},
    "k": 3,
    "min_score": 0.0,
    "tiers_enabled": [1, 2, 3],
    "diversity": {"max_per_poem": 1, "max_per_poet": 1, "near_dup_cosine": 0.8},
}

# Suggestion defaults for the confirmation step (UI pre-selection only; the user decides).
SUGGEST_SECOND_GROUP_MIN = 0.25
