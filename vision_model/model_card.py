"""Build the model_card document for PoetryVisionNet v1 and validate it against the contract.

    .venv/bin/python -B -m vision_model.model_card [--emotion-report evaluation/vision/<run_id>.json]

Without a trained emotion head the card stays a draft whose emotion head has no temperature and no
trained_on. Metrics are copied only from reports produced by this repository's scripts, with run ids.
"""
import argparse
import json
import os

from . import config
from .heads import LinearHead, load_old_calibration, load_old_scene_head, load_old_tag_head
from .train_emotion import HEAD_PATH

SCENE_CALIB_PATH = os.path.join(config.HEADS_DIR, "scene_calibration_v1.json")

CARD_PATH = os.path.join(config.ARTIFACTS, "model_card_v1.json")


def build(taxonomy, emotion_head=None, emotion_report=None, model_version="1.0.0-draft", scene_calibration=None,
          scene_report=None, status="draft"):
    calib = load_old_calibration()
    scene, tags = load_old_scene_head(taxonomy), load_old_tag_head(taxonomy)
    scene_threshold = {"rule": "max_in_taxonomy_prob_of_17way_softmax", "value": calib["scene_supported"],
                       "tpr_target": calib["scene_tpr_target"],
                       "fitted_on": "visual_module_v1: Places365 val split (in-taxonomy images)",
                       "after_temperature": False}
    if scene_calibration:
        scene.temperature = scene_calibration["temperature"]
        scene_threshold = {"rule": "max_in_taxonomy_prob_of_17way_softmax", "value": scene_calibration["scene_supported"],
                           "tpr_target": scene_calibration["tpr_target"], "fitted_on": scene_calibration["fitted_on"],
                           "after_temperature": True}
    emotion = emotion_head.card() if emotion_head else {
        "name": "emotion", "input": "embedding", "output_layer": "img_emotion",
        "output_ids": taxonomy.class_order["img_emotion"], "activation": "softmax", "in_dim": 512, "out_dim": 8,
        "params": 512 * 8 + 8, "origin": "trained_poetry_vision_v1", "source_file": None, "trained_on": None,
        "temperature": None, "calibrated": False}
    metrics, limitations = [], [
        "رأسا المشهد والوسوم منقولان من الوحدة البصرية السابقة دون إعادة تدريب",
        "رأس الوسوم لم يُعَد قياسه في هذه المساحة؛ عتباته من الوحدة السابقة",
        "لا تقييم بعد على PV-Test (صور الفريق المستقلة)؛ أرقام EmoSet وPlaces365 من توزيع بيانات التدريب نفسه",
        "تسميات EmoSet إجماع آراء عن صور من الإنترنت، ولا تمثّل بالضرورة الصور العربية أو التراثية"]
    if not scene_calibration:
        limitations.append("رأس المشهد غير معايَر بـtemperature بعد؛ عتبة الرفض مشتقة في الوحدة السابقة قبل أي معايرة")
    if scene_report:
        t, rej = scene_report["test_17way"], scene_report["rejection"]
        sid = scene_report["run_id"]
        metrics += [{"name": "scene_accuracy_17way", "value": float(t["accuracy"]), "dataset": "places365_sample",
                     "split": "test", "n": int(t["n"]), "run_id": sid},
                    {"name": "scene_macro_f1_17way", "value": float(t["macro_f1"]), "dataset": "places365_sample",
                     "split": "test", "n": int(t["n"]), "run_id": sid},
                    {"name": "scene_ece_15", "value": float(scene_report["test_17way_calibration"]["after"]["ece_15"]),
                     "dataset": "places365_sample", "split": "test", "n": int(t["n"]), "run_id": sid},
                    {"name": "scene_rejection_auroc_vs_ood", "value": float(rej["auroc_in_taxonomy_test_vs_ood_test"]),
                     "dataset": "places365_sample", "split": "test+ood_test",
                     "n": int(scene_report["test_in_taxonomy_16"]["n"] + rej["ood_n"]), "run_id": sid},
                    {"name": "scene_ood_rejected_share", "value": float(rej["ood_test_rejected"]),
                     "dataset": "places365_sample", "split": "ood_test", "n": int(rej["ood_n"]), "run_id": sid}]
    if emotion_report:
        test = emotion_report["test"]
        run_id = emotion_report["run_id"]
        metrics += [{"name": name, "value": float(test[key]), "dataset": "emoset118k_renad_sample", "split": "test",
                     "n": int(test["n"]), "run_id": run_id}
                   for name, key in (("emotion_accuracy", "accuracy"), ("emotion_macro_f1", "macro_f1"),
                                     ("emotion_ece_15", "ece_15"), ("emotion_nll", "nll"))]
    else:
        limitations.insert(0, "رأس الإحساس لم يُدرَّب بعد: ينتظر manifest الإحساس v0.9 المتحقق منه")
    return {
        "schema_version": "1.0.0", "taxonomy_version": taxonomy.version, "fixture": False,
        "model_id": config.MODEL_ID, "model_version": model_version, "status": status,
        "backbone": {"library": "open_clip", "library_version": config.CLIP_LIBRARY_VERSION, "arch": config.CLIP_ARCH,
                     "pretrained": config.CLIP_PRETRAINED, "hf_repo": config.HF_REPO, "hf_revision": config.HF_REVISION,
                     "weights_file": config.WEIGHTS_FILE, "weights_sha256": config.WEIGHTS_SHA256, "frozen": True,
                     "precision": "fp32", "embedding_dim": config.EMBEDDING_DIM, "l2_normalized": True},
        "preprocessing": {"exif_transpose": True, "color": "RGB", "resize_shortest": config.IMAGE_SIZE,
                          "interpolation": "bicubic", "antialias": True, "center_crop": config.IMAGE_SIZE,
                          "mean": list(config.MEAN), "std": list(config.STD)},
        "adapter": None,
        "heads": [scene.card(), emotion, tags.card()],
        "thresholds": {"scene_supported": scene_threshold,
                       "emotion_ambiguity_margin": config.EMOTION_AMBIGUITY_MARGIN,
                       "tags": {t: calib["tags"][t] for t in taxonomy.class_order["tag"]}},
        "metrics": metrics,
        "limitations": limitations,
    }


