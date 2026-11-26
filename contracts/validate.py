"""Validators for the nine Poetry-Vision data contracts (Python standard library only).

CLI:
    python3 -m contracts.validate <contract> <file> [--mode production|fixture]
                                  [--taxonomy PATH] [--apcd-zip PATH] [--corpus PATH]

Prints one line per issue (CODE<TAB>path<TAB>message). Exit code 0 = valid, 1 = invalid, 2 = usage or IO error.
JSONL paths are prefixed with the 1-based line number (e.g. "L3:emotions.primary[0].evidence_span").
"""
import argparse
import hashlib
import json
import math
import sys

from . import apcd
from .schema import ERROR_CODES, F, Issue, check_fields, is_semver, join
from .taxonomy import DEFAULT_PATH as DEFAULT_TAXONOMY, Taxonomy, load_taxonomy, validate_taxonomy

CONTRACTS = ("taxonomy", "image_manifest", "model_card", "inference_output", "image_profile",
             "poetry_record", "retrieval_query", "recommendations", "evaluation_record")
JSONL_CONTRACTS = ("image_manifest", "poetry_record", "evaluation_record")
MODES = ("production", "development", "fixture")
SUPPORTED_SCHEMA_MAJOR = 1
SUM_TOLERANCE = 1e-3   # probability vectors must sum to 1 within this tolerance
EPS = 1e-6             # derived values (margins, group sums, final scores) must match within this tolerance

__all__ = ["CONTRACTS", "ERROR_CODES", "Context", "display_allowed", "text_sha256", "load_jsonl",
           "validate_document", "validate_records", "validate_file", "main"]


class Context:
    def __init__(self, taxonomy=None, mode="production", apcd_zip=None, corpus=None):
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}")
        self.taxonomy = taxonomy
        self.mode = mode
        self.apcd_zip = apcd_zip
        self.corpus = corpus  # {verse_id: poetry_record} for cross-checking recommendations


def text_sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


DISPLAY_REVIEW_STATUSES = {"reviewed", "double_reviewed", "adjudicated"}
DISPLAY_METHODS = {"human", "ai_draft_human_reviewed"}


DEVELOPMENT_METHODS = {"human", "ai_draft", "ai_draft_human_reviewed"}


def display_allowed(record, mode="production"):
    """Derived display rule for a poetry record (never stored in the record itself).

    Every mode requires: attribution not disputed, text verified against its APCD row, hash intact.
    production:  human or human-reviewed AI draft with review status reviewed/double_reviewed/adjudicated.
    development: additionally unreviewed records (AI drafts pending review). Explicit opt-in for engine
                 development only; results must disclose that the labels are unreviewed drafts.
    fixture:     additionally synthetic fixtures (method and review status 'synthetic_fixture').
    """
    try:
        if record.get("attribution_status") == "disputed":
            return False
        if (record.get("text_verification") or {}).get("method") != "apcd_row_exact":
            return False
        if text_sha256(record["text_original"]) != record.get("text_sha256"):
            return False
        method = record["annotation"]["method"]
        status = record["review"]["status"]
    except (KeyError, TypeError, AttributeError):
        return False
    if method == "synthetic_fixture":
        return mode == "fixture" and status == "synthetic_fixture" and record.get("fixture") is True
    if method in DISPLAY_METHODS and status in DISPLAY_REVIEW_STATUSES:
        return True
    return mode == "development" and method in DEVELOPMENT_METHODS and status != "disputed"


# ============================================================================================ shared specs
def _header():
    return {"schema_version": F("str", fmt="semver"), "taxonomy_version": F("str", fmt="semver"),
            "fixture": F("bool", required=False)}


SPAN = F("obj", fields={"start": F("int", min=0), "end": F("int", min=1), "text": F("str")})
NULLABLE_SPAN = F("obj", nullable=True, fields=SPAN.fields)
DIMENSION = F("str", enum={"complete", "partial", "not_annotated"})
ATTRIBUTION = {"apcd_only", "source_verified", "disputed"}
VISUAL_TARGET_LAYERS = ("scene_group", "tag_exposed")
WEIGHTS = F("obj", fields={"emotion": F("num", min=0, max=1), "visual": F("num", min=0, max=1),
                           "text": F("num", min=0, max=1), "semantic": F("num", min=0, max=1)})
RETRIEVAL_METHODS = {"labels_exact", "labels_weighted", "tfidf", "tfidf_lecture", "w2v", "hybrid",
                     "hybrid_no_tier", "bge_m3_baseline"}
ABSTENTION_CODES = {"no_emotion_match", "no_visual_match_emotion_only_off", "cell_not_covered",
                    "diversity_exhausted", "empty_corpus"}


def _issue(issues, code, path, message):
    issues.append(Issue(code, path, message))


def _close(a, b, tol=EPS):
    return isinstance(a, (int, float)) and isinstance(b, (int, float)) and abs(a - b) <= tol


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _check_span(span, text, path, issues):
    if not isinstance(span, dict) or not isinstance(text, str):
        return
    start, end, sub = span.get("start"), span.get("end"), span.get("text")
    if not all(isinstance(v, int) and not isinstance(v, bool) for v in (start, end)) or not isinstance(sub, str):
        return  # type errors are reported by the schema check
    if not 0 <= start < end <= len(text):
        _issue(issues, "E_SPAN", path, f"offsets [{start}:{end}] outside text of length {len(text)}")
    elif text[start:end] != sub:
        _issue(issues, "E_SPAN", path, f"text[{start}:{end}] is {text[start:end]!r}, span says {sub!r}")


def _check_versions(doc, ctx, issues, prefix=""):
    schema_version, taxonomy_version = doc.get("schema_version"), doc.get("taxonomy_version")
    if is_semver(schema_version) and int(schema_version.split(".")[0]) != SUPPORTED_SCHEMA_MAJOR:
        _issue(issues, "E_VERSION", prefix + "schema_version",
               f"{schema_version} is not supported (expected {SUPPORTED_SCHEMA_MAJOR}.x.x)")
    if ctx.taxonomy is not None and is_semver(taxonomy_version) and is_semver(ctx.taxonomy.version):
        if taxonomy_version.split(".")[0] != ctx.taxonomy.version.split(".")[0]:
            _issue(issues, "E_VERSION", prefix + "taxonomy_version",
                   f"{taxonomy_version} is incompatible with loaded taxonomy {ctx.taxonomy.version}")


def _check_fixture_flag(doc, ctx, issues, prefix=""):
    if ctx.mode == "production" and doc.get("fixture") is True:
        _issue(issues, "E_FIXTURE_IN_PRODUCTION", prefix + "fixture", "fixture data is not allowed in production mode")


# ============================================================================================ image_manifest
IMAGE_MANIFEST = {
    **_header(),
    "image_id": F("str", fmt="image_id"),
    "source_dataset": F("str", enum={"emoset118k", "places365_sample", "pv_test", "pv_dev"}),
    "source_image_id": F("str"),
    "image_path": F("str", fmt="relpath"),
    "image_sha256": F("str", fmt="sha256"),
    "width": F("int", min=64),
    "height": F("int", min=64),
    "split": F("str", enum={"train", "val", "test", "ood_test"}),
    "split_origin": F("str", enum={"official", "hf_mirror_split", "reconstructed_from_official_val_seed42",
                                   "independent_test", "development"}),
    "near_dup_group": F("str", nullable=True),
    "scene_label": F("id", nullable=True, layers=("scene",)),
    "scene_label_status": F("str", enum={"labeled", "unavailable", "unmapped", "excluded_ood"}),
    "scene_label_source": F("str", nullable=True,
                            enum={"places365_category", "emoset_attribute_mapped", "human_annotation"}),
    "scene_source_raw": F("str", required=False, nullable=True),
    "scene_ambiguous": F("bool", required=False),
    "emotion_label": F("id", nullable=True, layers=("img_emotion",)),
    "emotion_label_status": F("str", enum={"labeled", "labeled_set", "unavailable"}),
    "emotion_label_source": F("str", nullable=True, enum={"emoset_consensus", "human_annotation"}),
    "acceptable_img_emotions": F("list", required=False, items=F("id", layers=("img_emotion",)), min_items=1),
    "acceptable_lit_emotions": F("list", required=False, items=F("id", layers=("lit_emotion",)), min_items=1),
    "annotation_provenance": F("obj", fields={"protocol": F("str"), "annotators": F("list", items=F("str")),
                                              "date": F("str", nullable=True, fmt="date")}),
    "review_status": F("str", enum={"dataset_original", "audit_sampled", "human_double", "adjudicated"}),
    "license_terms": F("str"),
}


