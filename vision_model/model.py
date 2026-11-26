"""PoetryVisionNet v1 (Stage 1): one frozen CLIP encoder shared by the scene, emotion and tag heads.

    image bytes -> decode (EXIF, RGB) -> CLIP ViT-B/32 -> z (512, L2) -> scene 17 / emotion 8 / tags 34

`analyze()` returns an `inference_output` document (contracts v1.0.0). The emotion head must be a
trained head loaded from artifacts/heads; the model refuses to run without one.
"""
import hashlib
import math
import time

import numpy as np

from . import config
from .backbone import ClipEncoder, ImageError, decode_image
from .heads import LinearHead, load_old_calibration, load_old_scene_head, load_old_tag_head

SCHEMA_VERSION = "1.0.0"
SUGGESTION_MIN_SCORE = 0.15  # an image emotion feeds a literary suggestion if it is top-2 and at least this likely

ERROR_MESSAGES_AR = {
    "invalid_image": "تعذّرت قراءة الصورة. استخدم ملف JPEG أو PNG سليمًا.",
    "unsupported_format": "صيغة الصورة غير مدعومة. استخدم JPEG أو PNG أو WebP.",
    "too_small": "الصورة أصغر من الحد الأدنى (32 بكسل للضلع الأقصر).",
    "internal": "حدث خطأ داخلي أثناء تحليل الصورة.",
}


class PoetryVisionNet:
    def __init__(self, taxonomy, emotion_head, encoder=None, device="auto", model_version="1.0.0-draft",
                 scene_head=None, tag_head=None, thresholds=None):
        if not isinstance(emotion_head, LinearHead) or emotion_head.output_ids != taxonomy.class_order["img_emotion"]:
            raise ValueError("a trained emotion head in taxonomy order is required")
        self.taxonomy, self.model_version = taxonomy, model_version
        self.encoder = encoder or ClipEncoder(device)
        self.scene = scene_head or load_old_scene_head(taxonomy)
        self.tags = tag_head or load_old_tag_head(taxonomy)
        self.emotion = emotion_head
        self.thresholds = thresholds or load_old_calibration()
        self.exposed = list(taxonomy.exposed_tags)
        self.tag_index = [self.tags.output_ids.index(t) for t in self.exposed]

    # ------------------------------------------------------------------ pure head part (no image I/O)
    def outputs_from_embedding(self, z):
        tax = self.taxonomy
        scene_p = self.scene.probs(z[None])[0]
        scene_ids = self.scene.output_ids
        in_tax = sorted((float(p) for i, p in zip(scene_ids, scene_p) if i != "scene.other"), reverse=True)
        top1, top2 = in_tax[0], in_tax[1]
        threshold = self.thresholds["scene_supported"]
        supported = top1 >= threshold
        status = "unsupported" if not supported else ("uncertain" if top1 - top2 < config.SCENE_UNCERTAIN_MARGIN
                                                      else "confident")
        scene_scores = dict(zip(scene_ids, (float(p) for p in scene_p)))
        scene = {"predictions": [{"id": i, "score": scene_scores[i]} for i in scene_ids],
                 "calibrated": self.scene.temperature is not None, "supported_threshold": threshold,
                 "supported": supported, "status": status, "top1_score": top1, "margin": top1 - top2}
        groups = [{"id": g, "score": float(sum(scene_scores[m] for m in tax.group_members(g)[0]))}
                  for g in tax.ids("scene_group")]

        emo_p = self.emotion.probs(z[None])[0]
        emo_ids = self.emotion.output_ids
        order = np.argsort(-emo_p)
        margin = float(emo_p[order[0]] - emo_p[order[1]])
        emotion = {"predictions": [{"id": i, "score": float(p)} for i, p in zip(emo_ids, emo_p)],
                   "calibrated": self.emotion.temperature is not None,
                   "status": "ambiguous" if margin < config.EMOTION_AMBIGUITY_MARGIN else "clear",
                   "margin": margin, "ambiguity_margin": config.EMOTION_AMBIGUITY_MARGIN,
                   "entropy": float(-sum(p * math.log(p) for p in emo_p if p > 0))}

        tag_scores = self.tags.logits(z[None])[0]
        tags = []
        for tag_id, k in zip(self.exposed, self.tag_index):
            thr = self.thresholds["tags"][tag_id]
            tags.append({"id": tag_id, "decision_score": float(tag_scores[k]), "threshold": thr,
                         "present": bool(tag_scores[k] >= thr)})

        suggestions, seen = [], set()
        pairs = sorted(tax.suggestion_pairs)
        for k in order[:2]:
            if emo_p[k] < SUGGESTION_MIN_SCORE:
                continue
            for src, lit in pairs:
                if src == emo_ids[k] and lit not in seen:
                    seen.add(lit)
                    suggestions.append({"id": lit, "from_img_emotion": src, "basis": tax.suggestion_basis})
        return {"scene": scene, "scene_groups": groups, "emotion": emotion, "tags": tags,
                "suggested_lit_emotions": suggestions}

    # ------------------------------------------------------------------ full inference
    def _document(self, image_sha256, status, error=None, parts=None, timings=None):
        doc = {"schema_version": SCHEMA_VERSION, "taxonomy_version": self.taxonomy.version, "fixture": False,
               "image_sha256": image_sha256, "model_id": config.MODEL_ID, "model_version": self.model_version,
               "status": status, "error": error}
        doc.update(parts or {k: None for k in ("scene", "scene_groups", "emotion", "tags", "suggested_lit_emotions")})
        doc["timings_ms"] = timings
        return doc

    def analyze(self, image_bytes):
        t0 = time.perf_counter()
        sha = hashlib.sha256(image_bytes).hexdigest()
        try:
            img = decode_image(image_bytes)
        except ImageError as exc:
            return self._document(sha, "error", {"code": exc.code, "message_ar": ERROR_MESSAGES_AR[exc.code]})
        batch = self.encoder.preprocess(img).unsqueeze(0)
        t1 = time.perf_counter()
        z = self.encoder.encode_tensors(batch)[0]
        t2 = time.perf_counter()
        parts = self.outputs_from_embedding(z)
        t3 = time.perf_counter()
        timings = {"preprocess": round((t1 - t0) * 1000, 3), "forward": round((t2 - t1) * 1000, 3),
                   "total": round((t3 - t0) * 1000, 3)}
        return self._document(sha, "ok", parts=parts, timings=timings)


def load_default(taxonomy, device="auto", model_version=None):
    """PoetryVisionNet with the trained emotion head and the Places-fitted scene temperature and threshold."""
    import json
    import os

    if model_version is None:
        model_version = "1.0.0-draft"
        if os.path.exists(config.MODEL_CARD_PATH):
            with open(config.MODEL_CARD_PATH, encoding="utf-8") as fh:
                model_version = json.load(fh)["model_version"]
    scene = load_old_scene_head(taxonomy)
    thresholds = load_old_calibration()
    if os.path.exists(config.SCENE_CALIB_PATH):
        with open(config.SCENE_CALIB_PATH, encoding="utf-8") as fh:
            calib = json.load(fh)
        scene.temperature = calib["temperature"]
        thresholds["scene_supported"] = calib["scene_supported"]
    return PoetryVisionNet(taxonomy, LinearHead.load(config.EMOTION_HEAD_PATH), device=device, model_version=model_version,
                           scene_head=scene, thresholds=thresholds)
