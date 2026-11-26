"""Build every contract fixture (valid and invalid) deterministically.

    python3 -m contracts.tools.build_fixtures [--apcd-zip PATH] [--calibration PATH]

Verse texts and APCD metadata are copied verbatim from APCD rows (rows located in the original project's
data/poems_reference.json, plus two rows found by an APCD search for negated scene words). All labels,
scores and ratings in fixtures are SYNTHETIC test data: every record carries "fixture": true, poetry
records use method/review status "synthetic_fixture", and the validator rejects them in production mode.
"""
import argparse
import copy
import hashlib
import json
import math
import os
import sys
import uuid

from .. import apcd
from ..taxonomy import load_taxonomy
from ..validate import text_sha256, validate_document, validate_records, Context

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(ROOT, "fixtures")
VISUAL_MODULE = "visual_module/ml/visual"  # path of Shaden's module inside product/vendor of the original project
DEFAULT_CALIBRATION = os.environ.get(
    "PV_VISUAL_CALIBRATION",
    os.path.join(os.path.dirname(ROOT), "external", "poetry_vision_old", "product", "vendor", *VISUAL_MODULE.split("/"),
                 "weights", "calibration.json"))
DATE = "2026-11-25"
TOOL = "contracts/tools/build_fixtures.py"
VERSIONS = {"schema_version": "1.0.0", "taxonomy_version": "1.0.0"}


def fixed_uuid(name):
    return str(uuid.UUID(bytes=hashlib.md5(name.encode("utf-8")).digest(), version=4))