def _image_manifest_record(r, p, ctx, issues):
    def conflict(field, message):
        _issue(issues, "E_STATUS_CONFLICT", p + field, message)

    source, source_id, image_id = r.get("source_dataset"), r.get("source_image_id"), r.get("image_id")
    if all(isinstance(v, str) for v in (source, source_id, image_id)):
        expected = f"img:{source}:{source_id}"
        if image_id != expected:
            _issue(issues, "E_FORMAT", p + "image_id", f"must be {expected!r}")

    s_label, s_status, s_source = r.get("scene_label"), r.get("scene_label_status"), r.get("scene_label_source")
    if (s_status == "labeled") != (s_label is not None):
        conflict("scene_label", "scene_label must be set exactly when scene_label_status is 'labeled'")
    if (s_status == "labeled") != (s_source is not None):
        conflict("scene_label_source", "scene_label_source must be set exactly when scene_label_status is 'labeled'")
    raw = r.get("scene_source_raw")
    if ctx.taxonomy is not None and isinstance(raw, str) and raw.strip() and s_source != "human_annotation":
        expected_label, expected_status = ctx.taxonomy.map_places365(raw)
        if (s_label, s_status) != (expected_label, expected_status):
            conflict("scene_label", f"raw scene {raw!r} maps to ({expected_label}, {expected_status}) "
                                    f"under taxonomy {ctx.taxonomy.version}")
    if r.get("split") == "ood_test" and s_status != "excluded_ood":
        conflict("scene_label_status", "ood_test images must have scene_label_status 'excluded_ood'")

    e_label, e_status, e_source = r.get("emotion_label"), r.get("emotion_label_status"), r.get("emotion_label_source")
    acceptable = r.get("acceptable_img_emotions")
    if e_status == "labeled" and (e_label is None or e_source is None or acceptable):
        conflict("emotion_label", "'labeled' needs emotion_label and emotion_label_source and no acceptable set")
    if e_status == "labeled_set" and (e_label is not None or not acceptable or e_source != "human_annotation"):
        conflict("emotion_label", "'labeled_set' needs acceptable_img_emotions, human_annotation and no single label")
    if e_status == "unavailable" and (e_label is not None or e_source is not None or acceptable):
        conflict("emotion_label", "'unavailable' must not carry an emotion label, source or acceptable set")

    if source == "pv_test":
        if r.get("split") != "test" or r.get("split_origin") != "independent_test":
            conflict("split", "pv_test images must be split 'test' with split_origin 'independent_test'")
    else:
        for field in ("acceptable_img_emotions", "acceptable_lit_emotions", "scene_ambiguous"):
            if field in r:
                conflict(field, "only pv_test records may carry this field")
    if r.get("split") == "train" and s_status != "labeled" and e_status != "labeled":
        conflict("split", "training records need at least one labeled task")


def _image_manifest_collection(records, ctx, issues):
    first_id, first_sha, groups = {}, {}, {}
    for line, r in records:
        image_id, sha, split, group = r.get("image_id"), r.get("image_sha256"), r.get("split"), r.get("near_dup_group")
        if isinstance(image_id, str):
            if image_id in first_id:
                _issue(issues, "E_DUP_ID", f"L{line}:image_id", f"duplicate image_id (first at line {first_id[image_id]})")
            else:
                first_id[image_id] = line
        if isinstance(sha, str):
            if sha in first_sha:
                other_line, other_split = first_sha[sha]
                code = "E_SPLIT_LEAK" if other_split != split else "E_DUP_ID"
                _issue(issues, code, f"L{line}:image_sha256",
                       f"same content as line {other_line} (splits {other_split!r} and {split!r})")
            else:
                first_sha[sha] = (line, split)
        if isinstance(group, str):
            groups.setdefault(group, []).append((line, split))
    for group, members in groups.items():
        splits = sorted({str(s) for _, s in members})
        if len(splits) > 1:
            _issue(issues, "E_SPLIT_LEAK", f"L{members[0][0]}:near_dup_group",
                   f"near-duplicate group {group!r} spans splits {splits}")


# ============================================================================================ model_card
HEAD = F("obj", fields={
    "name": F("str", enum={"scene", "emotion", "tags"}),
    "input": F("str", enum={"embedding", "adapter"}),
    "output_layer": F("str", enum={"scene", "img_emotion", "tag"}),
    "output_ids": F("list", items=F("id", layers=("scene", "img_emotion", "tag")), min_items=1),
    "exposed_ids": F("list", required=False, items=F("id", layers=("tag",))),
    "activation": F("str", enum={"softmax", "linear_threshold"}),
    "in_dim": F("int", min=1),
    "out_dim": F("int", min=1),
    "params": F("int", min=0),
    "origin": F("str", enum={"reused_visual_module_v1", "trained_poetry_vision_v1"}),
    "source_file": F("str", nullable=True),
    "trained_on": F("obj", nullable=True, fields={"manifest_sha256": F("str", fmt="sha256"),
                                                  "split": F("str", enum={"train"})}),
    "temperature": F("num", nullable=True, min=0, exclusive_min=True),
    "calibrated": F("bool"),
})
MODEL_CARD = {
    **_header(),
    "model_id": F("str"),
    "model_version": F("str", fmt="version"),
    "status": F("str", enum={"draft", "released"}),
    "backbone": F("obj", fields={
        "library": F("str", enum={"open_clip"}), "library_version": F("str"), "arch": F("str"),
        "pretrained": F("str"), "hf_repo": F("str"), "hf_revision": F("str"), "weights_file": F("str"),
        "weights_sha256": F("str", fmt="sha256"), "frozen": F("bool"), "precision": F("str", enum={"fp32"}),
        "embedding_dim": F("int", min=1), "l2_normalized": F("bool")}),
    "preprocessing": F("obj", fields={
        "exif_transpose": F("bool"), "color": F("str", enum={"RGB"}), "resize_shortest": F("int", min=1),
        "interpolation": F("str", enum={"bicubic"}), "antialias": F("bool"), "center_crop": F("int", min=1),
        "mean": F("list", items=F("num", min=0, max=1), min_items=3, max_items=3),
        "std": F("list", items=F("num", min=0, max=1, exclusive_min=True), min_items=3, max_items=3)}),
    "adapter": F("obj", required=False, nullable=True, fields={
        "in_dim": F("int", min=1), "out_dim": F("int", min=1), "activation": F("str", enum={"gelu"}),
        "dropout": F("num", min=0, max=1), "params": F("int", min=0)}),
    "heads": F("list", items=HEAD, min_items=1),
    "thresholds": F("obj", fields={
        "scene_supported": F("obj", fields={
            "rule": F("str", enum={"max_in_taxonomy_prob_of_17way_softmax"}),
            "value": F("num", nullable=True, min=0, max=1), "tpr_target": F("num", min=0, max=1),
            "fitted_on": F("str"), "after_temperature": F("bool")}),
        "emotion_ambiguity_margin": F("num", min=0, max=1),
        "tags": F("map", keys=F("id", layers=("tag",)), values=F("num"))}),
    "metrics": F("list", items=F("obj", fields={
        "name": F("str"), "value": F("num"), "dataset": F("str"), "split": F("str"), "n": F("int", min=1),
        "run_id": F("str")})),
    "limitations": F("list", items=F("str")),
}
HEAD_LAYER = {"scene": "scene", "emotion": "img_emotion", "tags": "tag"}
HEAD_ACTIVATION = {"scene": "softmax", "emotion": "softmax", "tags": "linear_threshold"}


