"""Build the synthetic development inputs for the retrieval engine (no engine logic here).

    python3 -m contracts.tools.build_dev_fixtures

Writes under <repo>/fixtures/:
  dev_profiles/      24 synthetic image_profile documents (fixture: true, origin synthetic_query) + INDEX.md, index.json
  dev_queries/       one retrieval_query per profile over the development corpus (corpus_mode development)
  synthetic_inference/ 3 synthetic inference_output documents (model_version 0.0.0-synthetic, not model predictions)
  dev_examples/      2 hand-written recommendations examples in development mode (illustrative only)

Expected outcomes in index.json were derived by hand from the AI-draft labels of
poetry_corpus/records/p0_ai_drafts_v1.jsonl under the rules in docs/RETRIEVAL_METHOD.md. They describe
eligibility per tier and abstention, not scores or final order, which belong to the engine.
"""
import hashlib
import json
import math
import os
import sys
import uuid

from ..taxonomy import load_taxonomy
from ..validate import load_jsonl

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(REPO, "fixtures")
_CORPUS_PATHS = (os.path.join(REPO, "poetry_corpus", "records", "p0_ai_drafts_v1.jsonl"),   # Omar's workspace
                 os.path.join(REPO, "data", "dev_corpus", "p0_ai_drafts_v1.jsonl"))        # handoff packages
CORPUS = next((p for p in _CORPUS_PATHS if os.path.isfile(p)), _CORPUS_PATHS[0])
MODEL_CARD = os.path.join(REPO, "contracts", "fixtures", "valid", "model_card", "model_card_v1_draft.json")
VERSIONS = {"schema_version": "1.0.0", "taxonomy_version": "1.0.0"}
WEIGHTS = {"emotion": 0.45, "visual": 0.35, "text": 0.20, "semantic": 0.0}
G, T, E = "scene_group.", "tag.", "lit_emotion."


def fixed_uuid(name):
    return str(uuid.UUID(bytes=hashlib.md5(name.encode("utf-8")).digest(), version=4))


def v(*numbers):
    return [f"pv:verse:{n:06d}" for n in numbers]


