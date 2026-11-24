"""Offline tests: no GPU, no internet, no torch.

They check the code paths (training heads, calibration, evaluation report,
suggestion policy, inference contract) on SYNTHETIC features. The numbers they
produce say nothing about real model quality and must never be reported as
results.

Run:  python -m pytest ml/emotion/tests -q     (or: python ml/emotion/tests/test_offline.py)
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(HERE)
sys.path.insert(0, MOD)

import config  # noqa: E402
from attributes import compute_attributes, numeric_attributes  # noqa: E402
from head import Head, fit_temperature, softmax  # noqa: E402
from policy import suggest_indices, uncertainty  # noqa: E402

K = len(config.TRAINED_CLASSES)


# ----------------------------------------------------------------- helpers
def _img_bytes(rgb, size=(64, 48)):
    buf = io.BytesIO()
    Image.new("RGB", size, rgb).save(buf, format="JPEG")
    return buf.getvalue()


def _synthetic_split(n_per_class, rng, means, dim, with_resnet=True, cache_dir=None, split="x"):
    X, y = [], []
    for k in range(K):
        X.append(means[k] + 0.6 * rng.standard_normal((n_per_class, dim)) / np.sqrt(dim) * 4)
        y += [k] * n_per_class
    X = np.concatenate(X).astype(np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    y = np.array(y)
    n = len(y)
    paths = []
    if cache_dir:
        os.makedirs(os.path.join(cache_dir, split), exist_ok=True)
        for i in range(n):
            rel = f"{split}/{i:06d}.jpg"
            Image.new("RGB", (32, 32), tuple(int(v) for v in rng.integers(0, 255, 3))).save(os.path.join(cache_dir, rel))
            paths.append(rel)
    d = {
        "clip": X, "labels": y,
        "attributes": (rng.random((n, 5)) + y[:, None] * 0.02).astype(np.float32),
        "paths": np.array(paths or [f"{split}/{i:06d}.jpg" for i in range(n)]),
        "ds_brightness": rng.random(n).astype(np.float32),
        "ds_colorfulness": rng.random(n).astype(np.float32),
        "image_id": np.array([str(i) for i in range(n)]),
        "scene": np.array([""] * n), "facial_expression": np.array([""] * n),
    }
    if with_resnet:
        d["resnet"] = np.concatenate([X, X ** 2], axis=1).astype(np.float32)
    return d


def _make_feature_dir(root):
    rng = np.random.default_rng(0)
    dim = 32
    means = rng.standard_normal((K, dim))
    fdir, cdir = os.path.join(root, "features"), os.path.join(root, "cache")
    os.makedirs(fdir)
    for split, n in [("train", 40), ("val", 15), ("test", 15)]:
        np.savez(os.path.join(fdir, f"{split}.npz"),
                 **_synthetic_split(n, rng, means, dim, cache_dir=cdir, split=split))
    ct = means / np.linalg.norm(means, axis=1, keepdims=True)
    dt = rng.standard_normal((3, dim)); dt /= np.linalg.norm(dt, axis=1, keepdims=True)
    np.savez(os.path.join(fdir, config.TEXT_EMB_FILENAME), class_text=ct.astype(np.float32),
             derived_text=dt.astype(np.float32), class_names=np.array(config.TRAINED_CLASSES),
             derived_names=np.array(config.DERIVED_CLASSES), model_name=np.array("synthetic/clip"),
             logit_scale=np.array(100.0, dtype=np.float32))
    return fdir, cdir, means


# ----------------------------------------------------------------- unit tests
def test_attributes_dark_vs_bright_and_warm_vs_cool():
    dark = numeric_attributes(np.full((10, 10, 3), 20, np.float32))
    bright = numeric_attributes(np.full((10, 10, 3), 230, np.float32))
    assert dark["brightness"] < 0.2 < 0.8 < bright["brightness"]
    warm = compute_attributes(_img_bytes((220, 120, 40)))
    cool = compute_attributes(_img_bytes((40, 120, 220)))
    assert warm["warmth"] > 0 > cool["warmth"]
    assert warm["descriptors_ar"]["tone"] == "دافئة" and cool["descriptors_ar"]["tone"] == "باردة"


def test_head_matches_sklearn_linear_and_mlp():
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler
    rng = np.random.default_rng(1)
    X = rng.standard_normal((200, 10)); y = rng.integers(0, K, 200)
    sc = StandardScaler().fit(X)
    for model in (LogisticRegression(max_iter=500), MLPClassifier((16,), max_iter=50, random_state=0)):
        model.fit(sc.transform(X), y)
        h = Head.from_sklearn(model, sc)
        assert np.allclose(h.proba(X, calibrated=False), model.predict_proba(sc.transform(X)), atol=1e-4)
    # folded linear head gives the same logits
    lr = LogisticRegression(max_iter=500).fit(sc.transform(X), y)
    h = Head.from_sklearn(lr, sc)
    w, b = h.folded_linear()
    assert np.allclose(X @ w + b, h.logits(X), atol=1e-3)


def test_head_save_load_roundtrip(tmp_path=None):
    tmp = tmp_path or tempfile.mkdtemp()
    h = Head("linear", [np.eye(3, K)], [np.zeros(K)], np.zeros(3), np.ones(3), 1.7, {"a": "ب"})
    p = os.path.join(str(tmp), "h.npz")
    h.save(p, extra_arrays={"model_name": np.array("m")})
    h2, extras = Head.load(p)
    assert h2.temperature == 1.7 and h2.meta == {"a": "ب"} and str(extras["model_name"]) == "m"


def test_temperature_reduces_overconfidence():
    rng = np.random.default_rng(2)
    y = rng.integers(0, K, 500)
    logits = rng.standard_normal((500, K)) * 8  # very overconfident, mostly wrong
    logits[np.arange(500), y] += 2
    assert fit_temperature(logits, y) > 1.0


def test_policy_suggestions_and_uncertainty():
    clear = np.array([0.9, 0.05] + [0.05 / 6] * 6)
    amb = np.array([0.4, 0.38, 0.1] + [0.12 / 5] * 5)
    assert suggest_indices(clear) == [0]
    assert suggest_indices(amb)[:2] == [0, 1]
    assert uncertainty(clear)["is_ambiguous"] is False
    assert uncertainty(amb)["is_ambiguous"] is True


# ----------------------------------------------------------------- end-to-end
def test_end_to_end_train_evaluate_infer():
    root = tempfile.mkdtemp()
    fdir, cdir, means = _make_feature_dir(root)
    adir, rdir = os.path.join(root, "artifacts"), os.path.join(root, "results")
    env = {**os.environ, "MPLBACKEND": "Agg"}
    for script, extra in [("train.py", []), ("evaluate.py", ["--skip_finetuned", "--n_boot", "50"])]:
        cmd = [sys.executable, os.path.join(MOD, script), "--features_dir", fdir, "--artifacts_dir", adir,
               "--results_dir", rdir] + (["--cache_dir", cdir] if script == "evaluate.py" else []) + extra
        p = subprocess.run(cmd, capture_output=True, text=True, env=env)
        assert p.returncode == 0, p.stdout + p.stderr

    report = json.load(open(os.path.join(adir, config.TRAIN_REPORT_FILENAME)))
    assert report["deployed_head"]["candidate"] in ("clip_linear", "clip_mlp")
    metrics = json.load(open(os.path.join(rdir, "metrics.json")))
    for name in ("zero_shot_clip", "attributes_only", "clip_linear", "clip_mlp", "resnet_linear"):
        assert name in metrics["summary"], name
    for fig in ("model_comparison.png", "per_class_f1.png", "reliability_deployed.png", "ambiguity_margin.png",
                "ambiguous_examples.png", "attributes_by_emotion.png", "val_model_selection.png"):
        assert os.path.exists(os.path.join(rdir, fig)), fig
    assert os.path.exists(os.path.join(rdir, "RESULTS.md"))

    # inference contract, using an injected embedding (no CLIP download needed)
    from inference import EmotionAnalyzer
    an = EmotionAnalyzer(artifacts_dir=adir)
    emb = means[2] / np.linalg.norm(means[2])
    out = an.analyze(_img_bytes((200, 150, 90)), clip_embedding=emb, embedding_model_name="synthetic/clip")
    for key in ("emotion_suggestions", "visual_affective_attributes", "uncertainty", "model_version"):
        assert key in out, key
    assert out["emotion_suggestions"][0]["source"] == "trained"
    assert abs(sum(out["all_trained_scores"].values()) - 1) < 1e-3
    assert all(s["source"] in ("trained", "zero_shot_unvalidated") for s in out["emotion_suggestions"])

    # wrong embedding model must be refused
    try:
        an.analyze(_img_bytes((1, 2, 3)), clip_embedding=emb, embedding_model_name="other/model")
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("PASS", name)