def _model_card_record(doc, p, ctx, issues):
    heads = [h for h in doc.get("heads") or [] if isinstance(h, dict)]
    backbone = doc.get("backbone") if isinstance(doc.get("backbone"), dict) else {}
    adapter = doc.get("adapter") if isinstance(doc.get("adapter"), dict) else None
    thresholds = doc.get("thresholds") if isinstance(doc.get("thresholds"), dict) else {}
    scene_supported = thresholds.get("scene_supported") if isinstance(thresholds.get("scene_supported"), dict) else {}
    released = doc.get("status") == "released"
    names = {}
    for i, head in enumerate(doc.get("heads") or []):
        if not isinstance(head, dict):
            continue
        path = p + join("heads", i)
        name = head.get("name")
        if name in names:
            _issue(issues, "E_DUP_ID", join(path, "name"), f"head {name!r} defined twice")
        names[name] = head
        if name in HEAD_LAYER and head.get("output_layer") != HEAD_LAYER[name]:
            _issue(issues, "E_STATUS_CONFLICT", join(path, "output_layer"), f"head {name!r} outputs {HEAD_LAYER[name]!r}")
        if name in HEAD_ACTIVATION and head.get("activation") != HEAD_ACTIVATION[name]:
            _issue(issues, "E_STATUS_CONFLICT", join(path, "activation"), f"head {name!r} uses {HEAD_ACTIVATION[name]!r}")
        ids = head.get("output_ids") if isinstance(head.get("output_ids"), list) else []
        layer = head.get("output_layer")
        if ctx.taxonomy is not None and layer in ctx.taxonomy.class_order and ids != ctx.taxonomy.class_order[layer]:
            _issue(issues, "E_STATUS_CONFLICT", join(path, "output_ids"),
                   f"must equal the taxonomy {layer} class order ({len(ctx.taxonomy.class_order[layer])} ids)")
        in_dim, out_dim, params = head.get("in_dim"), head.get("out_dim"), head.get("params")
        if isinstance(out_dim, int) and out_dim != len(ids):
            _issue(issues, "E_STATUS_CONFLICT", join(path, "out_dim"), f"out_dim {out_dim} != {len(ids)} output ids")
        if all(isinstance(v, int) for v in (in_dim, out_dim, params)) and params != in_dim * out_dim + out_dim:
            _issue(issues, "E_STATUS_CONFLICT", join(path, "params"),
                   f"a linear head {in_dim}->{out_dim} has {in_dim * out_dim + out_dim} parameters")
        if head.get("input") == "embedding" and isinstance(in_dim, int) and in_dim != backbone.get("embedding_dim"):
            _issue(issues, "E_STATUS_CONFLICT", join(path, "in_dim"), "must equal backbone.embedding_dim")
        if head.get("input") == "adapter":
            if adapter is None:
                _issue(issues, "E_STATUS_CONFLICT", join(path, "input"), "head reads the adapter but no adapter is defined")
            elif in_dim != adapter.get("out_dim"):
                _issue(issues, "E_STATUS_CONFLICT", join(path, "in_dim"), "must equal adapter.out_dim")
        if (head.get("temperature") is not None) != (head.get("calibrated") is True):
            _issue(issues, "E_STATUS_CONFLICT", join(path, "calibrated"), "calibrated must be true exactly when a temperature is set")
        if name == "tags":
            exposed = head.get("exposed_ids")
            if exposed is None:
                _issue(issues, "E_REQUIRED", join(path, "exposed_ids"), "the tag head must list its exposed tags")
            elif ctx.taxonomy is not None and list(exposed) != ctx.taxonomy.exposed_tags:
                _issue(issues, "E_STATUS_CONFLICT", join(path, "exposed_ids"), "must equal the taxonomy exposed tags")
            tag_thresholds = thresholds.get("tags") if isinstance(thresholds.get("tags"), dict) else {}
            for tag in exposed or []:
                if tag not in tag_thresholds:
                    _issue(issues, "E_REQUIRED", p + f"thresholds.tags.{tag}", "every exposed tag needs a threshold")
        if released:
            if head.get("origin") == "trained_poetry_vision_v1" and head.get("trained_on") is None:
                _issue(issues, "E_STATUS_CONFLICT", join(path, "trained_on"), "released heads trained here need trained_on")
            if head.get("activation") == "softmax" and head.get("calibrated") is not True:
                _issue(issues, "E_STATUS_CONFLICT", join(path, "calibrated"), "released softmax heads must be calibrated")
    if adapter is not None and adapter.get("in_dim") != backbone.get("embedding_dim"):
        _issue(issues, "E_STATUS_CONFLICT", p + "adapter.in_dim", "must equal backbone.embedding_dim")
    scene_head = names.get("scene") or {}
    if scene_supported.get("after_temperature") is True and scene_head.get("calibrated") is not True:
        _issue(issues, "E_STATUS_CONFLICT", p + "thresholds.scene_supported.after_temperature",
               "the scene head is not calibrated")
    if released:
        if scene_supported.get("value") is None:
            _issue(issues, "E_STATUS_CONFLICT", p + "thresholds.scene_supported.value", "a released model needs the threshold")
        if scene_head.get("calibrated") is True and scene_supported.get("after_temperature") is not True:
            _issue(issues, "E_STATUS_CONFLICT", p + "thresholds.scene_supported.after_temperature",
                   "re-derive the threshold after temperature scaling")
        if not doc.get("metrics"):
            _issue(issues, "E_STATUS_CONFLICT", p + "metrics", "a released model card needs measured metrics")


# ============================================================================================ inference_output
def _scored(layers):
    return F("list", nullable=True, items=F("obj", fields={"id": F("id", layers=layers),
                                                            "score": F("num", min=0, max=1)}))


INFERENCE_OUTPUT = {
    **_header(),
    "image_sha256": F("str", fmt="sha256"),
    "model_id": F("str"),
    "model_version": F("str", fmt="version"),
    "status": F("str", enum={"ok", "error"}),
    "error": F("obj", nullable=True, fields={
        "code": F("str", enum={"invalid_image", "too_small", "unsupported_format", "internal"}),
        "message_ar": F("str")}),
    "scene": F("obj", nullable=True, fields={
        "predictions": _scored(("scene",)), "calibrated": F("bool"),
        "supported_threshold": F("num", min=0, max=1), "supported": F("bool"),
        "status": F("str", enum={"confident", "uncertain", "unsupported"}),
        "top1_score": F("num", min=0, max=1), "margin": F("num", min=0, max=1)}),
    "scene_groups": _scored(("scene_group",)),
    "emotion": F("obj", nullable=True, fields={
        "predictions": _scored(("img_emotion",)), "calibrated": F("bool"),
        "status": F("str", enum={"clear", "ambiguous"}), "margin": F("num", min=0, max=1),
        "ambiguity_margin": F("num", min=0, max=1), "entropy": F("num", min=0)}),
    "tags": F("list", nullable=True, items=F("obj", fields={
        "id": F("id", layers=("tag_exposed",)), "decision_score": F("num"), "threshold": F("num"),
        "present": F("bool")})),
    "suggested_lit_emotions": F("list", nullable=True, items=F("obj", fields={
        "id": F("id", layers=("lit_emotion",)), "from_img_emotion": F("id", layers=("img_emotion",)),
        "basis": F("str")})),
    "timings_ms": F("obj", required=False, nullable=True, fields={
        "preprocess": F("num", min=0), "forward": F("num", min=0), "total": F("num", min=0)}),
}


