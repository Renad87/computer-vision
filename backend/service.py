"""Application state for the final app: one vision model, one corpus snapshot, one retrieval engine.

Loaded once at startup. Inference results are cached by analysis_id so a change of literary emotion, visual focus
or mode only reruns retrieval (about 1 ms), never the CLIP model.
"""
import hashlib
import json
import os
import threading
import time
import uuid
from collections import OrderedDict

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, validate_document, validate_records

from . import settings

TAXONOMY = load_taxonomy()
SCHEMA_VERSION = "1.0.0"

DISCLOSURE_AR = ("وضع التطوير: الأبيات المعروضة مأخوذة حرفيًا من APCD، لكن تسمياتها (الإحساس والعلاقة البصرية) "
                 "مسودات آلية لم يراجعها إنسان بعد، فلا تُعدّ نتائج معتمدة.")


class AppError(Exception):
    def __init__(self, status, code, message_ar, issues=None):
        super().__init__(code)
        self.status, self.code, self.message_ar, self.issues = status, code, message_ar, issues


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _rel(path):
    """Repository-relative path for display (never expose absolute paths of the host)."""
    try:
        return os.path.relpath(path, settings.REPO)
    except ValueError:
        return os.path.basename(path)


class State:
    def __init__(self):
        self.model = None
        self.model_error = None
        self.model_info = {}
        self.engine = None
        self.corpus = {}
        self.corpus_error = None
        self.corpus_info = {}
        self.analyses = OrderedDict()
        self.lock = threading.Lock()  # one forward pass at a time on the shared encoder

    # ------------------------------------------------------------------ loading
    def load_corpus(self, path=None):
        from retrieval.engine import ENGINE_VERSION, RetrievalEngine, load_corpus

        path = path or settings.CORPUS_PATH
        self.engine, self.corpus, self.corpus_error = None, {}, None
        try:
            if not os.path.isfile(path):
                raise FileNotFoundError(f"corpus file not found: {_rel(path)}")
            from contracts.validate import load_jsonl
            records, issues = load_jsonl(path)
            ctx = Context(taxonomy=TAXONOMY, mode="production")
            issues += validate_records("poetry_record", records, ctx)
            if issues:
                raise ValueError(f"corpus fails poetry_record validation ({len(issues)} issues), first: "
                                 f"{issues[0].code} {issues[0].path}")
            corpus = load_corpus(path)
            self.engine = RetrievalEngine(corpus, TAXONOMY)
            self.corpus = {r["verse_id"]: r for r in corpus}
            for mode in settings.MODES:  # build the TF-IDF indexes once, now
                self.engine.index(mode, settings.QUERY_DEFAULTS["preprocessing_variant"])
            self.corpus_info = {
                "version": settings.CORPUS_VERSION, "path": _rel(path), "sha256": sha256_file(path),
                "count": len(corpus), "engine_version": ENGINE_VERSION,
                "displayable": {m: sum(1 for r in corpus if display_allowed(r, m)) for m in settings.MODES},
            }
        except Exception as exc:  # noqa: BLE001 - reported through /api/ready
            self.corpus_error = f"{type(exc).__name__}: {exc}"

    def load_model(self):
        self.model, self.model_error = None, None
        try:
            from vision_model import config as vcfg
            from vision_model.backbone import verify_weights
            from vision_model.model import load_default
            from vision_model.scene_eval import CALIB_PATH
            from vision_model.train_emotion import HEAD_PATH

            for path, what in ((HEAD_PATH, "trained emotion head"), (CALIB_PATH, "scene calibration")):
                if not os.path.isfile(path):
                    raise FileNotFoundError(f"missing {what}: {_rel(path)}")
            with open(settings.MODEL_CARD_PATH, encoding="utf-8") as fh:
                card = json.load(fh)
            t0 = time.perf_counter()
            verify_weights()
            model = load_default(TAXONOMY, device=settings.DEVICE, model_version=card["model_version"])
            card_heads = {h["name"]: h for h in card["heads"]}
            if card_heads["emotion"]["output_ids"] != model.emotion.output_ids:
                raise RuntimeError("emotion head class order differs from the model card")
            if card_heads["scene"]["output_ids"] != model.scene.output_ids:
                raise RuntimeError("scene head class order differs from the model card")
            import io
            from PIL import Image
            buf = io.BytesIO(); Image.new("RGB", (224, 224), (128, 128, 128)).save(buf, "PNG")
            model.analyze(buf.getvalue())  # warm-up forward pass (first MPS call compiles kernels)
            self.model = model
            self.model_info = {
                "model_id": vcfg.MODEL_ID, "model_version": card["model_version"], "card_status": card.get("status"),
                "device": model.encoder.device, "backbone": f"{vcfg.CLIP_ARCH}/{vcfg.CLIP_PRETRAINED} (frozen, shared)",
                "load_seconds": round(time.perf_counter() - t0, 2),
                "heads": {n: {"origin": h["origin"], "out_dim": h["out_dim"], "temperature": h["temperature"]}
                          for n, h in card_heads.items()},
                "fingerprints": {
                    "clip_weights_sha256": vcfg.WEIGHTS_SHA256,
                    "emotion_head_sha256": sha256_file(HEAD_PATH),
                    "scene_head_sha256": vcfg.OLD_SCENE_HEAD_SHA256,
                    "tag_head_sha256": vcfg.OLD_TAG_HEAD_SHA256,
                    "scene_calibration_sha256": sha256_file(CALIB_PATH),
                    "model_card_sha256": sha256_file(settings.MODEL_CARD_PATH),
                },
            }
        except Exception as exc:  # noqa: BLE001
            self.model_error = f"{type(exc).__name__}: {exc}"

    def readiness(self):
        return {
            "ready": self.model is not None and self.engine is not None,
            "model": {"loaded": self.model is not None, "error": self.model_error, **self.model_info},
            "corpus": {"loaded": self.engine is not None, "error": self.corpus_error, **self.corpus_info},
            "engine_version": self.corpus_info.get("engine_version"),
            "modes": list(settings.MODES),
            "default_mode": settings.DEFAULT_MODE,
        }

    # ------------------------------------------------------------------ analyze
    def analyze(self, image_bytes):
        if self.model is None:
            raise AppError(503, "model_not_ready", "النموذج البصري غير محمّل؛ تحقق من ملفات النموذج.")
        t0 = time.perf_counter()
        with self.lock:
            doc = self.model.analyze(image_bytes)
        t1 = time.perf_counter()
        if doc["status"] == "error":
            raise AppError(400, doc["error"]["code"], doc["error"]["message_ar"])
        issues = validate_document("inference_output", doc, Context(taxonomy=TAXONOMY, mode="production"))
        if issues:
            raise AppError(500, "internal", "مخرجات النموذج لا تطابق العقد.", [str(i) for i in issues])
        analysis_id = str(uuid.uuid4())
        self.analyses[analysis_id] = doc
        while len(self.analyses) > settings.ANALYSIS_CACHE_SIZE:
            self.analyses.popitem(last=False)
        return {"analysis_id": analysis_id, "inference": doc, "suggestion": suggestion(doc),
                "timings_ms": {"inference": round((t1 - t0) * 1000, 2),
                               "model": doc["timings_ms"], "total": round((time.perf_counter() - t0) * 1000, 2)}}

    # ------------------------------------------------------------------ recommend
    def recommend(self, req):
        t0 = time.perf_counter()
        if self.engine is None:
            raise AppError(503, "corpus_not_ready", "مدونة الشعر غير محمّلة.")
        doc = self.analyses.get(req.get("analysis_id"))
        if doc is None:
            raise AppError(404, "analysis_not_found", "انتهت صلاحية تحليل الصورة؛ ارفع الصورة مرة أخرى.")
        mode = req.get("mode") or settings.DEFAULT_MODE
        if mode not in settings.MODES:
            raise AppError(422, "invalid_mode", "وضع غير معروف.")
        ctx = Context(taxonomy=TAXONOMY, mode=mode, corpus=self.corpus)
        profile = build_profile(doc, req)
        issues = validate_document("image_profile", profile, ctx)
        if issues:
            raise AppError(422, "invalid_profile", "اختيارات غير صالحة.", [f"{i.code} {i.path}: {i.message}" for i in issues])
        query = build_query(profile, mode, settings.CORPUS_VERSION)
        issues = validate_document("retrieval_query", query, ctx)
        if issues:
            raise AppError(500, "internal", "استعلام غير صالح.", [str(i) for i in issues])
        t1 = time.perf_counter()
        rec = self.engine.recommend(profile, query, with_timings=True)
        t2 = time.perf_counter()
        issues = validate_document("recommendations", rec, ctx)
        if issues:
            raise AppError(500, "internal", "مخرجات الاسترجاع لا تطابق العقد.", [str(i) for i in issues])
        display = []
        for item in rec["items"]:
            r = self.corpus[item["verse_id"]]
            display.append({"verse_id": r["verse_id"], "hemistichs": r.get("hemistichs"), "meaning_ar": r.get("meaning_ar"),
                            "source": r.get("source"), "poet_name_apcd": r["poet"]["name_apcd"], "era_apcd": r.get("era_apcd"),
                            "review_status": r["review"]["status"], "annotation_method": r["annotation"]["method"],
                            "text_note": r.get("text_note"),
                            "reviewed_dimensions": reviewed_dimensions(r),
                            "review_scope_note_ar": review_scope_note(r, item)})
        return {"mode": mode, "disclosure_ar": DISCLOSURE_AR if mode == "development" else None,
                "profile": profile, "query": query, "recommendations": rec, "display": display,
                "inference_reused": True,
                "timings_ms": {"retrieval": round((t2 - t1) * 1000, 3),
                               "total": round((time.perf_counter() - t0) * 1000, 3)}}


