"""Profile grid and per-item diagnostics for the retrieval quality diagnosis (stdlib only).

Profiles are built exactly like backend/service.py build_profile/build_query (origin user_session, confirmed
scene_group / exposed tag items with user_selection "primary" as the frontend sends them, production
QUERY_DEFAULTS from backend/settings.py), except that profile_id / query_id are deterministic so runs are
reproducible. No image is involved: source_inference carries a placeholder hash, as the engine never reads it.
"""
import hashlib
import json
import os
import uuid

from contracts.taxonomy import load_taxonomy

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CORPUS_PATH = os.path.join(REPO, "poetry_corpus", "exports", "corpus_all_v2.jsonl")
CORPUS_VERSION = "corpus_all_v2"
TAXONOMY = load_taxonomy()

# Copied from backend/settings.py QUERY_DEFAULTS (kept literal so this module does not import the backend app).
QUERY_DEFAULTS = {
    "method": "hybrid",
    "preprocessing_variant": "N1",
    "weights": {"emotion": 0.45, "visual": 0.35, "text": 0.20, "semantic": 0.0},
    "k": 3,
    "min_score": 0.0,
    "tiers_enabled": [1, 2, 3],
    "diversity": {"max_per_poem": 1, "max_per_poet": 1, "near_dup_cosine": 0.8},
}

SCENE_GROUPS = list(TAXONOMY.ids("scene_group"))
EXPOSED_TAGS = list(TAXONOMY.exposed_tags)
LIT_EMOTIONS = list(TAXONOMY.ids("lit_emotion"))
MODES = ("production", "development")

# Frontend defaults: symbolic off, emotion-only off (on only when no item is confirmed).
SETTINGS = {
    "default": {"symbolic_allowed": False, "emotion_only_allowed": False},
    "permissive": {"symbolic_allowed": True, "emotion_only_allowed": True},
}

# Realistic multi-item confirmations (a scene group plus a tag the vision model can report together).
COMBOS = [
    ("scene_group.sky_night", "tag.moon"), ("scene_group.sky_night", "tag.stars"),
    ("scene_group.sea", "tag.boat_ship"), ("scene_group.sea", "tag.sea"), ("scene_group.desert", "tag.horse"),
    ("scene_group.greenery", "tag.flower"), ("scene_group.greenery", "tag.bird"),
    ("scene_group.worship", "tag.mosque"), ("scene_group.mountains", "tag.fog"), ("scene_group.desert", "tag.road"),
    ("scene_group.heritage", "tag.road"), ("scene_group.water", "tag.bird"),
]


def _sid(*parts):
    """Deterministic id in uuid4 format (version and variant bits set) so the contracts accept it."""
    return str(uuid.UUID(bytes=hashlib.sha256("|".join(parts).encode()).digest()[:16], version=4))


def build_profile(item_ids, emotion, setting):
    """Mirror of backend.service.build_profile for a request with these items (all 'primary')."""
    s = SETTINGS[setting]
    items = [{"id": i, "user_selection": "primary", "suggested_by_model": True} for i in item_ids]
    return {
        "schema_version": "1.0.0", "taxonomy_version": TAXONOMY.version, "fixture": False,
        "profile_id": _sid(*item_ids, emotion, setting), "origin": "user_session",
        "source_inference": {"image_sha256": "0" * 64, "model_version": "1.0.0"},
        "confirmed_visual_items": items,
        "selected_lit_emotion": emotion,
        "secondary_lit_emotion": None,
        "concept_id": None,
        "symbolic_allowed": s["symbolic_allowed"],
        "emotion_only_allowed": s["emotion_only_allowed"] or not items,
    }


def build_query(profile, mode, expanded_query):
    q = {"schema_version": "1.0.0", "taxonomy_version": TAXONOMY.version, "fixture": False,
         "query_id": _sid(profile["profile_id"], mode), "profile_id": profile["profile_id"],
         "corpus_version": CORPUS_VERSION, "corpus_mode": mode, **json.loads(json.dumps(QUERY_DEFAULTS))}
    return expanded_query(profile, q, TAXONOMY)


def grid():
    """[(cell_id, item_ids, emotion, setting)]: no-item profiles, single items (9 groups + 13 tags), combos."""
    out = []
    for emotion in LIT_EMOTIONS:  # no confirmed item: the backend forces emotion_only_allowed
        out.append((f"none|{emotion}|default", (), emotion, "default"))
    for setting in SETTINGS:
        for emotion in LIT_EMOTIONS:
            for x in SCENE_GROUPS + EXPOSED_TAGS:
                out.append((f"{x}|{emotion}|{setting}", (x,), emotion, setting))
            for combo in COMBOS:
                out.append(("+".join(combo) + f"|{emotion}|{setting}", combo, emotion, setting))
    return out