def _score_map(entries, expected_ids, path, issues, must_sum_to_one):
    """Return {id: score} if the list is a well-formed distribution over expected_ids, else None."""
    if not isinstance(entries, list):
        return None
    scores = {}
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str) or not _num(entry.get("score")):
            return None
        if entry["id"] in scores:
            _issue(issues, "E_DUP_ID", join(join(path, i), "id"), f"{entry['id']} listed twice")
            return None
        scores[entry["id"]] = entry["score"]
    if expected_ids is not None and set(scores) != set(expected_ids):
        missing, extra = sorted(set(expected_ids) - set(scores)), sorted(set(scores) - set(expected_ids))
        _issue(issues, "E_STATUS_CONFLICT", path, f"ids must be exactly the model classes (missing {missing}, extra {extra})")
        return None
    if must_sum_to_one and abs(sum(scores.values()) - 1.0) > SUM_TOLERANCE:
        _issue(issues, "E_RANGE", path, f"scores sum to {sum(scores.values()):.6f}, expected 1")
    return scores


def _top_two(values):
    ordered = sorted(values, reverse=True) + [0.0, 0.0]
    return ordered[0], ordered[1]


def _inference_output_record(doc, p, ctx, issues):
    parts = ("scene", "scene_groups", "emotion", "tags", "suggested_lit_emotions")
    if doc.get("status") == "error":
        if doc.get("error") is None:
            _issue(issues, "E_STATUS_CONFLICT", p + "error", "status 'error' needs an error object")
        for part in parts:
            if doc.get(part) is not None:
                _issue(issues, "E_STATUS_CONFLICT", p + part, "must be null when status is 'error'")
        return
    if doc.get("status") != "ok":
        return
    if doc.get("error") is not None:
        _issue(issues, "E_STATUS_CONFLICT", p + "error", "must be null when status is 'ok'")
    for part in parts:
        if doc.get(part) is None:
            _issue(issues, "E_STATUS_CONFLICT", p + part, "required when status is 'ok'")
    taxonomy = ctx.taxonomy
    if taxonomy is None:
        return
    scene = doc.get("scene") if isinstance(doc.get("scene"), dict) else None
    scene_scores = None
    if scene is not None:
        scene_scores = _score_map(scene.get("predictions"), taxonomy.class_order["scene"],
                                  p + "scene.predictions", issues, True)
        if scene_scores is not None:
            top1, top2 = _top_two([v for k, v in scene_scores.items() if k != "scene.other"])
            if not _close(scene.get("top1_score"), top1):
                _issue(issues, "E_STATUS_CONFLICT", p + "scene.top1_score", f"expected {top1} (best in-taxonomy score)")
            if not _close(scene.get("margin"), top1 - top2):
                _issue(issues, "E_STATUS_CONFLICT", p + "scene.margin", f"expected {top1 - top2}")
            threshold = scene.get("supported_threshold")
            if _num(threshold) and isinstance(scene.get("supported"), bool) and scene["supported"] != (top1 >= threshold):
                _issue(issues, "E_STATUS_CONFLICT", p + "scene.supported", "must equal top1_score >= supported_threshold")
        if isinstance(scene.get("supported"), bool) and (scene.get("status") == "unsupported") == scene["supported"]:
            _issue(issues, "E_STATUS_CONFLICT", p + "scene.status", "status is 'unsupported' exactly when supported is false")
    group_scores = _score_map(doc.get("scene_groups"), taxonomy.ids("scene_group"), p + "scene_groups", issues, False)
    if group_scores is not None and scene_scores is not None:
        for group_id, score in group_scores.items():
            members, _ = taxonomy.group_members(group_id)
            expected = sum(scene_scores.get(m, 0.0) for m in members)
            if not _close(score, expected):
                _issue(issues, "E_STATUS_CONFLICT", p + f"scene_groups.{group_id}",
                       f"group score must be the sum of its scene scores ({expected})")
    emotion = doc.get("emotion") if isinstance(doc.get("emotion"), dict) else None
    if emotion is not None:
        emotion_scores = _score_map(emotion.get("predictions"), taxonomy.class_order["img_emotion"],
                                    p + "emotion.predictions", issues, True)
        if emotion_scores is not None:
            top1, top2 = _top_two(list(emotion_scores.values()))
            if not _close(emotion.get("margin"), top1 - top2):
                _issue(issues, "E_STATUS_CONFLICT", p + "emotion.margin", f"expected {top1 - top2}")
            limit = emotion.get("ambiguity_margin")
            if _num(limit) and emotion.get("status") in ("clear", "ambiguous"):
                if (emotion["status"] == "ambiguous") != (top1 - top2 < limit):
                    _issue(issues, "E_STATUS_CONFLICT", p + "emotion.status", "ambiguous exactly when margin < ambiguity_margin")
            entropy = -sum(v * math.log(v) for v in emotion_scores.values() if v > 0)
            if not _close(emotion.get("entropy"), entropy, 1e-4):
                _issue(issues, "E_STATUS_CONFLICT", p + "emotion.entropy", f"expected {entropy:.6f} (natural log)")
    tags = doc.get("tags") if isinstance(doc.get("tags"), list) else None
    if tags is not None:
        seen = set()
        for i, tag in enumerate(tags):
            if not isinstance(tag, dict):
                continue
            path = p + join("tags", i)
            if tag.get("id") in seen:
                _issue(issues, "E_DUP_ID", join(path, "id"), f"{tag.get('id')} listed twice")
            seen.add(tag.get("id"))
            score, threshold, present = tag.get("decision_score"), tag.get("threshold"), tag.get("present")
            if _num(score) and _num(threshold) and isinstance(present, bool) and present != (score >= threshold):
                _issue(issues, "E_STATUS_CONFLICT", join(path, "present"), "must equal decision_score >= threshold")
        if seen != set(taxonomy.exposed_tags):
            _issue(issues, "E_STATUS_CONFLICT", p + "tags", "must list every exposed tag exactly once")
    suggestions = doc.get("suggested_lit_emotions") if isinstance(doc.get("suggested_lit_emotions"), list) else []
    seen = set()
    for i, s in enumerate(suggestions):
        if not isinstance(s, dict):
            continue
        path = p + join("suggested_lit_emotions", i)
        if s.get("id") in seen:
            _issue(issues, "E_DUP_ID", join(path, "id"), f"{s.get('id')} suggested twice")
        seen.add(s.get("id"))
        if (s.get("from_img_emotion"), s.get("id")) not in taxonomy.suggestion_pairs:
            _issue(issues, "E_STATUS_CONFLICT", path, "pair is not in the taxonomy suggestion_map")
        if s.get("basis") != taxonomy.suggestion_basis:
            _issue(issues, "E_STATUS_CONFLICT", join(path, "basis"), f"must be {taxonomy.suggestion_basis!r}")


# ============================================================================================ image_profile
IMAGE_PROFILE = {
    **_header(),
    "profile_id": F("str", fmt="uuid4"),
    "origin": F("str", enum={"user_session", "evaluation_pv_dev", "evaluation_pv_test", "synthetic_query"}),
    "source_inference": F("obj", nullable=True, fields={"image_sha256": F("str", fmt="sha256"),
                                                         "model_version": F("str", fmt="version")}),
    "confirmed_visual_items": F("list", items=F("obj", fields={
        "id": F("id", layers=VISUAL_TARGET_LAYERS),
        "user_selection": F("str", enum={"focus", "primary", "secondary"}),
        "suggested_by_model": F("bool")})),
    "selected_lit_emotion": F("id", layers=("lit_emotion",)),
    "secondary_lit_emotion": F("id", nullable=True, layers=("lit_emotion",)),
    "concept_id": F("id", nullable=True, layers=("concept",)),
    "symbolic_allowed": F("bool"),
    "emotion_only_allowed": F("bool"),
}


def _image_profile_record(doc, p, ctx, issues):
    items = [i for i in doc.get("confirmed_visual_items") or [] if isinstance(i, dict)]
    seen = set()
    for k, item in enumerate(doc.get("confirmed_visual_items") or []):
        if isinstance(item, dict):
            if item.get("id") in seen:
                _issue(issues, "E_DUP_ID", p + join(join("confirmed_visual_items", k), "id"), f"{item.get('id')} confirmed twice")
            seen.add(item.get("id"))
    if sum(1 for i in items if i.get("user_selection") == "focus") > 1:
        _issue(issues, "E_STATUS_CONFLICT", p + "confirmed_visual_items", "at most one focus item")
    if not items and doc.get("emotion_only_allowed") is False:
        _issue(issues, "E_STATUS_CONFLICT", p + "emotion_only_allowed",
               "a profile without confirmed visual items must allow emotion-only retrieval")
    if doc.get("secondary_lit_emotion") is not None and doc.get("secondary_lit_emotion") == doc.get("selected_lit_emotion"):
        _issue(issues, "E_STATUS_CONFLICT", p + "secondary_lit_emotion", "must differ from selected_lit_emotion")
    if (doc.get("origin") == "synthetic_query") != (doc.get("source_inference") is None):
        _issue(issues, "E_STATUS_CONFLICT", p + "source_inference",
               "synthetic_query profiles have no source_inference; all other origins need one")