# id, purpose (English), pair, confirmed items, selected, secondary, concept, symbolic, emotion_only, expectation
PROFILES = [
    ("DP01_desert_longing", "desert scene, longing; association match", "DP02",
     [(G + "desert", "primary")], E + "longing", None, None, False, False,
     dict(tier1=v(10), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP02_desert_pride", "same visual as DP01, different emotion; literal match", "DP01",
     [(G + "desert", "primary")], E + "pride", None, None, False, False,
     dict(tier1=v(31), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP03_sea_loneliness", "sea scene, loneliness; literal match", "DP04",
     [(G + "sea", "primary")], E + "loneliness", None, None, False, False,
     dict(tier1=v(15), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP04_sea_joy", "same visual as DP03, different emotion; no suitable poetry", "DP03",
     [(G + "sea", "primary")], E + "joy", None, None, False, False,
     dict(tier1=[], tier2=[], tier3=[], status="abstained", abstain="no_visual_match_emotion_only_off")),
    ("DP05_greenery_serenity", "greenery, serenity; three literal matches, two by one poet", "DP06",
     [(G + "greenery", "primary")], E + "serenity", None, None, False, False,
     dict(tier1=v(21, 22, 24), tier2=[], tier3=[], status="ok", abstain=None)),
    ("DP06_greenery_joy", "same visual as DP05, different emotion; primary vs secondary emotion ranking", "DP05",
     [(G + "greenery", "primary")], E + "joy", None, None, False, False,
     dict(tier1=v(21, 22, 24, 26, 27, 29), tier2=[], tier3=[], status="ok", abstain=None)),
    ("DP07_heritage_awe", "heritage, awe; literal and association matches", "DP08",
     [(G + "heritage", "primary")], E + "awe", None, None, False, False,
     dict(tier1=v(17, 19), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP08_heritage_longing", "same visual as DP07, different emotion; no suitable poetry", "DP07",
     [(G + "heritage", "primary")], E + "longing", None, None, False, False,
     dict(tier1=[], tier2=[], tier3=[], status="abstained", abstain="no_visual_match_emotion_only_off")),
    ("DP09_focus_sky_serenity", "focus on sky/night (greenery also confirmed); focus restricts tier 1", "DP10",
     [(G + "sky_night", "focus"), (G + "greenery", "primary")], E + "serenity", None, None, False, False,
     dict(tier1=v(21, 23, 25), tier2=[], tier3=[], status="ok", abstain=None)),
    ("DP10_focus_greenery_serenity", "same items as DP09 with the focus on greenery", "DP09",
     [(G + "greenery", "focus"), (G + "sky_night", "primary")], E + "serenity", None, None, False, False,
     dict(tier1=v(21, 22, 24), tier2=[], tier3=[], status="ok", abstain=None)),
    ("DP11_sky_fear_symbolic", "sky/night, fear, symbolic allowed; tier-2 symbolic match", "DP12",
     [(G + "sky_night", "primary")], E + "fear", None, None, True, False,
     dict(tier1=[], tier2=v(36), tier3=[], status="partial", abstain=None)),
    ("DP12_sky_fear_no_symbolic", "same as DP11 with symbolic not allowed; no suitable poetry", "DP11",
     [(G + "sky_night", "primary")], E + "fear", None, None, False, False,
     dict(tier1=[], tier2=[], tier3=[], status="abstained", abstain="no_visual_match_emotion_only_off")),
    ("DP13_moon_pride_symbolic", "moon tag, pride, symbolic allowed; the literal moon verse has another emotion", None,
     [(T + "moon", "primary")], E + "pride", None, None, True, False,
     dict(tier1=[], tier2=v(32), tier3=[], status="partial", abstain=None)),
    ("DP14_emotion_only_longing", "no visual items, emotion-only longing; at most one tier-3 item", None,
     [], E + "longing", None, None, False, True,
     dict(tier1=[], tier2=[], tier3=v(1, 6, 7, 8, 9, 10, 30), status="partial", abstain=None)),
    ("DP15_unsupported_scene_sadness", "unsupported scene (see synthetic_inference/SI01): no confirmed items, emotion-only", None,
     [], E + "sadness", None, None, False, True,
     dict(tier1=[], tier2=[], tier3=v(1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 23, 40), status="partial", abstain=None)),
    ("DP16_missing_falcon_pride", "falcon tag never annotated in the corpus; missing labels", None,
     [(T + "falcon", "primary")], E + "pride", None, None, False, False,
     dict(tier1=[], tier2=[], tier3=[], status="abstained", abstain="cell_not_covered")),
    ("DP17_missing_worship_awe", "worship scene group never annotated in the corpus; missing labels", None,
     [(G + "worship", "primary")], E + "awe", None, None, False, False,
     dict(tier1=[], tier2=[], tier3=[], status="abstained", abstain="cell_not_covered")),
    ("DP18_stars_fear", "stars tag, fear; literal tag match", None,
     [(T + "stars", "primary")], E + "fear", None, None, False, False,
     dict(tier1=v(40), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP19_bird_loneliness", "bird tag, loneliness; association match", "DP20",
     [(T + "bird", "primary")], E + "loneliness", None, None, False, False,
     dict(tier1=v(12), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP20_bird_serenity", "same visual as DP19, different emotion; literal match", "DP19",
     [(T + "bird", "primary")], E + "serenity", None, None, False, False,
     dict(tier1=v(22), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP21_water_serenity", "water, serenity; two literal matches", None,
     [(G + "water", "primary")], E + "serenity", None, None, False, False,
     dict(tier1=v(21, 24), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP22_mountains_awe", "mountains, awe; literal match", None,
     [(G + "mountains", "primary")], E + "awe", None, None, False, False,
     dict(tier1=v(16), tier2=[], tier3=[], status="partial", abstain=None)),
    ("DP23_desert_longing_emotion_only", "DP01 with emotion-only enabled: tier 1 plus at most one tier-3 item", "DP01",
     [(G + "desert", "primary")], E + "longing", None, None, False, True,
     dict(tier1=v(10), tier2=[], tier3=v(1, 6, 7, 8, 9, 30), status="partial", abstain=None)),
    ("DP24_greenery_serenity_secondary_concept", "DP05 plus a secondary emotion and a concept; eligibility unchanged", "DP05",
     [(G + "greenery", "primary")], E + "serenity", E + "joy", "concept.spring_nature", False, False,
     dict(tier1=v(21, 22, 24), tier2=[], tier3=[], status="ok", abstain=None)),
]


def profile_doc(pid, items, selected, secondary, concept, symbolic, emotion_only):
    return {**VERSIONS, "fixture": True, "profile_id": fixed_uuid(f"dev-profile:{pid}"), "origin": "synthetic_query",
            "source_inference": None,
            "confirmed_visual_items": [{"id": i, "user_selection": s, "suggested_by_model": False} for i, s in items],
            "selected_lit_emotion": selected, "secondary_lit_emotion": secondary, "concept_id": concept,
            "symbolic_allowed": symbolic, "emotion_only_allowed": emotion_only}


def query_doc(pid):
    return {**VERSIONS, "fixture": True, "query_id": fixed_uuid(f"dev-query:{pid}"),
            "profile_id": fixed_uuid(f"dev-profile:{pid}"), "corpus_version": "p0_ai_drafts_v1",
            "corpus_mode": "development", "method": "hybrid", "preprocessing_variant": "N1", "weights": WEIGHTS,
            "k": 3, "min_score": 0.0, "tiers_enabled": [1, 2, 3],
            "diversity": {"max_per_poem": 1, "max_per_poet": 1, "near_dup_cosine": 0.8}}


# --------------------------------------------------------------------------------------------- synthetic inference
def inference_doc(name, tax, card, top, emotions, tag_hits):
    """A self-consistent synthetic inference_output. `top` maps scene ids to probabilities; the rest of the mass
    is spread evenly. Not a model prediction (model_version 0.0.0-synthetic)."""
    order = tax.class_order["scene"]
    rest = [s for s in order if s not in top]
    remaining = 1.0 - sum(top.values())
    scene = {s: top.get(s, remaining / len(rest)) for s in order}
    in_tax = sorted((p for s, p in scene.items() if s != "scene.other"), reverse=True)
    threshold = card["thresholds"]["scene_supported"]["value"]
    supported = in_tax[0] >= threshold
    status = "unsupported" if not supported else ("confident" if in_tax[0] - in_tax[1] >= 0.15 else "uncertain")
    groups = [{"id": g, "score": sum(scene[m] for m in tax.group_members(g)[0])} for g in tax.ids("scene_group")]
    e_sorted = sorted(emotions.values(), reverse=True)
    tags = []
    for tag in tax.exposed_tags:
        thr = card["thresholds"]["tags"][tag]
        score = round(thr + 0.4, 4) if tag in tag_hits else round(thr - 0.6, 4)
        tags.append({"id": tag, "decision_score": score, "threshold": thr, "present": score >= thr})
    suggestions = []
    for emotion_id, _ in sorted(emotions.items(), key=lambda kv: -kv[1])[:2]:
        for source, target in sorted(tax.suggestion_pairs):
            if source == emotion_id:
                suggestions.append({"id": target, "from_img_emotion": source, "basis": tax.suggestion_basis})
    return {**VERSIONS, "fixture": True, "image_sha256": hashlib.sha256(f"synthetic-image:{name}".encode()).hexdigest(),
            "model_id": "synthetic-fixture", "model_version": "0.0.0-synthetic", "status": "ok", "error": None,
            "scene": {"predictions": [{"id": k, "score": p} for k, p in scene.items()], "calibrated": False,
                      "supported_threshold": threshold, "supported": supported, "status": status,
                      "top1_score": in_tax[0], "margin": in_tax[0] - in_tax[1]},
            "scene_groups": groups,
            "emotion": {"predictions": [{"id": k, "score": p} for k, p in emotions.items()], "calibrated": False,
                        "status": "clear" if e_sorted[0] - e_sorted[1] >= 0.15 else "ambiguous",
                        "margin": e_sorted[0] - e_sorted[1], "ambiguity_margin": 0.15,
                        "entropy": -sum(p * math.log(p) for p in emotions.values() if p > 0)},
            "tags": tags, "suggested_lit_emotions": suggestions, "timings_ms": None}


def emotion_dist(**values):
    names = ["amusement", "awe", "contentment", "excitement", "anger", "disgust", "fear", "sadness"]
    return {f"img_emotion.{n}": values.get(n, 0.0) for n in names}


# --------------------------------------------------------------------------------------------- examples
def example_ok(corpus):
    record = next(r for r in corpus if r["verse_id"] == "pv:verse:000010")
    scores = {"emotion": 1.0, "visual": 0.7, "text": None, "semantic": None}
    present = [(WEIGHTS[k], s) for k, s in scores.items() if s is not None]
    final = sum(w * s for w, s in present) / sum(w for w, _ in present)
    span = record["emotions"]["primary"][0]["evidence_span"]
    return {**VERSIONS, "fixture": True, "query_id": fixed_uuid("dev-query:DP01_desert_longing"),
            "profile_id": fixed_uuid("dev-profile:DP01_desert_longing"), "engine_version": "0.0.0-example",
            "corpus_version": "p0_ai_drafts_v1", "corpus_mode": "development", "k": 3, "weights": WEIGHTS,
            "status": "partial",
            "items": [{
                "rank": 1, "verse_id": record["verse_id"], "apcd_row": record["apcd_row"],
                "text_original": record["text_original"], "poet_name_apcd": record["poet"]["name_apcd"],
                "era_apcd": record["era_apcd"], "attribution_status": record["attribution_status"], "tier": 1,
                "scores": {**scores, "final": final},
                "matched": {"lit_emotion": E + "longing", "emotion_role": "primary",
                            "visual_targets": [G + "desert"], "relations": ["relation.scene_association"]},
                "explanation": {
                    "template_ids": ["T_SCENE_ASSOC", "T_EMOTION_PRIMARY", "T_ATTRIBUTION", "T_DRAFT_DISCLOSURE"],
                    "sentences_ar": [
                        "البيت لا يسمّي الصحراء والبادية، لكن موقفه يقع فيها: مخاطبة المنازل المقفرة على سنة الوقوف بالأطلال.",
                        "اخترتَ الحنين والشوق، وهو الإحساس الأساسي المقترح لهذا البيت، ودليله «" + span["text"] + "».",
                        "النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.",
                        "تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير)."],
                    "evidence_spans": [span]},
                "review_status": record["review"]["status"]}],
            "abstention": None, "timings_ms": None}


def example_abstained():
    return {**VERSIONS, "fixture": True, "query_id": fixed_uuid("dev-query:DP04_sea_joy"),
            "profile_id": fixed_uuid("dev-profile:DP04_sea_joy"), "engine_version": "0.0.0-example",
            "corpus_version": "p0_ai_drafts_v1", "corpus_mode": "development", "k": 3, "weights": WEIGHTS,
            "status": "abstained", "items": [],
            "abstention": {"reason_code": "no_visual_match_emotion_only_off",
                           "message_ar": "لا يوجد في المدونة الحالية بيت بهيج يرتبط بالبحر، ووضع «الإحساس فقط» غير مفعّل.",
                           "coverage_gap": {"visual_targets": [G + "sea"], "lit_emotion": E + "joy"}},
            "timings_ms": None}


# --------------------------------------------------------------------------------------------- index
INDEX_HEAD = """# Development profiles (synthetic)

All files here are SYNTHETIC test fixtures ("fixture": true, origin "synthetic_query", suggested_by_model false).
They are not model predictions and must never be presented as real user data. Queries use corpus_mode
"development" over poetry_corpus/records/p0_ai_drafts_v1.jsonl (AI drafts pending human review).

Expected eligibility was derived by hand from the draft labels under docs/RETRIEVAL_METHOD.md:
tier 1 = literal or scene_association with an anchor item (the focus if set, else every confirmed item);
tier 2 = symbolic with an anchor item when symbolic_allowed; tier 3 = emotion-only candidates when
emotion_only_allowed (the engine returns at most one). Order and scores are the engine's job.

| Profile | Tests | Pair | Tier 1 | Tier 2 | Tier-3 candidates | Expected |
|---|---|---|---|---|---|---|
"""


def short(ids):
    return ", ".join(i.rsplit(":", 1)[1].lstrip("0") for i in ids) or "-"


def render():
    tax = load_taxonomy()
    corpus = [r for _, r in load_jsonl(CORPUS)[0]]
    with open(MODEL_CARD, encoding="utf-8") as fh:
        card = json.load(fh)
    files, index, rows = {}, [], []
    for pid, purpose, pair, items, selected, secondary, concept, symbolic, emotion_only, expect in PROFILES:
        files[f"dev_profiles/{pid}.json"] = profile_doc(pid, items, selected, secondary, concept, symbolic, emotion_only)
        files[f"dev_queries/{pid}.query.json"] = query_doc(pid)
        pair_id = next((p[0] for p in PROFILES if pair and p[0].startswith(pair + "_")), None)
        index.append({"profile": f"dev_profiles/{pid}.json", "query": f"dev_queries/{pid}.query.json",
                      "purpose": purpose, "pair": pair_id, "expected": expect})
        outcome = expect["status"] + (f" ({expect['abstain']})" if expect["abstain"] else "")
        rows.append(f"| {pid} | {purpose} | {pair or '-'} | {short(expect['tier1'])} | {short(expect['tier2'])} | "
                    f"{short(expect['tier3'])} | {outcome} |")
    files["dev_profiles/index.json"] = {"description": "Synthetic development profiles and hand-derived expectations",
                                        "corpus": "poetry_corpus/records/p0_ai_drafts_v1.jsonl", "profiles": index}
    files["dev_profiles/INDEX.md"] = INDEX_HEAD + "\n".join(rows) + "\n"
    files["synthetic_inference/SI01_unsupported_scene.json"] = inference_doc(
        "unsupported_scene", tax, card, {"scene.other": 0.46, "scene.modern_city": 0.12, "scene.home_interior": 0.10},
        emotion_dist(awe=0.12, contentment=0.33, sadness=0.22, amusement=0.10, excitement=0.08, fear=0.07,
                     anger=0.05, disgust=0.03), set())
    files["synthetic_inference/SI02_indoor_library.json"] = inference_doc(
        "indoor_library", tax, card, {"scene.library_books": 0.64, "scene.home_interior": 0.18},
        emotion_dist(contentment=0.52, awe=0.14, sadness=0.10, amusement=0.09, excitement=0.06, fear=0.04,
                     anger=0.03, disgust=0.02), set())
    files["synthetic_inference/SI03_sea_coast_boat.json"] = inference_doc(
        "sea_coast_boat", tax, card, {"scene.sea_coast": 0.71, "scene.rivers_lakes": 0.09, "scene.sky": 0.06},
        emotion_dist(awe=0.41, contentment=0.30, sadness=0.09, excitement=0.08, amusement=0.05, fear=0.04,
                     anger=0.02, disgust=0.01), {"tag.sea", "tag.boat_ship"})
    files["dev_examples/recs_DP01_example_partial.json"] = example_ok(corpus)
    files["dev_examples/recs_DP04_example_abstained.json"] = example_abstained()
    return {path: (doc if isinstance(doc, str) else json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
            for path, doc in files.items()}


def main():
    for relative, text in render().items():
        path = os.path.join(OUT, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(f"wrote development fixtures under {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