def reviewed_dimensions(record):
    """Dimensions a human accepted for this record (from review.decisions), e.g. ["emotion"]."""
    return sorted({d.get("dimension") for d in record["review"].get("decisions") or []
                   if d.get("decision") in ("accept", "correct", "adjudicate") and d.get("dimension")})


def review_scope_note(record, item):
    """Honest scope of the human review for a displayed verse. The display rule is per record; a record whose
    emotion was reviewed may still carry an AI-drafted visual association. Disclose that instead of hiding it."""
    if record["review"]["status"] not in ("reviewed", "double_reviewed", "adjudicated"):
        return None
    dims = reviewed_dimensions(record)
    if item["matched"]["visual_targets"] and "visual" not in dims:
        return "راجع إنسانٌ الإحساسَ في هذا البيت، أما علاقته البصرية بالمشهد فمسودة آلية لم تُراجَع بعد."
    return None


def _name(label_id):
    entry = TAXONOMY.labels.get(label_id) or {}
    return entry.get("name_ar", label_id)


def suggestion(doc):
    """Deterministic pre-selection for the confirmation step. Shown as a suggestion; the user confirms or changes it."""
    items = []
    if doc["scene"]["supported"]:
        groups = sorted(doc["scene_groups"], key=lambda g: -g["score"])
        items.append({"id": groups[0]["id"], "name_ar": _name(groups[0]["id"]), "score": groups[0]["score"],
                      "source": "scene_group"})
        if len(groups) > 1 and groups[1]["score"] >= settings.SUGGEST_SECOND_GROUP_MIN:
            items.append({"id": groups[1]["id"], "name_ar": _name(groups[1]["id"]), "score": groups[1]["score"],
                          "source": "scene_group"})
    for tag in doc["tags"]:
        if tag["present"]:
            items.append({"id": tag["id"], "name_ar": _name(tag["id"]), "score": None, "source": "tag"})
    rel = emotion_reliability(doc)
    # An unreliable image emotion does not feed a literary suggestion; the user always chooses (nothing is preselected).
    lit = [] if rel["uncertain"] else [
        {"id": s["id"], "name_ar": _name(s["id"]), "from_img_emotion": s["from_img_emotion"]}
        for s in doc["suggested_lit_emotions"]]
    return {"visual_items": items, "lit_emotions": lit, "emotion_reliability": rel}