# ============================================================================================ poetry_record
ASSOCIATION = F("obj", fields={
    "target": F("id", layers=VISUAL_TARGET_LAYERS),
    "relation": F("id", layers=("relation",)),
    "evidence_span": NULLABLE_SPAN,
    "justification_ar": F("str", nullable=True, max_words=15),
})
EMOTION_ENTRY = F("obj", fields={
    "id": F("id", layers=("lit_emotion",)),
    "basis": F("str", enum={"expressed", "evoked"}),
    "evidence_span": NULLABLE_SPAN,
    "justification_ar": F("str", nullable=True, max_words=15),
})
POETRY_RECORD = {
    **_header(),
    "verse_id": F("str", fmt="verse_id"),
    "apcd_row": F("int"),
    "text_original": F("str"),
    "text_sha256": F("str", fmt="sha256"),
    "hemistichs": F("obj", required=False, nullable=True, fields={"shatr_right": F("str"), "shatr_left": F("str")}),
    "text_verification": F("obj", fields={"method": F("str", enum={"apcd_row_exact", "not_verified"}),
                                          "tool": F("str"), "date": F("str", fmt="date")}),
    "text_note": F("str", required=False, nullable=True),
    "poet": F("obj", fields={"name_apcd": F("str"), "poet_id": F("str", nullable=True, fmt="poet_id")}),
    "era_apcd": F("str"),
    "source": F("obj", fields={"dataset": F("str", enum={"APCD"}), "diwan_apcd": F("str", allow_empty=True),
                               "meter_apcd": F("str", allow_empty=True), "rhyme_apcd": F("str", allow_empty=True)}),
    "attribution_status": F("str", enum=ATTRIBUTION),
    "evidence_ids": F("list", items=F("str", fmt="evidence_id")),
    "poem_id": F("str", nullable=True, fmt="poem_id"),
    "visual_associations": F("list", items=ASSOCIATION),
    "emotion_status": F("str", enum={"has_emotion", "neutral", "ambiguous", "not_annotated"}),
    "emotions": F("obj", fields={"primary": F("list", items=EMOTION_ENTRY, max_items=2),
                                 "secondary": F("list", items=EMOTION_ENTRY, max_items=2)}),
    "semantic_concepts": F("list", items=F("id", layers=("concept",))),
    "genre": F("id", nullable=True, layers=("genre",)),
    "meaning_ar": F("str", nullable=True, max_words=40),
    "dimension_status": F("obj", fields={"visual": DIMENSION, "emotion": DIMENSION, "concepts": DIMENSION,
                                         "genre": DIMENSION, "meaning": DIMENSION}),
    "annotation": F("obj", fields={
        "annotator_id": F("str"),
        "method": F("str", enum={"human", "ai_draft", "ai_draft_human_reviewed", "synthetic_fixture"}),
        "model_id": F("str", nullable=True), "date": F("str", fmt="date")}),
    "review": F("obj", fields={
        "status": F("str", enum={"not_reviewed", "reviewed", "double_reviewed", "adjudicated", "disputed",
                                 "synthetic_fixture"}),
        "reviewers": F("list", items=F("str")),
        "decisions": F("list", items=F("obj", fields={
            "reviewer_id": F("str"),
            "dimension": F("str", enum={"text", "visual", "emotion", "concepts", "genre", "meaning", "attribution", "all"}),
            "decision": F("str", enum={"accept", "correct", "reject", "unsure", "adjudicate"}),
            "note": F("str", nullable=True), "date": F("str", fmt="date")}))}),
    "annotator_uncertainty": F("str", enum={"low", "medium", "high"}),
}
SPAN_REQUIRED_RELATIONS = {"relation.literal", "relation.negated", "relation.hypothetical"}
JUSTIFIED_RELATIONS = {"relation.scene_association", "relation.symbolic", "relation.ambiguous"}


def _poetry_pre(record, p, issues):
    if "display_allowed" in record:
        _issue(issues, "E_DISPLAY_RULE", p + "display_allowed",
               "display_allowed is derived by contracts.validate.display_allowed() and must not be stored")
        record = {k: v for k, v in record.items() if k != "display_allowed"}
    return record


def _poetry_record(r, p, ctx, issues):
    text = r.get("text_original")
    row = r.get("apcd_row")
    if isinstance(row, int) and not isinstance(row, bool) and row < 0:
        _issue(issues, "E_APCD_ROW", p + "apcd_row", "APCD rows are 0-based data-row indices (>= 0)")
    if isinstance(text, str) and isinstance(r.get("text_sha256"), str) and text_sha256(text) != r["text_sha256"]:
        _issue(issues, "E_APCD_TEXT", p + "text_sha256", "does not match sha256(text_original)")

    targets = set()
    for i, assoc in enumerate(r.get("visual_associations") or []):
        if not isinstance(assoc, dict):
            continue
        path = p + join("visual_associations", i)
        if assoc.get("target") in targets:
            _issue(issues, "E_DUP_ID", join(path, "target"), f"{assoc.get('target')} annotated twice")
        targets.add(assoc.get("target"))
        relation = assoc.get("relation")
        if relation in SPAN_REQUIRED_RELATIONS and assoc.get("evidence_span") is None:
            _issue(issues, "E_REQUIRED", join(path, "evidence_span"), f"{relation} needs an evidence span")
        if relation in JUSTIFIED_RELATIONS and not assoc.get("justification_ar"):
            _issue(issues, "E_REQUIRED", join(path, "justification_ar"), f"{relation} needs a justification")
        _check_span(assoc.get("evidence_span"), text, join(path, "evidence_span"), issues)

    emotions = r.get("emotions") if isinstance(r.get("emotions"), dict) else {}
    primary = emotions.get("primary") if isinstance(emotions.get("primary"), list) else []
    secondary = emotions.get("secondary") if isinstance(emotions.get("secondary"), list) else []
    seen = set()
    for role, entries in (("primary", primary), ("secondary", secondary)):
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            path = p + join(f"emotions.{role}", i)
            if entry.get("id") in seen:
                _issue(issues, "E_DUP_ID", join(path, "id"), f"{entry.get('id')} listed twice")
            seen.add(entry.get("id"))
            if entry.get("basis") == "expressed" and entry.get("evidence_span") is None:
                _issue(issues, "E_REQUIRED", join(path, "evidence_span"), "an expressed emotion needs an evidence span")
            if entry.get("basis") == "evoked" and not entry.get("justification_ar"):
                _issue(issues, "E_REQUIRED", join(path, "justification_ar"), "an evoked emotion needs a justification")
            _check_span(entry.get("evidence_span"), text, join(path, "evidence_span"), issues)

    status = r.get("emotion_status")
    dims = r.get("dimension_status") if isinstance(r.get("dimension_status"), dict) else {}
    if status == "has_emotion" and not 1 <= len(primary) <= 2:
        _issue(issues, "E_STATUS_CONFLICT", p + "emotions.primary", "has_emotion needs one or two primary emotions")
    if status in ("neutral", "ambiguous", "not_annotated") and (primary or secondary):
        _issue(issues, "E_STATUS_CONFLICT", p + "emotions", f"{status} records carry no emotion labels")
    if (status == "not_annotated") != (dims.get("emotion") == "not_annotated"):
        _issue(issues, "E_STATUS_CONFLICT", p + "dimension_status.emotion",
               "must be 'not_annotated' exactly when emotion_status is 'not_annotated'")
    for dim, field, empty in (("visual", "visual_associations", []), ("concepts", "semantic_concepts", []),
                              ("genre", "genre", None), ("meaning", "meaning_ar", None)):
        if dims.get(dim) == "not_annotated" and r.get(field) not in (empty, None, []):
            _issue(issues, "E_STATUS_CONFLICT", p + field, f"dimension {dim!r} is not_annotated but {field} is set")

    attribution = r.get("attribution_status")
    if attribution == "source_verified" and not r.get("evidence_ids"):
        _issue(issues, "E_STATUS_CONFLICT", p + "evidence_ids", "source_verified needs evidence ids")
    if r.get("poem_id") is not None and attribution != "source_verified":
        _issue(issues, "E_STATUS_CONFLICT", p + "poem_id", "poem_id links to history only for source_verified records")

    annotation = r.get("annotation") if isinstance(r.get("annotation"), dict) else {}
    review = r.get("review") if isinstance(r.get("review"), dict) else {}
    method, review_status = annotation.get("method"), review.get("status")
    if method in ("ai_draft", "ai_draft_human_reviewed") and not annotation.get("model_id"):
        _issue(issues, "E_REQUIRED", p + "annotation.model_id", "AI drafts must name the model")
    if method == "human" and annotation.get("model_id"):
        _issue(issues, "E_STATUS_CONFLICT", p + "annotation.model_id", "human annotations have no model_id")
    synthetic = [method == "synthetic_fixture", review_status == "synthetic_fixture", r.get("fixture") is True]
    if any(synthetic) and not all(synthetic):
        _issue(issues, "E_STATUS_CONFLICT", p + "annotation.method",
               "synthetic_fixture method, synthetic_fixture review status and fixture=true go together")
    reviewers = [x for x in review.get("reviewers") or [] if isinstance(x, str)]
    others = set(reviewers) - {annotation.get("annotator_id")}
    if review_status == "reviewed" and not others:
        _issue(issues, "E_STATUS_CONFLICT", p + "review.reviewers", "reviewed needs a reviewer other than the annotator")
    if review_status == "double_reviewed" and len(others) < 2:
        _issue(issues, "E_STATUS_CONFLICT", p + "review.reviewers", "double_reviewed needs two other reviewers")
    if review_status == "adjudicated" and not any(isinstance(d, dict) and d.get("decision") == "adjudicate"
                                                  for d in review.get("decisions") or []):
        _issue(issues, "E_STATUS_CONFLICT", p + "review.decisions", "adjudicated needs an 'adjudicate' decision")
    if review_status in ("not_reviewed", "synthetic_fixture") and reviewers:
        _issue(issues, "E_STATUS_CONFLICT", p + "review.reviewers", f"{review_status} records list no reviewers")
    if method == "ai_draft" and review_status in DISPLAY_REVIEW_STATUSES:
        _issue(issues, "E_STATUS_CONFLICT", p + "annotation.method", "a reviewed AI draft is 'ai_draft_human_reviewed'")
    if ctx.mode == "production" and method == "synthetic_fixture":
        _issue(issues, "E_FIXTURE_IN_PRODUCTION", p + "annotation.method", "synthetic fixtures are not allowed in production")


