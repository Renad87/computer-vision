"""Diagnosis of the emotion head (why it predicts img_emotion.awe so often on real photos).

Reads only cached embeddings and existing artifacts; never modifies emotion_head_v1 or the runtime code path.

    # 1. (needs CLIP, small) runtime-vs-cache parity on 20 EmoSet images + embeddings of local test photos
    .venv/bin/python -B -m vision_model.diagnose_emotion embed --photos <dir with the e2e photos>
    # 2. (NumPy / scikit-learn) all diagnostics and candidate comparison, validation only for selection
    .venv/bin/python -B -m vision_model.diagnose_emotion run

Writes evaluation/vision/emotion_diagnosis/results.json (+ parity.json, photos_embeddings.npz).
Selection protocol: every choice (C, temperature, abstention thresholds) is made on EmoSet val.
Test is read only for a candidate that is saved, once, after it is frozen. Places365 has no
emotion labels: it is reported as a behaviour diagnostic (prediction and confidence distribution).
"""
import argparse
import collections
import json
import math
import os

import numpy as np

from . import config, metrics
from .heads import LinearHead, load_old_scene_head, softmax

OUT_DIR = os.path.join(config.REPO, "evaluation", "vision", "emotion_diagnosis")
EMOSET_CACHE = os.path.join(config.FEATURES_DIR, "emoset_clip_vitb32.npz")
PLACES_CACHE = os.path.join(config.FEATURES_DIR, "places_clip_vitb32.npz")
EMO_MANIFEST = os.path.join(config.REPO, "datasets", "manifests", "manifest_v0.9_emotion.jsonl")
V1_MANIFEST = os.path.join(config.REPO, "datasets", "manifests", "manifest_v1.jsonl")
EMOSET_META = os.path.join(config.REPO, "external", "emoset_metadata", "emoset118k_image_emotion_scene.jsonl")
CANDIDATE_PATH = os.path.join(config.HEADS_DIR, "emotion_head_v2_candidate.npz")
AWE = "img_emotion.awe"

# Places365 category names (as used by EmoSet's unaudited `scene` attribute) that denote outdoor natural
# landscapes or open sky/water views. Fixed before looking at emotion counts.
LANDSCAPE_SCENES = {
    "badlands", "bamboo_forest", "beach", "butte", "canyon", "cliff", "coast", "corn_field", "creek", "crevasse",
    "desert", "desert_road", "field", "field_road", "forest", "forest_path", "forest_road", "glacier", "grotto",
    "hayfield", "hot_spring", "ice_floe", "ice_shelf", "iceberg", "islet", "lagoon", "lake", "mountain",
    "mountain_path", "mountain_snowy", "ocean", "orchard", "pasture", "pond", "rainforest", "rice_paddy", "river",
    "rock_arch", "sky", "snowfield", "swamp", "tundra", "valley", "vineyard", "volcano", "waterfall",
    "watering_hole", "wave", "wheat_field",
}
WIDE_C_GRID = (0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, 300.0)
KNN_K = 10
KEEP_TARGET = 0.95  # abstention thresholds keep 95% of EmoSet val