# Thresholds chosen on EmoSet validation only (each flags 5% of val); see evaluation/vision/emotion_diagnosis/REPORT.md.
EMOTION_MIN_MAXPROB = 0.4058
EMOTION_MAX_ENTROPY = 1.4335
LANDSCAPE_SCENES = {"scene.desert", "scene.sea_coast", "scene.mountains_valleys", "scene.rivers_lakes", "scene.forest",
                    "scene.garden", "scene.farmland_rural", "scene.sky", "scene.snow_ice"}


def emotion_reliability(doc):
    """Display-side reliability of the image emotion. Reads the model output; never changes a score."""
    emo = doc["emotion"]
    top = max(emo["predictions"], key=lambda p: p["score"])
    reasons = []
    if top["score"] < EMOTION_MIN_MAXPROB:
        reasons.append("low_max_prob")
    if emo["entropy"] > EMOTION_MAX_ENTROPY:
        reasons.append("high_entropy")
    if emo["status"] == "ambiguous":
        reasons.append("ambiguous_margin")
    scene_top = max(doc["scene"]["predictions"], key=lambda p: p["score"])["id"]
    return {"uncertain": bool(reasons), "reasons": reasons,
            "landscape_awe": top["id"] == "img_emotion.awe" and scene_top in LANDSCAPE_SCENES,
            "thresholds": {"min_max_prob": EMOTION_MIN_MAXPROB, "max_entropy": EMOTION_MAX_ENTROPY}}