def _poetry_collection(records, ctx, issues):
    first_verse, first_row = {}, {}
    for line, r in records:
        verse_id, row = r.get("verse_id"), r.get("apcd_row")
        if isinstance(verse_id, str):
            if verse_id in first_verse:
                _issue(issues, "E_DUP_ID", f"L{line}:verse_id", f"duplicate verse_id (first at line {first_verse[verse_id]})")
            else:
                first_verse[verse_id] = line
        if isinstance(row, int) and not isinstance(row, bool):
            if row in first_row:
                _issue(issues, "E_DUP_ID", f"L{line}:apcd_row", f"APCD row {row} already used at line {first_row[row]}")
            else:
                first_row[row] = line
    if ctx.apcd_zip is None:
        return
    rows = apcd.get_rows([r["apcd_row"] for _, r in records
                          if isinstance(r.get("apcd_row"), int) and not isinstance(r.get("apcd_row"), bool)
                          and r["apcd_row"] >= 0], ctx.apcd_zip)
    for line, r in records:
        row_number = r.get("apcd_row")
        if not isinstance(row_number, int) or isinstance(row_number, bool) or row_number < 0:
            continue
        p = f"L{line}:"
        row = rows.get(row_number)
        if row is None:
            _issue(issues, "E_APCD_ROW", p + "apcd_row", f"row {row_number} does not exist in APCD")
            continue
        poet = r.get("poet") if isinstance(r.get("poet"), dict) else {}
        source = r.get("source") if isinstance(r.get("source"), dict) else {}
        hemistichs = r.get("hemistichs") if isinstance(r.get("hemistichs"), dict) else None
        checks = [("text_original", r.get("text_original"), row[apcd.VERSE]),
                  ("poet.name_apcd", poet.get("name_apcd"), row[apcd.POET]),
                  ("era_apcd", r.get("era_apcd"), row[apcd.ERA]),
                  ("source.diwan_apcd", source.get("diwan_apcd"), row[apcd.DIWAN]),
                  ("source.meter_apcd", source.get("meter_apcd"), row[apcd.METER]),
                  ("source.rhyme_apcd", source.get("rhyme_apcd"), row[apcd.RHYME])]
        if hemistichs is not None:
            checks += [("hemistichs.shatr_right", hemistichs.get("shatr_right"), row[apcd.SHATR_RIGHT]),
                       ("hemistichs.shatr_left", hemistichs.get("shatr_left"), row[apcd.SHATR_LEFT])]
        for field, value, expected in checks:
            if value != expected:
                _issue(issues, "E_APCD_TEXT", p + field, f"differs from APCD row {row_number}: {expected!r}")


# ============================================================================================ retrieval_query
RETRIEVAL_QUERY = {
    **_header(),
    "query_id": F("str", fmt="uuid4"),
    "profile_id": F("str", fmt="uuid4"),
    "corpus_version": F("str"),
    "corpus_mode": F("str", enum=set(MODES)),
    "method": F("str", enum=RETRIEVAL_METHODS),
    "preprocessing_variant": F("str", enum={"N0", "N1", "N2"}),
    "weights": WEIGHTS,
    "k": F("int", min=1, max=10),
    "min_score": F("num", min=0, max=1),
    "tiers_enabled": F("list", items=F("int", min=1, max=3), min_items=1),
    "diversity": F("obj", fields={"max_per_poem": F("int", min=1), "max_per_poet": F("int", min=1),
                                  "near_dup_cosine": F("num", min=0, max=1, exclusive_min=True)}),
    "query_terms_ar": F("list", required=False, items=F("str")),
}


def _weights_sum(weights, path, issues):
    if isinstance(weights, dict) and all(_num(weights.get(k)) for k in ("emotion", "visual", "text", "semantic")):
        total = sum(weights[k] for k in ("emotion", "visual", "text", "semantic"))
        if abs(total - 1.0) > EPS:
            _issue(issues, "E_RANGE", path, f"weights sum to {total}, expected 1")


def _check_corpus_mode(doc, p, ctx, issues):
    if ctx.mode == "production" and doc.get("corpus_mode") in ("fixture", "development"):
        _issue(issues, "E_FIXTURE_IN_PRODUCTION", p + "corpus_mode",
               f"{doc.get('corpus_mode')} corpus (synthetic or unreviewed) is not allowed in production mode")


def _retrieval_query_record(doc, p, ctx, issues):
    _weights_sum(doc.get("weights"), p + "weights", issues)
    tiers = doc.get("tiers_enabled") if isinstance(doc.get("tiers_enabled"), list) else []
    if len(set(map(str, tiers))) != len(tiers):
        _issue(issues, "E_DUP_ID", p + "tiers_enabled", "duplicate tier")
    _check_corpus_mode(doc, p, ctx, issues)