def main(argv=None):
    from contracts.taxonomy import load_taxonomy
    from contracts.validate import Context, validate_document

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--emotion-report")
    parser.add_argument("--scene-report")
    parser.add_argument("--out", default=CARD_PATH)
    parser.add_argument("--release", action="store_true", help="status released, model_version 1.0.0 (owner approval)")
    args = parser.parse_args(argv)
    taxonomy = load_taxonomy()
    head = LinearHead.load(HEAD_PATH) if os.path.exists(HEAD_PATH) else None
    report = None
    if args.emotion_report:
        with open(args.emotion_report, encoding="utf-8") as fh:
            report = json.load(fh)
    scene_calibration = scene_report = None
    if os.path.exists(SCENE_CALIB_PATH):
        with open(SCENE_CALIB_PATH, encoding="utf-8") as fh:
            scene_calibration = json.load(fh)
    if args.scene_report:
        with open(args.scene_report, encoding="utf-8") as fh:
            scene_report = json.load(fh)
    card = build(taxonomy, head, report, scene_calibration=scene_calibration, scene_report=scene_report,
                 model_version="1.0.0" if args.release else "1.0.0-draft", status="released" if args.release else "draft")
    issues = validate_document("model_card", card, Context(taxonomy=taxonomy, mode="production"))
    if issues:
        raise SystemExit("model card failed validation:\n" + "\n".join(map(str, issues)))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(card, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    released = dict(card, status="released")
    blockers = validate_document("model_card", released, Context(taxonomy=taxonomy, mode="production"))
    print(f"wrote {args.out} (status {card['status']}, emotion head trained: {head is not None}); validation: 0 issues")
    print("would also pass as 'released':", not blockers, [str(i) for i in blockers])


if __name__ == "__main__":
    main()