def fake_sha(name):
    return hashlib.sha256(f"poetry-vision-fixture:{name}".encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------------------------- poetry fixtures
# (verse_no, apcd_row, poem_id, poet_id, attribution, evidence_ids, text_note,
#  visual [(target, relation, span_text, justification)], emotion_status,
#  primary/secondary [(id, basis, span_text, justification)], concepts, genre, meaning, dims, uncertainty)
KB = {
    "hamama": ("hist:poem:abufiras_hamama", "hist:poet:abu_firas", ["ev:abufiras_dove_headnote"]),
    "araka": ("hist:poem:abufiras_araka", "hist:poet:abu_firas", ["ev:abufiras_araka_placement"]),
    "eid": ("hist:poem:mutanabbi_eid", "hist:poet:mutanabbi", ["ev:eid_headnote", "ev:eid_wafayat_kafur"]),
    "imru": ("hist:poem:imru_muallaqa", "hist:poet:imru_al_qays", ["ev:imru_juljul"]),
    "khansa": ("hist:poem:khansa_qadha", "hist:poet:al_khansa", ["ev:khansa_poem_text"]),
    "zahra": ("hist:poem:ibnzaydun_zahra", "hist:poet:ibn_zaydun", ["ev:zahra_qalaid", "ev:zahra_dhakhira"]),
    "malik": ("hist:poem:malik_self_elegy", "hist:poet:malik_ibn_al_rayb", ["ev:malik_meaning", "ev:malik_13_verses"]),
    "rundi": ("hist:poem:rundi_nuniyya", "hist:poet:abu_al_baqa_al_rundi", ["ev:rundi_identity"]),
}
NA = "not_annotated"


def dims(visual="complete", emotion="complete", concepts=NA, genre=NA, meaning=NA):
    return {"visual": visual, "emotion": emotion, "concepts": concepts, "genre": genre, "meaning": meaning}


VERSES = [
    dict(n=1, row=12996, kb="hamama",
         visual=[("tag.bird", "relation.literal", "حَمامَةٌ", None)],
         primary=[("lit_emotion.sadness", "expressed", "ناحَت", None)],
         secondary=[("lit_emotion.longing", "evoked", None, "مناجاة الحمامة تكشف حنين الأسير إلى أهله")],
         concepts=["concept.exile"], genre="genre.complaint",
         meaning="يخاطب الشاعر حمامةً تنوح قربه ويسألها هل تشعر بحاله.",
         dims=dims(concepts="partial", genre="complete", meaning="complete")),
    dict(n=2, row=12997, kb="hamama", emotion_status=NA, dims=dims(emotion=NA), uncertainty="medium"),
    dict(n=3, row=12998, kb="hamama",
         visual=[("scene_group.greenery", "relation.scene_association", None, "الغصن العالي موضع الطائر في الشجر"),
                 ("tag.bird", "relation.scene_association", None, "القوادم ريش أجنحة الطائر")],
         primary=[("lit_emotion.sadness", "expressed", "مَحزونَ", None)]),
    dict(n=4, row=1873, kb="eid", emotion_status="ambiguous", uncertainty="high"),
    dict(n=5, row=1874, kb="eid",
         visual=[("scene_group.desert", "relation.literal", "فَالبَيداءُ", None)],
         primary=[("lit_emotion.longing", "evoked", None, "البيداء تفصل الشاعر عن أحبته")],
         secondary=[("lit_emotion.sadness", "evoked", None, "يتمنى أن تبعد عنه الأعياد بعد فراق الأحبة")],
         concepts=["concept.separation"], dims=dims(concepts="partial")),
    dict(n=6, row=1875, kb="eid",
         visual=[("scene_group.desert", "relation.scene_association", None, "الناقة الوجناء تقطع الفلاة بالشاعر")],
         primary=[("lit_emotion.pride", "expressed", "العُلى", None)]),
    dict(n=7, row=26789, kb="imru",
         visual=[("scene_group.desert", "relation.scene_association", None, "الوقوف على منزل الحبيب في مواضع البادية")],
         primary=[("lit_emotion.longing", "expressed", "ذِكرى", None)],
         secondary=[("lit_emotion.sadness", "expressed", "نَبكِ", None)],
         concepts=["concept.atlal", "concept.memory"], genre="genre.love_poetry",
         meaning="يدعو الشاعر صاحبيه إلى الوقوف والبكاء عند ذكرى حبيب ومنزل بين مواضع معروفة.",
         dims=dims(concepts="complete", genre="complete", meaning="complete")),
    dict(n=8, row=26794, kb="imru",
         visual=[("scene_group.desert", "relation.scene_association", None, "الرسم الدارس أثر ديار في البادية")],
         primary=[("lit_emotion.sadness", "expressed", "عَبرَةٌ", None)]),
    dict(n=9, row=26832, kb="imru",
         visual=[("scene_group.sky_night", "relation.literal", "وَلَيلٍ", None),
                 ("scene_group.sea", "relation.symbolic", None, "الليل مشبه بموج البحر في تتابعه")],
         primary=[("lit_emotion.sadness", "expressed", "الهُمومِ", None)],
         secondary=[("lit_emotion.awe", "evoked", None, "صورة الليل الهائل المشبه بموج البحر")],
         meaning="يصف ليلًا كموج البحر أرخى ستوره على الشاعر بأنواع الهموم ليختبره.",
         dims=dims(meaning="complete")),
    dict(n=10, row=29687, kb="khansa",
         visual=[("scene_group.heritage", "relation.ambiguous", "الدارُ", "الدار قد تعني منزل الأهل لا أثرًا قديمًا")],
         primary=[("lit_emotion.sadness", "expressed", "ذَرَفَت", None)],
         genre="genre.elegy", dims=dims(genre="complete")),
    dict(n=11, row=29688, kb="khansa",
         visual=[("scene_group.water", "relation.symbolic", None, "الدمع مشبه بالفيض السائل")],
         primary=[("lit_emotion.sadness", "expressed", "يَسيلُ عَلى الخَدَّينِ", None)],
         genre="genre.elegy", dims=dims(genre="complete")),
    dict(n=12, row=83820, kb="zahra",
         text_note="في APCD كُتبت «بِازَهراءَ» بلا لام بعد الباء؛ يبدو سقطًا في المصدر، والنص محفوظ دون تصحيح.",
         visual=[("scene_group.heritage", "relation.literal", "بِازَهراءَ", None),
                 ("scene_group.sky_night", "relation.literal", "وَالأُفقُ", None)],
         primary=[("lit_emotion.longing", "expressed", "مُشتاقاً", None)],
         concepts=["concept.memory"],
         meaning="يذكر الشاعر محبوبته وهو في الزهراء مشتاقًا، والأفق صافٍ ومنظر الأرض بهيج.",
         dims=dims(concepts="partial", meaning="complete")),
    dict(n=13, row=83821, kb="zahra",
         visual=[("scene_group.greenery", "relation.scene_association", None, "نسيم الأصيل يهب في الرياض والحدائق")],
         primary=[("lit_emotion.longing", "evoked", None, "النسيم يرق لحال الشاعر المشتاق")],
         secondary=[("lit_emotion.serenity", "evoked", None, "هدوء نسيم الأصيل ورقته")]),
    dict(n=14, row=83822, kb="zahra",
         visual=[("scene_group.greenery", "relation.literal", "وَالرَوضُ", None),
                 ("scene_group.water", "relation.literal", "مائِهِ", None)],
         primary=[("lit_emotion.serenity", "evoked", None, "الروض المبتسم عن مائه يبعث الطمأنينة")],
         secondary=[("lit_emotion.joy", "evoked", None, "بهجة الروض في صورة الابتسام")],
         concepts=["concept.spring_nature"],
         meaning="يصف الروض مبتسمًا عن مائه الفضي كأن أطواقًا شُقّت عن النحور.",
         dims=dims(concepts="partial", meaning="complete")),
    dict(n=15, row=326116, kb="malik",
         visual=[("scene_group.desert", "relation.hypothetical", "بِجَنبِ الغَضا", None),
                 ("scene_group.sky_night", "relation.hypothetical", "لَيلَةً", None)],
         primary=[("lit_emotion.longing", "evoked", None, "تمني مبيت ليلة في أرض الغضا البعيدة")],
         concepts=["concept.exile"], dims=dims(concepts="partial")),
    dict(n=16, row=929989, kb="rundi",
         primary=[("lit_emotion.sadness", "evoked", None, "زوال كل تمام يبعث الأسى")],
         concepts=["concept.passing_time"], genre="genre.wisdom",
         dims=dims(concepts="complete", genre="complete")),
    dict(n=17, row=112270, kb=None,
         visual=[("scene_group.desert", "relation.scene_association", None, "ديار المحبوبة في البادية")],
         primary=[("lit_emotion.longing", "evoked", None, "تقبيل جدران ديار ليلى شوقًا إليها")],
         concepts=["concept.atlal"], dims=dims(concepts="partial")),
    dict(n=18, row=12332, kb="araka",
         text_note="في APCD «لايُذاعُ» بلا مسافة بين «لا» و«يُذاعُ»؛ النص محفوظ دون تصحيح.",
         primary=[("lit_emotion.longing", "expressed", "مُشتاقٌ", None)],
         secondary=[("lit_emotion.sadness", "expressed", "لَوعَةٌ", None)],
         dims=dims(visual=NA)),
    dict(n=19, row=130269, kb=None,
         visual=[("scene_group.desert", "relation.literal", "بِبَيداءَ", None),
                 ("scene_group.water", "relation.negated", "لا ماءٌ", None),
                 ("scene_group.greenery", "relation.negated", "وَلا عُشبُ", None)],
         emotion_status="neutral"),
    dict(n=20, row=144477, kb=None,
         visual=[("scene_group.sky_night", "relation.literal", "لَيلٌ", None),
                 ("tag.stars", "relation.negated", "لا نَجمٌ", None)],
         primary=[("lit_emotion.sadness", "expressed", "الهَمِّ", None)]),
]


DIACRITICS = {chr(c) for c in range(0x064B, 0x0653)} | {"ٰ", "ـ"}


def span(text, sub):
    """Locate `sub` in `text` ignoring diacritics/tatweel and return the span copied from the original text.

    Spans are never retyped: the returned `text` is text[start:end] of the APCD verse (code-point offsets,
    end exclusive), including the diacritics that follow the last letter.
    """
    if sub is None:
        return None
    letters, positions = [], []
    for i, ch in enumerate(text):
        if ch not in DIACRITICS:
            letters.append(ch)
            positions.append(i)
    plain_text = "".join(letters)
    plain_sub = "".join(ch for ch in sub if ch not in DIACRITICS)
    found = plain_text.find(plain_sub)
    if not plain_sub or found < 0 or plain_text.find(plain_sub, found + 1) >= 0:
        raise SystemExit(f"span {sub!r} must occur exactly once in {text!r}")
    start = positions[found]
    end = positions[found + len(plain_sub) - 1] + 1
    while end < len(text) and text[end] in DIACRITICS:
        end += 1
    return {"start": start, "end": end, "text": text[start:end]}


def verse_id(n):
    return f"pv:verse:{900000 + n:06d}"


def build_poetry(rows):
    records = []
    for v in VERSES:
        row = rows[v["row"]]
        text = row[apcd.VERSE]
        poem_id, poet_id, evidence = KB[v["kb"]] if v.get("kb") else (None, None, [])
        status = v.get("emotion_status", "has_emotion")

        def emotion(entries):
            return [{"id": i, "basis": basis, "evidence_span": span(text, s), "justification_ar": j}
                    for i, basis, s, j in entries]

        records.append({
            **VERSIONS,
            "fixture": True,
            "verse_id": verse_id(v["n"]),
            "apcd_row": v["row"],
            "text_original": text,
            "text_sha256": text_sha256(text),
            "hemistichs": {"shatr_right": row[apcd.SHATR_RIGHT], "shatr_left": row[apcd.SHATR_LEFT]},
            "text_verification": {"method": "apcd_row_exact", "tool": TOOL, "date": DATE},
            "text_note": v.get("text_note"),
            "poet": {"name_apcd": row[apcd.POET], "poet_id": poet_id},
            "era_apcd": row[apcd.ERA],
            "source": {"dataset": "APCD", "diwan_apcd": row[apcd.DIWAN], "meter_apcd": row[apcd.METER],
                       "rhyme_apcd": row[apcd.RHYME]},
            "attribution_status": "source_verified" if poem_id else "apcd_only",
            "evidence_ids": evidence,
            "poem_id": poem_id,
            "visual_associations": [{"target": t, "relation": r, "evidence_span": span(text, s), "justification_ar": j}
                                    for t, r, s, j in v.get("visual", [])],
            "emotion_status": status,
            "emotions": {"primary": emotion(v.get("primary", [])), "secondary": emotion(v.get("secondary", []))},
            "semantic_concepts": v.get("concepts", []),
            "genre": v.get("genre"),
            "meaning_ar": v.get("meaning"),
            "dimension_status": v.get("dims", dims()),
            "annotation": {"annotator_id": "synthetic_fixture", "method": "synthetic_fixture", "model_id": None,
                           "date": DATE},
            "review": {"status": "synthetic_fixture", "reviewers": [], "decisions": []},
            "annotator_uncertainty": v.get("uncertainty", "low"),
        })
    return records


# --------------------------------------------------------------------------------------------- image manifest
def build_manifest(tax):
    unmapped, ood_a, ood_b = "volcano", "airport_terminal", "bowling_alley"
    background = tax.data["places365_mapping"]["background_for_scene_other"][0]
    assert tax.map_places365(unmapped) == (None, "unmapped"), "pick another unmapped category"
    assert tax.map_places365(ood_a)[1] == "excluded_ood" and tax.map_places365(ood_b)[1] == "excluded_ood"
    emoset = {"protocol": "EmoSet: 10 annotators per image, consensus above 7/10; scene attribute from a "
                          "Places365 model checked yes/no by annotators (per the paper)",
              "annotators": [], "date": None}
    places = {"protocol": "Places365 official validation category; seeded re-split 60/20/20 (visual module)",
              "annotators": [], "date": None}
    license_ = "synthetic fixture record; no real image"

    def rec(source, sid, path, split, origin, scene, s_status, s_source, raw, emotion, e_status, e_source,
            provenance, review="dataset_original", group=None, **extra):
        return {**VERSIONS, "fixture": True, "image_id": f"img:{source}:{sid}", "source_dataset": source,
                "source_image_id": sid, "image_path": path, "image_sha256": fake_sha(sid), "width": 256,
                "height": 171, "split": split, "split_origin": origin, "near_dup_group": group,
                "scene_label": scene, "scene_label_status": s_status, "scene_label_source": s_source,
                "scene_source_raw": raw, "emotion_label": emotion, "emotion_label_status": e_status,
                "emotion_label_source": e_source, **extra, "annotation_provenance": provenance,
                "review_status": review, "license_terms": license_}

    return [
        rec("emoset118k", "fixture_awe_0001", "datasets/images/emoset/train/awe/fixture_awe_0001.jpg", "train",
            "hf_mirror_split", "scene.sea_coast", "labeled", "emoset_attribute_mapped", "coast",
            "img_emotion.awe", "labeled", "emoset_consensus", emoset, review="audit_sampled"),
        rec("emoset118k", "fixture_sadness_0002", "datasets/images/emoset/test/sadness/fixture_sadness_0002.jpg",
            "test", "hf_mirror_split", None, "unmapped", None, unmapped, "img_emotion.sadness", "labeled",
            "emoset_consensus", emoset, group="g:fixture_01"),
        rec("emoset118k", "fixture_fear_0003", "datasets/images/emoset/val/fear/fixture_fear_0003.jpg", "val",
            "hf_mirror_split", None, "excluded_ood", None, ood_a, "img_emotion.fear", "labeled",
            "emoset_consensus", emoset),
        rec("places365_sample", "fixture_desert_sand_0004", "datasets/images/places365/desert-sand/fixture_0004.jpg",
            "train", "reconstructed_from_official_val_seed42", "scene.desert", "labeled", "places365_category",
            "desert-sand", None, "unavailable", None, places),
        rec("places365_sample", "fixture_background_0005", "datasets/images/places365/background/fixture_0005.jpg",
            "train", "reconstructed_from_official_val_seed42", "scene.other", "labeled", "places365_category",
            background, None, "unavailable", None, places),
        rec("places365_sample", "fixture_ood_0006", "datasets/images/places365/ood/fixture_0006.jpg", "ood_test",
            "reconstructed_from_official_val_seed42", None, "excluded_ood", None, ood_b, None, "unavailable", None,
            places),
        rec("pv_test", "pv_0001", "datasets/images/pv_test/pv_0001.jpg", "test", "independent_test",
            "scene.desert", "labeled", "human_annotation", None, None, "labeled_set", "human_annotation",
            {"protocol": "two independent team annotators; union of acceptable sets; scene by consensus",
             "annotators": ["annotator_A", "annotator_B"], "date": DATE},
            review="human_double", scene_ambiguous=False,
            acceptable_img_emotions=["img_emotion.awe", "img_emotion.contentment"],
            acceptable_lit_emotions=["lit_emotion.awe", "lit_emotion.serenity", "lit_emotion.longing"]),
    ]


# --------------------------------------------------------------------------------------------- model card
def build_model_card(tax, calibration):
    tag_thresholds = {f"tag.{k}": v["threshold"] for k, v in calibration["tags"].items()}
    head = lambda name, layer, act, n, origin, source, **extra: {  # noqa: E731
        "name": name, "input": "embedding", "output_layer": layer, "output_ids": tax.class_order[layer], **extra,
        "activation": act, "in_dim": 512, "out_dim": n, "params": 512 * n + n, "origin": origin,
        "source_file": source, "trained_on": None, "temperature": None, "calibrated": False}
    visual = f"{VISUAL_MODULE}/weights/"  # relative to the original project's product/vendor/
    return {
        **VERSIONS, "fixture": True,
        "model_id": "poetry-vision-net", "model_version": "1.0.0-draft", "status": "draft",
        "backbone": {"library": "open_clip", "library_version": "4.2.2", "arch": "ViT-B-32-quickgelu",
                     "pretrained": "openai", "hf_repo": "timm/vit_base_patch32_clip_224.openai",
                     "hf_revision": "a6f597a30f7b82c51704746581f9a4e41421e878",
                     "weights_file": "open_clip_model.safetensors",
                     "weights_sha256": "e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31",
                     "frozen": True, "precision": "fp32", "embedding_dim": 512, "l2_normalized": True},
        "preprocessing": {"exif_transpose": True, "color": "RGB", "resize_shortest": 224, "interpolation": "bicubic",
                          "antialias": True, "center_crop": 224,
                          "mean": [0.48145466, 0.4578275, 0.40821073], "std": [0.26862954, 0.26130258, 0.27577711]},
        "adapter": None,
        "heads": [
            head("scene", "scene", "softmax", 17, "reused_visual_module_v1", visual + "scene_head_clip.npz"),
            head("emotion", "img_emotion", "softmax", 8, "trained_poetry_vision_v1", None),
            head("tags", "tag", "linear_threshold", 34, "reused_visual_module_v1", visual + "tag_heads.npz",
                 exposed_ids=tax.exposed_tags),
        ],
        "thresholds": {
            "scene_supported": {"rule": "max_in_taxonomy_prob_of_17way_softmax",
                                "value": calibration["scene_reject_threshold"],
                                "tpr_target": calibration["scene_reject_tpr"],
                                "fitted_on": "visual_module_v1: Places365 val split (in-taxonomy images)",
                                "after_temperature": False},
            "emotion_ambiguity_margin": 0.15,
            "tags": tag_thresholds,
        },
        "metrics": [],
        "limitations": ["رأس الإحساس لم يُدرَّب بعد؛ ينتظر صور EmoSet",
                        "لا temperature بعد؛ الاحتمالات غير معايَرة",
                        "عتبة الرفض مشتقة قبل أي معايرة، ويجب إعادة اشتقاقها بعد temperature"],
    }


# --------------------------------------------------------------------------------------------- inference output
def build_inference(tax, calibration):
    special = {"scene.desert": 0.58, "scene.camp_tents": 0.14, "scene.sea_coast": 0.06,
               "scene.mountains_valleys": 0.05, "scene.sky": 0.04, "scene.other": 0.03}
    rest = [s for s in tax.class_order["scene"] if s not in special]
    scene = {s: special.get(s, 0.10 / len(rest)) for s in tax.class_order["scene"]}
    in_tax = sorted((v for k, v in scene.items() if k != "scene.other"), reverse=True)
    threshold = calibration["scene_reject_threshold"]
    groups = []
    for gid in tax.ids("scene_group"):
        members, _ = tax.group_members(gid)
        groups.append({"id": gid, "score": sum(scene[m] for m in members)})
    emotion = {"img_emotion.amusement": 0.04, "img_emotion.awe": 0.55, "img_emotion.contentment": 0.20,
               "img_emotion.excitement": 0.05, "img_emotion.anger": 0.02, "img_emotion.disgust": 0.01,
               "img_emotion.fear": 0.03, "img_emotion.sadness": 0.10}
    e_sorted = sorted(emotion.values(), reverse=True)
    tags = []
    for tag in tax.exposed_tags:
        thr = calibration["tags"][tag.split(".", 1)[1]]["threshold"]
        score = 1.9 if tag == "tag.road" else round(thr - 0.5, 4)
        tags.append({"id": tag, "decision_score": score, "threshold": thr, "present": score >= thr})
    return {
        **VERSIONS, "fixture": True,
        "image_sha256": fake_sha("inference:desert_road_photo"),
        "model_id": "poetry-vision-net", "model_version": "1.0.0-draft", "status": "ok", "error": None,
        "scene": {"predictions": [{"id": k, "score": v} for k, v in scene.items()], "calibrated": False,
                  "supported_threshold": threshold, "supported": in_tax[0] >= threshold,
                  "status": "confident" if in_tax[0] >= threshold else "unsupported",
                  "top1_score": in_tax[0], "margin": in_tax[0] - in_tax[1]},
        "scene_groups": groups,
        "emotion": {"predictions": [{"id": k, "score": v} for k, v in emotion.items()], "calibrated": False,
                    "status": "clear" if e_sorted[0] - e_sorted[1] >= 0.15 else "ambiguous",
                    "margin": e_sorted[0] - e_sorted[1], "ambiguity_margin": 0.15,
                    "entropy": -sum(v * math.log(v) for v in emotion.values() if v > 0)},
        "tags": tags,
        "suggested_lit_emotions": [
            {"id": "lit_emotion.awe", "from_img_emotion": "img_emotion.awe", "basis": "mapping_v1"},
            {"id": "lit_emotion.serenity", "from_img_emotion": "img_emotion.contentment", "basis": "mapping_v1"}],
        "timings_ms": None,
    }


def build_inference_error():
    return {**VERSIONS, "fixture": True, "image_sha256": fake_sha("inference:corrupt_upload"),
            "model_id": "poetry-vision-net", "model_version": "1.0.0-draft", "status": "error",
            "error": {"code": "invalid_image", "message_ar": "تعذّر فتح الصورة؛ ارفع ملف JPEG أو PNG أو WebP."},
            "scene": None, "scene_groups": None, "emotion": None, "tags": None, "suggested_lit_emotions": None}


# --------------------------------------------------------------------------------------------- profiles
def profile(name, items, selected, secondary=None, concept=None, symbolic=False, emotion_only=False):
    return {**VERSIONS, "fixture": True, "profile_id": fixed_uuid(f"profile:{name}"), "origin": "synthetic_query",
            "source_inference": None,
            "confirmed_visual_items": [{"id": i, "user_selection": s, "suggested_by_model": True} for i, s in items],
            "selected_lit_emotion": selected, "secondary_lit_emotion": secondary, "concept_id": concept,
            "symbolic_allowed": symbolic, "emotion_only_allowed": emotion_only}


PROFILES = {
    "profile_literal_desert": dict(items=[("scene_group.desert", "primary")], selected="lit_emotion.longing"),
    "profile_association_greenery": dict(items=[("scene_group.greenery", "primary"), ("tag.bird", "secondary")],
                                         selected="lit_emotion.sadness"),
    "profile_symbolic_allowed_sea": dict(items=[("scene_group.sea", "primary"), ("scene_group.sky_night", "secondary")],
                                         selected="lit_emotion.sadness", symbolic=True),
    "profile_symbolic_denied_sea": dict(items=[("scene_group.sea", "primary"), ("scene_group.sky_night", "secondary")],
                                        selected="lit_emotion.sadness", symbolic=False),
    "profile_emotion_only": dict(items=[], selected="lit_emotion.longing", emotion_only=True),
    "profile_focus": dict(items=[("scene_group.sky_night", "focus"), ("scene_group.heritage", "primary")],
                          selected="lit_emotion.longing", secondary="lit_emotion.serenity", concept="concept.memory"),
    "profile_tag_only": dict(items=[("tag.stars", "primary")], selected="lit_emotion.sadness"),
}

WEIGHTS = {"emotion": 0.45, "visual": 0.35, "text": 0.20, "semantic": 0.0}


def build_query(tax):
    terms = tax.labels["scene_group.desert"]["query_terms_ar"][:6]
    return {**VERSIONS, "fixture": True, "query_id": fixed_uuid("query:literal_desert"),
            "profile_id": fixed_uuid("profile:profile_literal_desert"), "corpus_version": "fixtures_v1",
            "corpus_mode": "fixture", "method": "hybrid", "preprocessing_variant": "N1", "weights": WEIGHTS,
            "k": 3, "min_score": 0.0, "tiers_enabled": [1, 2, 3],
            "diversity": {"max_per_poem": 1, "max_per_poet": 1, "near_dup_cosine": 0.8}, "query_terms_ar": terms}


def final_score(components):
    present = [(WEIGHTS[k], v) for k, v in components.items() if v is not None]
    return sum(w * v for w, v in present) / sum(w for w, _ in present)


def build_recommendations(poetry):
    by_id = {r["verse_id"]: r for r in poetry}

    def item(rank, n, visual, relation, sentences, templates, spans):
        r = by_id[verse_id(n)]
        scores = {"emotion": 1.0, "visual": visual, "text": None, "semantic": None}
        return {"rank": rank, "verse_id": r["verse_id"], "apcd_row": r["apcd_row"], "text_original": r["text_original"],
                "poet_name_apcd": r["poet"]["name_apcd"], "era_apcd": r["era_apcd"],
                "attribution_status": r["attribution_status"], "tier": 1,
                "scores": {**scores, "final": final_score(scores)},
                "matched": {"lit_emotion": "lit_emotion.longing", "emotion_role": "primary",
                            "visual_targets": ["scene_group.desert"], "relations": [relation]},
                "explanation": {"template_ids": templates, "sentences_ar": sentences,
                                "evidence_spans": [span(r["text_original"], s) for s in spans]},
                "review_status": r["review"]["status"]}

    literal = "تُظهر الصورة الصحراء والبادية (أكّدتَها)، والبيت يذكر «فَالبَيداءُ» وصفًا حرفيًا."
    assoc_7 = "البيت لا يسمي الصحراء والبادية، لكن موقفه يقع فيها: الوقوف على منزل الحبيب في مواضع البادية."
    assoc_17 = "البيت لا يسمي الصحراء والبادية، لكن موقفه يقع فيها: ديار المحبوبة في البادية."
    longing = "اخترتَ الحنين والشوق، وهو الإحساس الأساسي المسجل لهذا البيت."
    verified = "النسبة موثقة بأدلة من قاعدة المعرفة التاريخية."
    apcd_only = "النسبة من APCD وحده، ولم يُتحقق منها بمصدر مستقل."
    ok = {
        **VERSIONS, "fixture": True, "query_id": fixed_uuid("query:literal_desert"),
        "profile_id": fixed_uuid("profile:profile_literal_desert"), "engine_version": "0.0.0-fixture",
        "corpus_version": "fixtures_v1", "corpus_mode": "fixture", "k": 3, "weights": WEIGHTS, "status": "ok",
        "items": [
            item(1, 5, 1.0, "relation.literal", [literal, longing, verified],
                 ["T_SCENE_LITERAL", "T_EMOTION_PRIMARY", "T_ATTRIBUTION"], ["فَالبَيداءُ"]),
            item(2, 7, 0.7, "relation.scene_association", [assoc_7, longing + " ودليله «ذِكرى».", verified],
                 ["T_SCENE_ASSOC", "T_EMOTION_PRIMARY", "T_ATTRIBUTION"], ["ذِكرى"]),
            item(3, 17, 0.7, "relation.scene_association", [assoc_17, longing, apcd_only],
                 ["T_SCENE_ASSOC", "T_EMOTION_PRIMARY", "T_ATTRIBUTION"], []),
        ],
        "abstention": None, "timings_ms": None,
    }
    abstained = {
        **VERSIONS, "fixture": True, "query_id": fixed_uuid("query:tag_only"),
        "profile_id": fixed_uuid("profile:profile_tag_only"), "engine_version": "0.0.0-fixture",
        "corpus_version": "fixtures_v1", "corpus_mode": "fixture", "k": 3, "weights": WEIGHTS,
        "status": "abstained", "items": [],
        "abstention": {"reason_code": "no_visual_match_emotion_only_off",
                       "message_ar": "لا يوجد في المدونة بيت حزين يثبت النجوم، ووضع «الإحساس فقط» غير مفعّل.",
                       "coverage_gap": {"visual_targets": ["tag.stars"], "lit_emotion": "lit_emotion.sadness"}},
        "timings_ms": None,
    }
    return ok, abstained


# --------------------------------------------------------------------------------------------- evaluation records
def build_evaluation():
    base = {**VERSIONS, "fixture": True, "test_set": {"id": "fixture_set", "manifest_sha256": None},
            "system": {"model_version": None, "corpus_version": "fixtures_v1", "engine_version": "0.0.0-fixture",
                       "method": "hybrid"},
            "rater_id": "synthetic_fixture", "blind": True,
            "notes": "synthetic fixture; not a human judgment", "timestamp": "2026-11-25T12:00:00+03:00"}
    empty = {"visual_fit": None, "emotion_fit": None, "overall": None, "explanation_correct": None,
             "text_authentic": None, "judgment": None}
    profile_id = fixed_uuid("profile:profile_literal_desert")
    return [
        {**base, "eval_id": fixed_uuid("eval:retrieval:1"), "layer": "retrieval",
         "item_id": f"{profile_id}|lit_emotion.longing|{verse_id(5)}",
         "rating": {**empty, "visual_fit": 3, "emotion_fit": 2, "overall": 2}},
        {**base, "eval_id": fixed_uuid("eval:e2e:1"), "layer": "e2e",
         "item_id": f"{fake_sha('inference:desert_road_photo')}|lit_emotion.longing|{verse_id(7)}",
         "rating": {**empty, "visual_fit": 2, "emotion_fit": 3, "overall": 2, "explanation_correct": "yes",
                    "text_authentic": "yes"}},
        {**base, "eval_id": fixed_uuid("eval:annotation:1"), "layer": "annotation", "blind": False,
         "system": {"model_version": None, "corpus_version": None, "engine_version": None, "method": None},
         "item_id": "img:emoset118k:fixture_awe_0001", "rating": {**empty, "judgment": "correct"}},
    ]


# --------------------------------------------------------------------------------------------- invalid fixtures
def without(d, key):
    return {k: v for k, v in d.items() if k != key}


def build_invalid(valid):
    m, poetry = valid["image_manifest"], valid["poetry_record"]
    card, inference = valid["model_card"], valid["inference_output"]
    profiles, query = valid["image_profile"], valid["retrieval_query"]
    recs, evals = valid["recommendations"], valid["evaluation_record"]
    c = copy.deepcopy
    out = {}

    def put(contract, name, payload):
        out[(contract, name)] = payload

    put("image_manifest", "E_REQUIRED__missing_image_sha256.jsonl", [without(m[0], "image_sha256")])
    put("image_manifest", "E_ENUM__unknown_split.jsonl", [{**m[0], "split": "training"}])
    put("image_manifest", "E_TYPE__width_as_string.jsonl", [{**m[0], "width": "256"}])
    put("image_manifest", "E_FORMAT__windows_path.jsonl", [{**m[0], "image_path": m[0]["image_path"].replace("/", "\\")}])
    put("image_manifest", "E_SPLIT_LEAK__near_duplicate_across_splits.jsonl",
        [{**m[0], "near_dup_group": "g:leak"}, {**m[1], "near_dup_group": "g:leak"}])
    put("image_manifest", "E_STATUS_CONFLICT__label_with_unavailable_status.jsonl",
        [{**m[3], "scene_label_status": "unavailable"}])

    put("taxonomy", "E_VERSION__unsupported_major.json",
        {"schema_version": "2.0.0", "taxonomy_version": "2.0.0", "title_ar": "تصنيف غير صالح", "layers": [],
         "labels": []})

    bad_card = c(card)
    bad_card["heads"][1].update(temperature=-1.0, calibrated=True)
    put("model_card", "E_RANGE__negative_temperature.json", bad_card)
    bad_card = c(card)
    bad_card["heads"][0]["params"] = 9000
    put("model_card", "E_STATUS_CONFLICT__params_mismatch.json", bad_card)

    bad = c(inference["inference_ok"])
    for entry in bad["scene"]["predictions"]:
        if entry["id"] == "scene.library_books":
            entry["score"] += 0.05
    put("inference_output", "E_RANGE__scene_scores_do_not_sum_to_one.json", bad)
    put("inference_output", "E_UNKNOWN_FIELD__extra_field.json", {**inference["inference_ok"], "debug": True})

    bad = c(profiles["profile_literal_desert"])
    bad["confirmed_visual_items"][0]["id"] = "scene_group.jungle"
    put("image_profile", "E_UNKNOWN_ID__unknown_scene_group.json", bad)
    put("image_profile", "E_STATUS_CONFLICT__no_visual_without_emotion_only.json",
        {**profiles["profile_emotion_only"], "emotion_only_allowed": False})
    bad = c(profiles["profile_association_greenery"])
    bad["confirmed_visual_items"][1]["id"] = "scene_group.greenery"
    put("image_profile", "E_DUP_ID__item_confirmed_twice.json", bad)

    first = poetry[0]
    bad = c(first)
    bad["emotions"]["primary"][0]["evidence_span"]["text"] = "حمامة"
    put("poetry_record", "E_SPAN__span_text_mismatch.jsonl", [bad])
    put("poetry_record", "E_APCD_ROW__negative_row.jsonl", [{**first, "apcd_row": -5}])
    put("poetry_record", "E_APCD_TEXT__hash_mismatch.jsonl", [{**first, "text_sha256": text_sha256("نص آخر")}])
    put("poetry_record", "E_DISPLAY_RULE__stored_display_allowed.jsonl", [{**first, "display_allowed": True}])
    put("poetry_record", "E_FIXTURE_IN_PRODUCTION__production.jsonl", [first])
    put("poetry_record", "E_DUP_ID__duplicate_verse_id.jsonl", [first, {**poetry[1], "verse_id": first["verse_id"]}])
    bad = c(poetry[4])
    bad["visual_associations"][0]["evidence_span"] = None
    put("poetry_record", "E_REQUIRED__literal_without_span.jsonl", [bad])

    put("retrieval_query", "E_RANGE__weights_do_not_sum_to_one.json",
        {**query, "weights": {**query["weights"], "text": 0.30}})
    put("retrieval_query", "E_VERSION__schema_major_2.json", {**query, "schema_version": "2.0.0"})

    bad = c(recs["recs_ok_literal_desert"])
    bad["status"] = "abstained"
    bad["abstention"] = c(recs["recs_abstained_tag_only"]["abstention"])
    put("recommendations", "E_STATUS_CONFLICT__abstained_with_items.json", bad)
    put("recommendations", "E_DISPLAY_RULE__fixture_verses_claimed_as_production.json",
        {**recs["recs_ok_literal_desert"], "corpus_mode": "production"})
    put("recommendations", "E_STATUS_CONFLICT__development_without_draft_disclosure.json",
        {**recs["recs_ok_literal_desert"], "corpus_mode": "development"})
    put("retrieval_query", "E_FIXTURE_IN_PRODUCTION__production_with_development_corpus.json",
        {**without(query, "fixture"), "corpus_mode": "development"})

    put("evaluation_record", "E_REQUIRED__missing_rater_id.jsonl", [without(evals[0], "rater_id")])
    put("evaluation_record", "E_STATUS_CONFLICT__unblinded_retrieval_judgment.jsonl", [{**evals[0], "blind": False}])
    return out


# --------------------------------------------------------------------------------------------- rendering
def as_json(payload):
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def as_jsonl(records):
    return "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records)


def render(apcd_zip=None, calibration_path=None):
    """Build every fixture in memory. Returns (files, valid, taxonomy) with files = {relative path: text}."""
    tax = load_taxonomy()
    with open(calibration_path or DEFAULT_CALIBRATION, encoding="utf-8") as fh:
        calibration = json.load(fh)
    rows = apcd.get_rows([v["row"] for v in VERSES], apcd_zip)
    missing = [v["row"] for v in VERSES if v["row"] not in rows]
    if missing:
        raise SystemExit(f"APCD rows not found: {missing}")

    poetry = build_poetry(rows)
    ok, abstained = build_recommendations(poetry)
    valid = {
        "image_manifest": build_manifest(tax),
        "poetry_record": poetry,
        "model_card": build_model_card(tax, calibration),
        "inference_output": {"inference_ok": build_inference(tax, calibration), "inference_error": build_inference_error()},
        "image_profile": {name: profile(name, **spec) for name, spec in PROFILES.items()},
        "retrieval_query": build_query(tax),
        "recommendations": {"recs_ok_literal_desert": ok, "recs_abstained_tag_only": abstained},
        "evaluation_record": build_evaluation(),
    }
    files = {
        "valid/image_manifest/manifest_fixture.jsonl": as_jsonl(valid["image_manifest"]),
        "valid/poetry_record/poetry_fixtures_v1.jsonl": as_jsonl(poetry),
        "valid/model_card/model_card_v1_draft.json": as_json(valid["model_card"]),
        "valid/retrieval_query/query_hybrid_literal_desert.json": as_json(valid["retrieval_query"]),
        "valid/evaluation_record/evaluation_fixture.jsonl": as_jsonl(valid["evaluation_record"]),
        "valid/taxonomy/README.md": "The valid taxonomy fixture is the real file: contracts/taxonomy/taxonomy_v1.json\n",
    }
    for group in ("inference_output", "image_profile", "recommendations"):
        for name, doc in valid[group].items():
            files[f"valid/{group}/{name}.json"] = as_json(doc)
    for (contract, name), payload in build_invalid(valid).items():
        files[f"invalid/{contract}/{name}"] = as_jsonl(payload) if name.endswith(".jsonl") else as_json(payload)
    return files, valid, tax


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--apcd-zip", default=apcd.DEFAULT_ZIP)
    parser.add_argument("--calibration", default=DEFAULT_CALIBRATION)
    args = parser.parse_args(argv)
    files, valid, tax = render(args.apcd_zip, args.calibration)
    for relative, text in files.items():
        path = os.path.join(FIXTURES, relative)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # self-check: every valid fixture passes in fixture mode
    poetry = valid["poetry_record"]
    ctx = Context(taxonomy=tax, mode="fixture", corpus={r["verse_id"]: r for r in poetry})
    problems = []
    for contract in ("image_manifest", "poetry_record", "evaluation_record"):
        problems += validate_records(contract, list(enumerate(valid[contract], 1)), ctx)
    problems += validate_document("model_card", valid["model_card"], ctx)
    problems += validate_document("retrieval_query", valid["retrieval_query"], ctx)
    for group in ("inference_output", "image_profile", "recommendations"):
        for doc in valid[group].values():
            problems += validate_document(group, doc, ctx)
    for problem in problems:
        print(problem, file=sys.stderr)
    print(f"fixtures written under {FIXTURES} ({len(problems)} problem(s) in valid fixtures)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