# ============================================================================================ recommendations
ITEM = F("obj", fields={
    "rank": F("int", min=1),
    "verse_id": F("str", fmt="verse_id"),
    "apcd_row": F("int", min=0),
    "text_original": F("str"),
    "poet_name_apcd": F("str"),
    "era_apcd": F("str"),
    "attribution_status": F("str", enum=ATTRIBUTION),
    "tier": F("int", min=1, max=3),
    "scores": F("obj", fields={"emotion": F("num", min=0, max=1), "visual": F("num", nullable=True, min=0, max=1),
                               "text": F("num", nullable=True, min=0, max=1),
                               "semantic": F("num", nullable=True, min=0, max=1), "final": F("num", min=0, max=1)}),
    "matched": F("obj", fields={"lit_emotion": F("id", layers=("lit_emotion",)),
                                "emotion_role": F("str", enum={"primary", "secondary"}),
                                "visual_targets": F("list", items=F("id", layers=VISUAL_TARGET_LAYERS)),
                                "relations": F("list", items=F("id", layers=("relation",)))}),
    "explanation": F("obj", fields={"template_ids": F("list", items=F("str"), min_items=1),
                                    "sentences_ar": F("list", items=F("str"), min_items=1),
                                    "evidence_spans": F("list", items=SPAN)}),
    "review_status": F("str"),
})
RECOMMENDATIONS = {
    **_header(),
    "query_id": F("str", fmt="uuid4"),
    "profile_id": F("str", fmt="uuid4"),
    "engine_version": F("str", fmt="version"),
    "corpus_version": F("str"),
    "corpus_mode": F("str", enum=set(MODES)),
    "k": F("int", min=1, max=10),
    "weights": WEIGHTS,
    "status": F("str", enum={"ok", "partial", "abstained"}),
    "items": F("list", items=ITEM),
    "abstention": F("obj", nullable=True, fields={
        "reason_code": F("str", enum=ABSTENTION_CODES), "message_ar": F("str"),
        "coverage_gap": F("obj", nullable=True, fields={
            "visual_targets": F("list", items=F("id", layers=VISUAL_TARGET_LAYERS)),
            "lit_emotion": F("id", layers=("lit_emotion",))})}),
    "timings_ms": F("obj", required=False, nullable=True, fields={
        "retrieve": F("num", min=0), "rank": F("num", min=0), "explain": F("num", min=0), "total": F("num", min=0)}),
}
EMOTION_SCORE = {"primary": 1.0, "secondary": 0.6}
DRAFT_DISCLOSURE = "T_DRAFT_DISCLOSURE"


def _recommendations_record(doc, p, ctx, issues):
    _weights_sum(doc.get("weights"), p + "weights", issues)
    _check_corpus_mode(doc, p, ctx, issues)
    items = doc.get("items") if isinstance(doc.get("items"), list) else []
    status, k, abstention = doc.get("status"), doc.get("k"), doc.get("abstention")
    if (status == "abstained") != (not items) or (status == "abstained") != (abstention is not None):
        _issue(issues, "E_STATUS_CONFLICT", p + "status", "abstained exactly when there are no items and an abstention")
    if isinstance(k, int):
        if status == "ok" and len(items) != k:
            _issue(issues, "E_STATUS_CONFLICT", p + "status", f"'ok' returns exactly k={k} items")
        if status == "partial" and not 0 < len(items) < k:
            _issue(issues, "E_STATUS_CONFLICT", p + "status", f"'partial' returns between 1 and {k - 1} items")
        if len(items) > k:
            _issue(issues, "E_RANGE", p + "items", f"more than k={k} items")
    weights = doc.get("weights") if isinstance(doc.get("weights"), dict) else {}
    verse_ids, previous, tier3 = set(), None, 0
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        path = p + join("items", i)
        if item.get("rank") != i + 1:
            _issue(issues, "E_STATUS_CONFLICT", join(path, "rank"), f"ranks must be 1..n in order (expected {i + 1})")
        if item.get("verse_id") in verse_ids:
            _issue(issues, "E_DUP_ID", join(path, "verse_id"), f"{item.get('verse_id')} returned twice")
        verse_ids.add(item.get("verse_id"))
        tier = item.get("tier")
        tier3 += tier == 3
        scores = item.get("scores") if isinstance(item.get("scores"), dict) else {}
        final = scores.get("final")
        if previous is not None and isinstance(tier, int) and _num(final):
            prev_tier, prev_final = previous
            if tier < prev_tier or (tier == prev_tier and final > prev_final + EPS):
                _issue(issues, "E_STATUS_CONFLICT", join(path, "tier"), "items must be ordered by tier, then final score")
        if isinstance(tier, int) and _num(final):
            previous = (tier, final)
        components = [(weights.get(name), scores.get(name)) for name in ("emotion", "visual", "text", "semantic")]
        present = [(w, s) for w, s in components if _num(w) and _num(s)]
        if _num(final) and present and sum(w for w, _ in present) > 0:
            expected = sum(w * s for w, s in present) / sum(w for w, _ in present)
            if not _close(final, expected):
                _issue(issues, "E_STATUS_CONFLICT", join(path, "scores.final"),
                       f"expected {expected:.6f}: weighted mean of the non-null components")
        matched = item.get("matched") if isinstance(item.get("matched"), dict) else {}
        role = matched.get("emotion_role")
        if role in EMOTION_SCORE and _num(scores.get("emotion")) and not _close(scores["emotion"], EMOTION_SCORE[role]):
            _issue(issues, "E_STATUS_CONFLICT", join(path, "scores.emotion"), f"a {role} match scores {EMOTION_SCORE[role]}")
        explanation = item.get("explanation") if isinstance(item.get("explanation"), dict) else {}
        templates, sentences = explanation.get("template_ids"), explanation.get("sentences_ar")
        if isinstance(templates, list) and isinstance(sentences, list) and len(templates) != len(sentences):
            _issue(issues, "E_STATUS_CONFLICT", join(path, "explanation"), "one sentence per template id")
        if doc.get("corpus_mode") == "development" and DRAFT_DISCLOSURE not in (templates or []):
            _issue(issues, "E_STATUS_CONFLICT", join(path, "explanation.template_ids"),
                   f"development-mode items must disclose unreviewed labels ({DRAFT_DISCLOSURE})")
        for j, span in enumerate(explanation.get("evidence_spans") or []):
            _check_span(span, item.get("text_original"), join(path, f"explanation.evidence_spans[{j}]"), issues)
        if ctx.corpus is not None:
            _cross_check_item(item, path, doc.get("corpus_mode"), ctx, issues)
    if tier3 > 1:
        _issue(issues, "E_STATUS_CONFLICT", p + "items", "at most one tier-3 (emotion-only) item")


def _cross_check_item(item, path, corpus_mode, ctx, issues):
    record = ctx.corpus.get(item.get("verse_id"))
    if record is None:
        _issue(issues, "E_UNKNOWN_ID", join(path, "verse_id"), "verse not found in the corpus")
        return
    if item.get("text_original") != record.get("text_original"):
        _issue(issues, "E_APCD_TEXT", join(path, "text_original"), "differs from the corpus record")
    poet = record.get("poet") if isinstance(record.get("poet"), dict) else {}
    for field, expected in (("apcd_row", record.get("apcd_row")), ("poet_name_apcd", poet.get("name_apcd")),
                            ("era_apcd", record.get("era_apcd")),
                            ("attribution_status", record.get("attribution_status")),
                            ("review_status", (record.get("review") or {}).get("status"))):
        if item.get(field) != expected:
            _issue(issues, "E_STATUS_CONFLICT", join(path, field), f"corpus record says {expected!r}")
    mode = corpus_mode if corpus_mode in MODES else "production"
    if not display_allowed(record, mode):
        _issue(issues, "E_DISPLAY_RULE", join(path, "verse_id"), f"verse is not displayable in {mode} mode")