def _round(x, n=4):
    if isinstance(x, dict):
        return {k: _round(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_round(v, n) for v in x]
    if isinstance(x, (float, np.floating)):
        return round(float(x), n)
    if isinstance(x, np.integer):
        return int(x)
    return x


# ---------------------------------------------------------------------------------------------- embed step
def embed(photos_dir, device="cpu", n_emoset=20):
    import zipfile

    from .backbone import ClipEncoder, decode_image

    with np.load(EMOSET_CACHE, allow_pickle=False) as d:
        feats, zpaths, shas = d["feats"], d["zip_path"], d["sha256"]
    pick = np.linspace(0, len(feats) - 1, n_emoset).astype(int)
    enc = ClipEncoder(device)
    import hashlib

    imgs, sha_ok = [], []
    with zipfile.ZipFile(config.EMOSET_ZIP) as z:
        for i in pick:
            data = z.read(str(zpaths[i]))
            sha_ok.append(hashlib.sha256(data).hexdigest() == str(shas[i]))
            imgs.append(decode_image(data))
    fresh = enc.encode_images(imgs)
    cos = (fresh * feats[pick]).sum(1)
    head = LinearHead.load(config.EMOTION_HEAD_PATH)
    p_fresh, p_cache = head.probs(fresh), head.probs(feats[pick])
    parity = {"device": enc.device, "n": int(len(pick)), "sha256_match": int(sum(sha_ok)),
              "min_cosine": float(cos.min()), "mean_cosine": float(cos.mean()),
              "max_abs_diff": float(np.abs(fresh - feats[pick]).max()),
              "emotion_prob_max_abs_diff": float(np.abs(p_fresh - p_cache).max()),
              "argmax_agree": int((p_fresh.argmax(1) == p_cache.argmax(1)).sum()),
              "zip_paths": [str(zpaths[i]) for i in pick]}
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "parity.json"), "w", encoding="utf-8") as fh:
        json.dump(_round(parity, 8), fh, indent=1)
        fh.write("\n")
    print(json.dumps({k: v for k, v in parity.items() if k != "zip_paths"}))
    if photos_dir:
        names = sorted(f for f in os.listdir(photos_dir) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
        ok_names, ims = [], []
        for n in names:
            with open(os.path.join(photos_dir, n), "rb") as fh:
                try:
                    ims.append(decode_image(fh.read()))
                    ok_names.append(n)
                except Exception:  # noqa: BLE001
                    pass
        np.savez(os.path.join(OUT_DIR, "photos_embeddings.npz"), feats=enc.encode_images(ims),
                 names=np.array(ok_names))
        print(f"embedded {len(ok_names)} photos")


# ---------------------------------------------------------------------------------------------- data
def load_data():
    from contracts.taxonomy import load_taxonomy

    from .features import load_cache
    from .train_emotion import assemble, emotion_rows, load_validated_manifest

    tax = load_taxonomy()
    class_ids = tax.class_order["img_emotion"]
    rows = emotion_rows(load_validated_manifest(EMO_MANIFEST, tax))
    cache = load_cache(EMOSET_CACHE)
    data = assemble(rows, cache, class_ids)
    # Places: scene labels from manifest_v1, matched by image_id and sha256
    prow = {}
    with open(V1_MANIFEST, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            if r["source_dataset"] == "places365_sample":
                prow[r["image_id"]] = r
    with np.load(PLACES_CACHE, allow_pickle=False) as d:
        pf, pids, psha, psplit = d["feats"], [str(x) for x in d["image_ids"]], [str(x) for x in d["sha256"]], d["split"]
    assert all(prow[i]["image_sha256"] == s for i, s in zip(pids, psha)), "Places sha256 mismatch"
    places = {"X": pf, "ids": pids, "split": np.array([str(s) for s in psplit]),
              "scene": np.array([prow[i]["scene_label"] or "ood(excluded)" for i in pids]),
              "raw": np.array([prow[i].get("scene_source_raw") or "" for i in pids])}
    meta = {}
    with open(EMOSET_META, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            meta[r["image_id"]] = r
    return tax, class_ids, data, places, meta


# ---------------------------------------------------------------------------------------------- helpers
def eval_probs(y, p, k, boot=True):
    pred = p.argmax(1)
    out = {"accuracy": metrics.accuracy(y, pred), "macro_f1": metrics.macro_f1(y, pred, k),
           "nll": metrics.nll(y, p), "ece_15": metrics.ece(y, p), "brier": metrics.brier(y, p),
           "top2_accuracy": metrics.top_k_accuracy(y, p, 2), "top3_accuracy": metrics.top_k_accuracy(y, p, 3)}
    if boot:
        out["macro_f1_ci95"] = metrics.bootstrap_ci(y, pred, lambda a, b: metrics.macro_f1(a, b, k))
        out["accuracy_ci95"] = metrics.bootstrap_ci(y, pred, metrics.accuracy)
    return out


def paired_delta_ci(y, pred_a, pred_b, k, n_boot=1000, seed=42):
    """Bootstrap CI of macro-F1(b) - macro-F1(a) on the same resampled images."""
    rng = np.random.default_rng(seed)
    n = len(y)
    d = []
    for _ in range(n_boot):
        i = rng.integers(0, n, n)
        d.append(metrics.macro_f1(y[i], pred_b[i], k) - metrics.macro_f1(y[i], pred_a[i], k))
    d = np.array(d)
    return {"delta": metrics.macro_f1(y, pred_b, k) - metrics.macro_f1(y, pred_a, k),
            "ci95": [float(np.quantile(d, 0.025)), float(np.quantile(d, 0.975))]}


def maxprob_summary(p):
    m = p.max(1)
    shown = np.round(m * 100)  # frontend pct(): Math.round(x*100)
    return {"n": int(len(m)), "mean": float(m.mean()), "median": float(np.median(m)),
            "p10": float(np.quantile(m, 0.1)), "p90": float(np.quantile(m, 0.9)),
            "share_ge_0.9": float((m >= 0.9).mean()), "share_ge_0.985_shown_99_or_100": float((shown >= 99).mean()),
            "share_ge_0.995_shown_100": float((shown >= 100).mean())}


def pred_distribution(p, class_ids):
    c = np.bincount(p.argmax(1), minlength=len(class_ids))
    return {cid: float(v / len(p)) for cid, v in zip(class_ids, c)}


def reliability(y, p, n_bins=10):
    conf, pred = p.max(1), p.argmax(1)
    corr = (pred == y)
    edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            rows.append({"bin": [float(lo), float(hi)], "n": int(m.sum()), "mean_conf": float(conf[m].mean()),
                         "accuracy": float(corr[m].mean())})
    return rows


def entropy(p):
    return -(p * np.log(np.clip(p, 1e-12, 1))).sum(1)


def auroc(pos, neg):
    """P(score_pos > score_neg), ties count half."""
    pos, neg = np.asarray(pos), np.asarray(neg)
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind="mergesort")
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    rp = ranks[:len(pos)].sum()
    return float((rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def cramers_v(a, b):
    ua, ia = np.unique(a, return_inverse=True)
    ub, ib = np.unique(b, return_inverse=True)
    t = np.zeros((len(ua), len(ub)))
    np.add.at(t, (ia, ib), 1)
    e = t.sum(1, keepdims=True) * t.sum(0, keepdims=True) / t.sum()
    chi2 = float(((t - e) ** 2 / np.where(e > 0, e, 1)).sum())
    return math.sqrt(chi2 / (t.sum() * (min(t.shape) - 1))) if min(t.shape) > 1 else 0.0


def fit_logreg(X, y, C, class_weight=None):
    from sklearn.linear_model import LogisticRegression

    clf = LogisticRegression(C=C, max_iter=5000, random_state=config.SEED, class_weight=class_weight)
    clf.fit(X, y)
    return clf.coef_.astype(np.float32), clf.intercept_.astype(np.float32)


# ---------------------------------------------------------------------------------------------- run step
def run():
    from . import calibration

    tax, class_ids, data, places, meta = load_data()
    k = len(class_ids)
    awe = class_ids.index(AWE)
    head = LinearHead.load(config.EMOTION_HEAD_PATH)
    T1 = float(head.temperature)
    R = {"protocol": __doc__.strip(), "class_ids": class_ids}

    # 5. class order ------------------------------------------------------------------------------
    v1_report = json.load(open(os.path.join(config.REPORTS_DIR, "emotion-s1-20261125T220720Z-efd7de.json")))
    card = json.load(open(config.MODEL_CARD_PATH))
    card_emotion = next((h for h in card.get("heads", []) if h.get("name") == "emotion"), {})
    folder_agree = {}
    with np.load(EMOSET_CACHE, allow_pickle=False) as d:
        fe = {str(i): str(f) for i, f in zip(d["image_ids"], d["folder_emotion"])}
    for s in ("train", "val", "test"):
        lab = [class_ids[j] for j in data[s]["y"]]
        folder_agree[s] = float(np.mean([("img_emotion." + fe[i]) == l for i, l in zip(data[s]["ids"], lab)]))
    R["class_order"] = {"head_output_ids": head.output_ids, "taxonomy_order": class_ids,
                        "run_report_class_ids": v1_report["class_ids"],
                        "model_card_output_ids": card_emotion.get("output_ids"),
                        "all_equal": head.output_ids == class_ids == v1_report["class_ids"]
                        and card_emotion.get("output_ids", class_ids) == class_ids,
                        "training_label_index": "y = class_ids.index(emotion_label) with class_ids = taxonomy order "
                                                "(train_emotion.assemble); sklearn classes_ = 0..7 in that order",
                        "manifest_label_equals_zip_folder_share": folder_agree,
                        "temperature": T1}
    parity_path = os.path.join(OUT_DIR, "parity.json")
    if os.path.exists(parity_path):
        R["runtime_parity"] = json.load(open(parity_path))
    R["compat_report_preprocessing_matches_contract"] = json.load(
        open(os.path.join(config.REPORTS_DIR, "compat_report.json")))["preprocessing"]["matches_contract"]

    # reproduce v1 val/test numbers from the cache (detects a cache/head mismatch)
    zl = {s: head.logits(data[s]["X"]) for s in ("train", "val", "test")}
    R["v1_reproduced"] = {s: metrics.macro_f1(data[s]["y"], zl[s].argmax(1), k) for s in ("val", "test")}
    R["v1_reported"] = {s: v1_report[s]["macro_f1"] for s in ("val", "test")}

    # 1. label distribution -----------------------------------------------------------------------
    R["label_distribution"] = {s: {cid: int((data[s]["y"] == i).sum()) for i, cid in enumerate(class_ids)}
                               for s in ("train", "val", "test")}

    # 2 / 4. prediction + confidence distributions ------------------------------------------------
    pl = head.logits(places["X"])
    probs = {}
    for name, z in (("emoset_val", zl["val"]), ("emoset_test", zl["test"]), ("places_all", pl)):
        probs[name] = {"raw_T1": softmax(z), "after_T": softmax(z / T1)}
    R["prediction_distribution"] = {
        name: {"argmax_raw": pred_distribution(pp["raw_T1"], class_ids),
               "argmax_after_T": pred_distribution(pp["after_T"], class_ids),
               "argmax_identical": bool((pp["raw_T1"].argmax(1) == pp["after_T"].argmax(1)).all())}
        for name, pp in probs.items()}
    R["maxprob_distribution"] = {name: {"raw_T1": maxprob_summary(pp["raw_T1"]),
                                        "after_T": maxprob_summary(pp["after_T"])}
                                 for name, pp in probs.items()}
    pa = probs["places_all"]["after_T"]
    pred_pl = pa.argmax(1)
    awe_mask = pred_pl == awe
    R["places_awe"] = {"overall": float(awe_mask.mean()),
                       "by_split": {s: float(awe_mask[places["split"] == s].mean()) for s in np.unique(places["split"])},
                       "maxprob_when_awe": maxprob_summary(pa[awe_mask]),
                       "maxprob_when_not_awe": maxprob_summary(pa[~awe_mask])}
    per_scene = {}
    for sc in sorted(np.unique(places["scene"])):
        m = places["scene"] == sc
        per_scene[sc] = {"n": int(m.sum()), "awe_rate": float(awe_mask[m].mean()),
                         "top_emotions": sorted(((cid, float(v)) for cid, v in pred_distribution(pa[m], class_ids).items()
                                                 if v > 0), key=lambda t: -t[1])[:3],
                         "median_maxprob": float(np.median(pa[m].max(1)))}
    R["places_awe"]["per_scene_label"] = per_scene
    # awe on EmoSet val: how sure is the model on genuinely-awe images vs Places-awe
    yv = data["val"]["y"]
    pv = probs["emoset_val"]["after_T"]
    R["places_awe"]["emoset_val_true_awe_pred_awe_maxprob"] = maxprob_summary(pv[(yv == awe) & (pv.argmax(1) == awe)])
    R["places_awe"]["awe_logit_margin"] = {
        name: float(np.median((z[:, awe] - np.sort(z, 1)[:, -2])[z.argmax(1) == awe]))
        for name, z in (("emoset_val_pred_awe", zl["val"]), ("places_pred_awe", pl))}

    # 3. confusion / per class (val reported; test only reported) ---------------------------------
    R["val_report"] = {"confusion": v1_report["val"]["confusion"], "per_class": v1_report["val"]["per_class"],
                       "macro_f1": v1_report["val"]["macro_f1"], "accuracy": v1_report["val"]["accuracy"],
                       "source": "evaluation/vision/emotion-s1-20261125T220720Z-efd7de.json"}
    R["test_report_reported_only"] = {"confusion": v1_report["test"]["confusion"],
                                      "per_class": v1_report["test"]["per_class"],
                                      "macro_f1": v1_report["test"]["macro_f1"]}
    cm = np.array(v1_report["val"]["confusion"])
    R["val_report"]["predicted_awe_total"] = int(cm[:, awe].sum())
    R["val_report"]["awe_false_positives_from"] = {class_ids[i]: int(cm[i, awe]) for i in range(k) if i != awe}

    # 4. reliability ------------------------------------------------------------------------------
    R["val_reliability"] = {"raw_T1": reliability(yv, probs["emoset_val"]["raw_T1"]),
                            "after_T": reliability(yv, pv),
                            "ece_15": {"raw_T1": metrics.ece(yv, probs["emoset_val"]["raw_T1"]),
                                       "after_T": metrics.ece(yv, pv)},
                            "nll": {"raw_T1": metrics.nll(yv, probs["emoset_val"]["raw_T1"]),
                                    "after_T": metrics.nll(yv, pv)}}
    hi = pv.max(1) >= 0.985
    R["val_reliability"]["val_conf_ge_0.985"] = {"n": int(hi.sum()), "accuracy": float((pv.argmax(1)[hi] == yv[hi]).mean())
                                                 if hi.any() else None}

    # 6. domain shift: EmoSet scenes --------------------------------------------------------------
    def scene_table(rows_iter):
        cnt = collections.Counter()
        for emo, sc in rows_iter:
            grp = "no_scene" if not sc else ("landscape" if sc in LANDSCAPE_SCENES else "other_scene")
            cnt[(grp, emo)] += 1
        out = {}
        for grp in ("landscape", "other_scene", "no_scene"):
            tot = sum(v for (g, _), v in cnt.items() if g == grp)
            out[grp] = {"n": tot, "emotion_share": {e: round(cnt[(grp, e)] / tot, 4) for e in
                                                    sorted({e for (g, e) in cnt if g == grp}, key=lambda e: -cnt[(grp, e)])}}
        return out

    train_meta = []
    for i, yy in zip(data["train"]["ids"], data["train"]["y"]):
        m = meta.get(i.split(":")[-1])
        train_meta.append((class_ids[yy].split(".")[1], m["scene"] if m else None))
    R["emoset_scene_shift"] = {"sample_train": scene_table(train_meta),
                               "full_118k": scene_table((r["emotion"], r["scene"]) for r in meta.values()),
                               "landscape_scene_list": sorted(LANDSCAPE_SCENES),
                               "note": "EmoSet scene attribute is unaudited (Places365-style predictions); 76% missing"}
    awe_train_sc = collections.Counter(s for e, s in train_meta if e == "awe" and s)
    R["emoset_scene_shift"]["sample_train_awe_top_scenes"] = awe_train_sc.most_common(15)

    # kNN view of Places: what labels do the nearest EmoSet train images carry?
    Xtr, ytr = data["train"]["X"], data["train"]["y"]
    def knn(X):
        s = X @ Xtr.T
        idx = np.argpartition(-s, KNN_K, axis=1)[:, :KNN_K]
        sims = np.take_along_axis(s, idx, 1)
        votes = np.zeros((len(X), k))
        np.add.at(votes, (np.repeat(np.arange(len(X)), KNN_K), ytr[idx].ravel()), 1)
        return sims.mean(1), votes / KNN_K
    knn_val_sim, knn_val_votes = knn(data["val"]["X"])
    knn_pl_sim, knn_pl_votes = knn(places["X"])
    R["knn_check"] = {"k": KNN_K,
                      "val_knn_accuracy": float((knn_val_votes.argmax(1) == yv).mean()),
                      "places_knn_majority_awe": float((knn_pl_votes.argmax(1) == awe).mean()),
                      "places_mean_awe_vote": float(knn_pl_votes[:, awe].mean()),
                      "linear_vs_knn_agree_places": float((knn_pl_votes.argmax(1) == pred_pl).mean())}

    # 7. scene vs emotion on Places ---------------------------------------------------------------
    scene_head = load_old_scene_head(tax)
    calib = json.load(open(config.SCENE_CALIB_PATH))
    scene_head.temperature = calib["temperature"]
    sp = scene_head.probs(places["X"])
    spred = np.array(scene_head.output_ids)[sp.argmax(1)]
    natural = {"scene.desert", "scene.sea_coast", "scene.mountains_valleys", "scene.rivers_lakes", "scene.forest",
               "scene.farmland_rural", "scene.sky", "scene.snow_ice"}
    is_nat = np.isin(spred, list(natural))
    R["scene_emotion_correlation"] = {
        "cramers_v_pred_scene_vs_pred_emotion": cramers_v(spred, pred_pl),
        "cramers_v_true_scene_vs_pred_emotion": cramers_v(places["scene"], pred_pl),
        "awe_rate_pred_natural_scene": float(awe_mask[is_nat].mean()),
        "awe_rate_pred_other_scene": float(awe_mask[~is_nat].mean()),
        "share_pred_natural": float(is_nat.mean()),
        "awe_rate_by_pred_scene": {s: {"n": int((spred == s).sum()), "awe_rate": float(awe_mask[spred == s].mean())}
                                   for s in scene_head.output_ids if (spred == s).any()},
        "natural_scene_set": sorted(natural)}

    # candidates (val only) ------------------------------------------------------------------------
    cands = {}
    cands["a_v1"] = {"C": 3.0, "T": T1, "W": head.W, "b": head.b}
    cands["b_v1_T1"] = {"C": 3.0, "T": 1.0, "W": head.W, "b": head.b,
                        "note": "T>=1 constraint: val-NLL optimum is 0.776 < 1, so the constrained optimum is T=1"}
    grid = []
    for C in WIDE_C_GRID:
        W, b = fit_logreg(Xtr, ytr, C)
        z = data["val"]["X"] @ W.T + b
        T, _ = calibration.fit_temperature(z, yv)
        p = softmax(z / T)
        pp = softmax(pl.dtype.type(1) * (places["X"] @ W.T + b) / T)
        grid.append({"C": C, "T": T, "val_macro_f1": metrics.macro_f1(yv, z.argmax(1), k),
                     "val_nll_after_T": metrics.nll(yv, p), "val_ece_after_T": metrics.ece(yv, p),
                     "places_awe_rate": float((pp.argmax(1) == awe).mean()),
                     "places_median_maxprob": float(np.median(pp.max(1)))})
        if C in (0.01, 0.1, 0.3, 1.0):
            cands[f"c_C{C}"] = {"C": C, "T": T, "W": W, "b": b}
    best_f1 = max(grid, key=lambda r: (round(r["val_macro_f1"], 6), -r["C"]))
    best_nll = min(grid, key=lambda r: r["val_nll_after_T"])
    R["wide_c_grid"] = {"grid": grid, "best_by_val_macro_f1": best_f1["C"], "best_by_val_nll": best_nll["C"]}
    R["class_weight_balanced"] = {"skipped": True,
                                  "reason": "train is exactly balanced (600 per class); class_weight='balanced' "
                                            "gives identical weights (1.0) and therefore the same model"}

    cand_out = {}
    pred_v1 = zl["val"].argmax(1)
    for name, c in cands.items():
        zv = data["val"]["X"] @ c["W"].T + c["b"]
        p = softmax(zv / c["T"])
        pp = softmax((places["X"] @ c["W"].T + c["b"]) / c["T"])
        cand_out[name] = {"C": c["C"], "T": c["T"], "val": eval_probs(yv, p, k),
                          "val_delta_macro_f1_vs_v1": paired_delta_ci(yv, pred_v1, p.argmax(1), k),
                          "places_awe_rate": float((pp.argmax(1) == awe).mean()),
                          "places_maxprob": maxprob_summary(pp), **({"note": c["note"]} if "note" in c else {})}
    R["candidates"] = cand_out

    # (e) abstention / uncertainty rules, thresholds from EmoSet val (keep 95%) --------------------
    cent = np.stack([Xtr[ytr == i].mean(0) for i in range(k)])
    cent /= np.linalg.norm(cent, axis=1, keepdims=True)
    def scores(X, z):
        p = softmax(z / T1)
        srt = np.sort(p, 1)
        sim, _ = knn(X)
        return {"maxprob": p.max(1), "margin": srt[:, -1] - srt[:, -2], "neg_entropy": -entropy(p),
                "max_centroid_cos": (X @ cent.T).max(1), "knn10_mean_cos": sim}
    sv = scores(data["val"]["X"], zl["val"])
    spl = scores(places["X"], pl)
    photos = None
    pe = os.path.join(OUT_DIR, "photos_embeddings.npz")
    if os.path.exists(pe):
        with np.load(pe, allow_pickle=False) as d:
            photos = {"X": d["feats"], "names": [str(n) for n in d["names"]]}
        sph = scores(photos["X"], head.logits(photos["X"]))
    rules = {}
    correct_v = pred_v1 == yv
    for s in sv:
        thr = float(np.quantile(sv[s], 1 - KEEP_TARGET))  # flag if score < thr
        keep_v = sv[s] >= thr
        flag_pl = spl[s] < thr
        rule = {"threshold": thr, "flag_if": f"{s} < threshold",
                "emoset_val_flagged": float((~keep_v).mean()),
                "emoset_val_selective_accuracy_kept": float(correct_v[keep_v].mean()),
                "emoset_val_accuracy_flagged": float(correct_v[~keep_v].mean()),
                "auroc_correct_vs_wrong_val": auroc(sv[s][correct_v], sv[s][~correct_v]),
                "places_flagged_all": float(flag_pl.mean()),
                "places_flagged_among_pred_awe": float(flag_pl[awe_mask].mean()),
                "auroc_emoset_val_vs_places": auroc(sv[s], spl[s]),
                "places_val_flagged": float(flag_pl[places["split"] == "val"].mean())}
        if photos is not None:
            fp = sph[s] < thr
            rule["photos_flagged"] = float(fp.mean())
        rules[s] = rule
    # risk-coverage for maxprob at a few fixed thresholds
    rc = []
    for t in (0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        kv = sv["maxprob"] >= t
        rc.append({"maxprob_threshold": t, "val_coverage": float(kv.mean()),
                   "val_accuracy_kept": float(correct_v[kv].mean()), "places_coverage": float((spl["maxprob"] >= t).mean())})
    R["abstention"] = {"keep_target_on_val": KEEP_TARGET, "rules": rules, "maxprob_risk_coverage": rc}
    # kNN-distance threshold derived from Places val (OOD rate) as asked
    if True:
        thr_pv = float(np.quantile(spl["knn10_mean_cos"][places["split"] == "val"], 0.5))
        R["abstention"]["knn_places_val_median_threshold"] = {
            "threshold": thr_pv, "emoset_val_below": float((sv["knn10_mean_cos"] < thr_pv).mean()),
            "places_test_below": float((spl["knn10_mean_cos"][places["split"] == "test"] < thr_pv).mean())}

    # photos (the e2e landscape photos): reproduce predictions and apply rules ---------------------
    if photos is not None:
        php = head.probs(photos["X"])
        order = np.argsort(-php, 1)
        R["photos"] = {"n": len(photos["names"]), "awe_rate": float((php.argmax(1) == awe).mean()),
                       "rows": [{"image": n, "top3": [[class_ids[j], round(float(php[i, j]), 3)] for j in order[i, :3]],
                                 "maxprob": float(php[i].max()), "knn10_mean_cos": float(sph["knn10_mean_cos"][i]),
                                 "knn_awe_vote": float(knn(photos["X"][i:i + 1])[1][0, awe]),
                                 "pred_scene": scene_head.output_ids[int(scene_head.probs(photos["X"][i:i + 1])[0].argmax())]}
                                for i, n in enumerate(photos["names"])],
                       "maxprob": maxprob_summary(php)}
    R["emoset_val_score_quantiles"] = {s: [float(np.quantile(v, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
                                       for s, v in sv.items()}
    R["places_score_quantiles"] = {s: [float(np.quantile(v, q)) for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
                                   for s, v in spl.items()}

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "results.json"), "w", encoding="utf-8") as fh:
        json.dump(_round(R), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("wrote", os.path.join(OUT_DIR, "results.json"))
    return R


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("embed")
    e.add_argument("--photos", default=None)
    e.add_argument("--device", default="cpu")
    sub.add_parser("run")
    args = ap.parse_args(argv)
    if args.cmd == "embed":
        embed(args.photos, args.device)
    else:
        run()


if __name__ == "__main__":
    main()