def build_profile(doc, req):
    suggested = {i["id"] for i in suggestion(doc)["visual_items"]}
    items = []
    for it in req.get("confirmed_visual_items") or []:
        if not isinstance(it, dict):
            continue
        items.append({"id": it.get("id"), "user_selection": it.get("user_selection", "primary"),
                      "suggested_by_model": it.get("id") in suggested})
    return {
        "schema_version": SCHEMA_VERSION, "taxonomy_version": TAXONOMY.version, "fixture": False,
        "profile_id": str(uuid.uuid4()), "origin": "user_session",
        "source_inference": {"image_sha256": doc["image_sha256"], "model_version": doc["model_version"]},
        "confirmed_visual_items": items,
        "selected_lit_emotion": req.get("selected_lit_emotion"),
        "secondary_lit_emotion": req.get("secondary_lit_emotion") or None,
        "concept_id": None,
        "symbolic_allowed": bool(req.get("symbolic_allowed", False)),
        "emotion_only_allowed": bool(req.get("emotion_only_allowed", False)) or not items,
    }


def build_query(profile, mode, corpus_version):
    from retrieval.engine import expanded_query

    q = {"schema_version": SCHEMA_VERSION, "taxonomy_version": TAXONOMY.version, "fixture": False,
         "query_id": str(uuid.uuid4()), "profile_id": profile["profile_id"], "corpus_version": corpus_version,
         "corpus_mode": mode, **json.loads(json.dumps(settings.QUERY_DEFAULTS))}
    return expanded_query(profile, q, TAXONOMY)


def taxonomy_payload():
    def labels(layer, ids=None):
        ids = ids if ids is not None else TAXONOMY.ids(layer)
        return [{"id": i, "name_ar": _name(i), "name_en": (TAXONOMY.labels.get(i) or {}).get("name_en")} for i in ids]

    return {
        "taxonomy_version": TAXONOMY.version,
        "scene_groups": labels("scene_group"),
        "scenes": labels("scene", TAXONOMY.class_order["scene"]),
        "img_emotions": labels("img_emotion", TAXONOMY.class_order["img_emotion"]),
        "lit_emotions": labels("lit_emotion"),
        "exposed_tags": labels("tag", TAXONOMY.exposed_tags),
        "pilot": TAXONOMY.pilot,
        "suggestion_map": [{"from": a, "to": b} for a, b in sorted(TAXONOMY.suggestion_pairs)],
        "user_only_lit_emotions": sorted(TAXONOMY.user_only),
    }


STATE = State()