# ============================================================================================ evaluation_record
EVALUATION_RECORD = {
    **_header(),
    "eval_id": F("str", fmt="uuid4"),
    "layer": F("str", enum={"vision", "annotation", "retrieval", "e2e"}),
    "test_set": F("obj", fields={"id": F("str"), "manifest_sha256": F("str", nullable=True, fmt="sha256")}),
    "system": F("obj", fields={"model_version": F("str", nullable=True), "corpus_version": F("str", nullable=True),
                               "engine_version": F("str", nullable=True), "method": F("str", nullable=True)}),
    "item_id": F("str"),
    "rater_id": F("str"),
    "blind": F("bool"),
    "rating": F("obj", fields={
        "visual_fit": F("int", nullable=True, min=0, max=3), "emotion_fit": F("int", nullable=True, min=0, max=3),
        "overall": F("int", nullable=True, min=0, max=3),
        "explanation_correct": F("str", nullable=True, enum={"yes", "no", "na"}),
        "text_authentic": F("str", nullable=True, enum={"yes", "no", "na"}),
        "judgment": F("str", nullable=True, enum={"correct", "incorrect", "unsure"})}),
    "notes": F("str", required=False, nullable=True),
    "timestamp": F("str", fmt="datetime"),
}


def _evaluation_record(r, p, ctx, issues):
    layer = r.get("layer")
    rating = r.get("rating") if isinstance(r.get("rating"), dict) else {}
    if layer in ("retrieval", "e2e"):
        if r.get("blind") is False:
            _issue(issues, "E_STATUS_CONFLICT", p + "blind", f"{layer} judgments must be blind")
        needed = ["visual_fit", "emotion_fit", "overall"]
        if layer == "e2e":
            needed += ["explanation_correct", "text_authentic"]
        for field in needed:
            if rating.get(field) is None:
                _issue(issues, "E_REQUIRED", p + f"rating.{field}", f"required for {layer} judgments")
    if layer in ("vision", "annotation") and rating.get("judgment") is None:
        _issue(issues, "E_REQUIRED", p + "rating.judgment", f"required for {layer} judgments")


def _evaluation_collection(records, ctx, issues):
    first_eval, first_key = {}, {}
    for line, r in records:
        eval_id = r.get("eval_id")
        if isinstance(eval_id, str):
            if eval_id in first_eval:
                _issue(issues, "E_DUP_ID", f"L{line}:eval_id", f"duplicate eval_id (first at line {first_eval[eval_id]})")
            else:
                first_eval[eval_id] = line
        system = r.get("system") if isinstance(r.get("system"), dict) else {}
        key = (r.get("layer"), r.get("rater_id"), r.get("item_id"), system.get("method"))
        if all(isinstance(v, str) for v in key[:3]):
            if key in first_key:
                _issue(issues, "E_DUP_ID", f"L{line}:item_id",
                       f"rater already judged this item for this method (line {first_key[key]})")
            else:
                first_key[key] = line


# ============================================================================================ registry
REGISTRY = {
    "image_manifest": (IMAGE_MANIFEST, None, _image_manifest_record, _image_manifest_collection),
    "model_card": (MODEL_CARD, None, _model_card_record, None),
    "inference_output": (INFERENCE_OUTPUT, None, _inference_output_record, None),
    "image_profile": (IMAGE_PROFILE, None, _image_profile_record, None),
    "poetry_record": (POETRY_RECORD, _poetry_pre, _poetry_record, _poetry_collection),
    "retrieval_query": (RETRIEVAL_QUERY, None, _retrieval_query_record, None),
    "recommendations": (RECOMMENDATIONS, None, _recommendations_record, None),
    "evaluation_record": (EVALUATION_RECORD, None, _evaluation_record, _evaluation_collection),
}


def _validate_one(contract, record, prefix, ctx, issues):
    if not isinstance(record, dict):
        _issue(issues, "E_TYPE", prefix or "$", "expected a JSON object")
        return False
    spec, pre, semantic, _ = REGISTRY[contract]
    if pre is not None:
        record = pre(record, prefix, issues)
    _check_with_prefix(record, spec, prefix, ctx, issues)
    _check_versions(record, ctx, issues, prefix)
    _check_fixture_flag(record, ctx, issues, prefix)
    semantic(record, prefix, ctx, issues)
    return True


def _check_with_prefix(record, spec, prefix, ctx, issues):
    found = []
    check_fields(record, spec, "", ctx, found)
    for issue in found:
        issues.append(Issue(issue.code, prefix + issue.path if prefix else issue.path, issue.message))


def validate_document(contract, doc, ctx):
    """Validate one JSON document (taxonomy, model_card, inference_output, image_profile, retrieval_query,
    recommendations). Returns a list of Issue."""
    issues = []
    if contract == "taxonomy":
        validate_taxonomy(doc, issues, SUPPORTED_SCHEMA_MAJOR)
        return issues
    if contract in JSONL_CONTRACTS:
        return validate_records(contract, [(1, doc)], ctx)
    _validate_one(contract, doc, "", ctx, issues)
    return issues


def validate_records(contract, records, ctx):
    """Validate JSONL records given as [(line_number, record)]. Returns a list of Issue."""
    issues = []
    valid = []
    for line, record in records:
        if _validate_one(contract, record, f"L{line}:", ctx, issues):
            valid.append((line, record))
    collection = REGISTRY[contract][3]
    if collection is not None:
        collection(valid, ctx, issues)
    return issues


def load_jsonl(path):
    """Return ([(line_number, obj)], [Issue]) for a JSONL file; blank lines are ignored."""
    records, issues = [], []
    with open(path, encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                records.append((number, json.loads(line)))
            except json.JSONDecodeError as exc:
                issues.append(Issue("E_TYPE", f"L{number}", f"invalid JSON: {exc.msg}"))
    return records, issues


def load_corpus(path):
    records, issues = load_jsonl(path)
    if issues:
        raise ValueError(f"corpus {path} is not valid JSONL: {issues[0]}")
    return {r["verse_id"]: r for _, r in records if isinstance(r, dict) and "verse_id" in r}


def validate_file(contract, path, mode="production", taxonomy=None, apcd_zip=None, corpus_path=None):
    """Validate a contract file. `taxonomy` may be a Taxonomy, a path, or None for the default v1 file."""
    if contract not in CONTRACTS:
        raise ValueError(f"unknown contract {contract!r}; expected one of {CONTRACTS}")
    if contract == "taxonomy":
        issues = []
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
        except json.JSONDecodeError as exc:
            return [Issue("E_TYPE", "$", f"invalid JSON: {exc.msg}")]
        validate_taxonomy(doc, issues, SUPPORTED_SCHEMA_MAJOR)
        return issues
    if not isinstance(taxonomy, Taxonomy):
        taxonomy = load_taxonomy(taxonomy)
    corpus = load_corpus(corpus_path) if corpus_path else None
    ctx = Context(taxonomy=taxonomy, mode=mode, apcd_zip=apcd_zip, corpus=corpus)
    if contract in JSONL_CONTRACTS:
        records, issues = load_jsonl(path)
        return issues + validate_records(contract, records, ctx)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except json.JSONDecodeError as exc:
        return [Issue("E_TYPE", "$", f"invalid JSON: {exc.msg}")]
    return validate_document(contract, doc, ctx)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python3 -m contracts.validate", description=__doc__.split("\n\n")[0])
    parser.add_argument("contract", choices=CONTRACTS)
    parser.add_argument("path")
    parser.add_argument("--mode", choices=MODES, default="production")
    parser.add_argument("--taxonomy", default=DEFAULT_TAXONOMY)
    parser.add_argument("--apcd-zip", default=None, help="verify verse text and metadata against APCD rows")
    parser.add_argument("--corpus", default=None, help="poetry_record JSONL used to cross-check recommendations")
    args = parser.parse_args(argv)
    try:
        issues = validate_file(args.contract, args.path, args.mode, args.taxonomy, args.apcd_zip, args.corpus)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    for issue in issues:
        print(issue)
    print(f"{'FAIL' if issues else 'OK'}: {args.contract} {args.path} ({len(issues)} issue(s), mode={args.mode})",
          file=sys.stderr)
    return 1 if issues else 0


if __name__ == "__main__":
    sys.exit(main())
