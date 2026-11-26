"""Tests for vision_model/. Need the project .venv (numpy, scipy, scikit-learn, torch, open_clip);
under the stdlib-only interpreter they are skipped. Tests that need the previous project's head files,
the CLIP weights or the EmoSet archive skip when those are absent.

    .venv/bin/python -B -m unittest discover -s tests -t .
"""
import importlib.util
import json
import os
import tempfile
import unittest

HAVE_STACK = all(importlib.util.find_spec(m) for m in ("numpy", "scipy", "sklearn", "torch", "open_clip"))

if HAVE_STACK:
    import numpy as np

    from contracts.taxonomy import load_taxonomy
    from contracts.validate import Context, validate_document
    from vision_model import calibration, config, metrics
    from vision_model.heads import LinearHead, softmax

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HAVE_OLD_HEADS = HAVE_STACK and os.path.isfile(os.path.join(config.OLD_WEIGHTS, "scene_head_clip.npz"))
SYNTHETIC_MANIFEST = os.path.join(REPO, "fixtures", "dataset", "valid", "V02_emotion_only_emoset_v09_shape.jsonl")


def synthetic_clusters(n_per_class, k=8, seed=0, spread=0.6):
    """Well-separated Gaussian clusters on the unit sphere: test data for the pipeline code only."""
    rng = np.random.default_rng(seed)
    centres = rng.standard_normal((k, 512))
    X = np.concatenate([centres[c] + spread * rng.standard_normal((n_per_class, 512)) for c in range(k)])
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    return X.astype(np.float32), np.repeat(np.arange(k), n_per_class)


def synthetic_emotion_head(taxonomy, seed=1):
    rng = np.random.default_rng(seed)
    return LinearHead("emotion", "img_emotion", taxonomy.class_order["img_emotion"],
                      rng.standard_normal((8, 512)) * 5, np.zeros(8), "softmax", "trained_poetry_vision_v1",
                      trained_on="0" * 64, temperature=1.3)


@unittest.skipUnless(HAVE_STACK, "needs the project .venv")
class Metrics(unittest.TestCase):
    def test_perfect_and_known_values(self):
        y = np.array([0, 1, 2, 2])
        p = np.eye(3)[[0, 1, 2, 1]] * 0.9 + 0.1 / 3
        self.assertAlmostEqual(0.75, metrics.accuracy(y, p.argmax(1)))
        _, _, f1 = metrics.per_class_f1(y, p.argmax(1), 3)
        self.assertTrue(np.allclose([1.0, 2 / 3, 2 / 3], f1))
        self.assertAlmostEqual(f1.mean(), metrics.macro_f1(y, p.argmax(1), 3))

    def test_ece_zero_when_confidence_equals_accuracy(self):
        y = np.array([0, 0, 0, 1])
        p = np.tile([0.75, 0.25], (4, 1))
        self.assertAlmostEqual(0.0, metrics.ece(y, p), places=9)

    def test_bootstrap_interval_contains_point(self):
        rng = np.random.default_rng(0)
        y, pred = rng.integers(0, 4, 400), rng.integers(0, 4, 400)
        lo, hi = metrics.bootstrap_ci(y, pred, metrics.accuracy, n_boot=200)
        self.assertLessEqual(lo, metrics.accuracy(y, pred))
        self.assertGreaterEqual(hi, metrics.accuracy(y, pred))


@unittest.skipUnless(HAVE_STACK, "needs the project .venv")
class Calibration(unittest.TestCase):
    def test_recovers_known_temperature(self):
        rng = np.random.default_rng(0)
        true_logits = rng.standard_normal((5000, 8)) * 2
        y = np.array([rng.choice(8, p=p) for p in softmax(true_logits)])
        t, fit = calibration.fit_temperature(true_logits * 2.5, y)  # over-confident by a factor 2.5
        self.assertAlmostEqual(2.5, t, delta=0.15)
        self.assertLess(fit["val_nll_after"], fit["val_nll_before"])
        self.assertFalse(fit["at_search_bound"])

    def test_accuracy_invariant(self):
        rng = np.random.default_rng(1)
        logits, y = rng.standard_normal((300, 8)), rng.integers(0, 8, 300)
        table = calibration.calibration_table(y, logits, 3.0)
        self.assertEqual(table["before"]["accuracy"], table["after"]["accuracy"])


@unittest.skipUnless(HAVE_STACK, "needs the project .venv")
class TrainingPipeline(unittest.TestCase):
    def test_pipeline_on_synthetic_clusters(self):
        from vision_model.train_emotion import train

        tax = load_taxonomy()
        ids = tax.class_order["img_emotion"]
        data = {}
        for seed, (split, n) in enumerate((("train", 40), ("val", 15), ("test", 15))):
            X, y = synthetic_clusters(n, seed=0) if split == "train" else synthetic_clusters(n, seed=0)
            rng = np.random.default_rng(seed + 10)
            X = X + 0.01 * rng.standard_normal(X.shape).astype(np.float32)
            data[split] = {"X": X / np.linalg.norm(X, axis=1, keepdims=True), "y": y, "ids": []}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "head.npz")
            head, report = train(data, ids, manifest_sha="f" * 64, run_id="unit-test", out_path=path)
            reloaded = LinearHead.load(path)
        self.assertEqual(ids, reloaded.output_ids)
        self.assertTrue(np.allclose(head.W, reloaded.W))
        self.assertGreater(head.temperature, 0)
        self.assertGreater(report["test"]["macro_f1"], 0.9)
        self.assertIn(report["selected_C"], [g["C"] for g in report["c_grid"]])
        self.assertEqual({"train": 320, "val": 120, "test": 120}, report["sizes"])

    def test_refuses_fixture_manifest(self):
        from vision_model.train_emotion import ManifestError, load_validated_manifest

        with self.assertRaises(ManifestError):
            load_validated_manifest(SYNTHETIC_MANIFEST, load_taxonomy())

    def test_refuses_sha_mismatch(self):
        from vision_model.train_emotion import ManifestError, assemble

        cache = {"image_ids": np.array(["img:emoset118k:a"]), "sha256": np.array(["1" * 64]),
                 "feats": np.zeros((1, 512), np.float32)}
        rows = [{"image_id": "img:emoset118k:a", "image_sha256": "2" * 64, "split": "train",
                 "emotion_label": "img_emotion.awe"}]
        with self.assertRaises(ManifestError):
            assemble(rows, cache, load_taxonomy().class_order["img_emotion"])


@unittest.skipUnless(HAVE_STACK and HAVE_OLD_HEADS, "needs the .venv and the previous project's head files")
class ReusedHeads(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from vision_model.heads import load_old_calibration, load_old_scene_head, load_old_tag_head

        cls.tax = load_taxonomy()
        cls.scene, cls.tags = load_old_scene_head(cls.tax), load_old_tag_head(cls.tax)
        cls.calib = load_old_calibration()

    def test_orders_match_taxonomy(self):
        self.assertEqual(self.tax.class_order["scene"], self.scene.output_ids)
        self.assertEqual(self.tax.class_order["tag"], self.tags.output_ids)
        self.assertEqual(list(self.tax.exposed_tags), self.tags.exposed_ids)
        self.assertTrue(all(t in self.calib["tags"] for t in self.tax.class_order["tag"]))

    def test_reordering_preserves_old_outputs(self):
        z = synthetic_clusters(4, k=2)[0]
        with np.load(config.OLD_SCENE_HEAD, allow_pickle=False) as d:
            classes = [str(c) for c in d["classes"]]
            old = softmax(z @ d["W"].T + d["b"])
        perm = [classes.index("__other__" if i == "scene.other" else i.split(".", 1)[1]) for i in self.scene.output_ids]
        self.assertTrue(np.allclose(old[:, perm], self.scene.probs(z), atol=1e-7))

    def test_inference_output_validates(self):
        from vision_model.model import PoetryVisionNet

        net = PoetryVisionNet(self.tax, synthetic_emotion_head(self.tax), encoder=object())
        ctx = Context(taxonomy=self.tax, mode="production")
        for z in synthetic_clusters(3, k=3)[0]:
            doc = net._document("a" * 64, "ok", parts=net.outputs_from_embedding(z),
                                timings={"preprocess": 1.0, "forward": 2.0, "total": 3.0})
            self.assertEqual([], [str(i) for i in validate_document("inference_output", doc, ctx)])
        error = net.analyze(b"not an image")
        self.assertEqual("invalid_image", error["error"]["code"])
        self.assertEqual([], [str(i) for i in validate_document("inference_output", error, ctx)])

    def test_model_card_validates(self):
        from vision_model.model_card import build

        card = build(self.tax)
        self.assertEqual([], [str(i) for i in validate_document("model_card", card, Context(self.tax))])
        self.assertEqual("draft", card["status"])
        self.assertEqual([], card["metrics"])


EMOSET_CACHE = os.path.join(REPO, "artifacts", "features", "emoset_clip_vitb32.npz")
WEIGHTS = os.path.join(REPO, "external", "poetry_vision_old", "product", "models", "hf")


@unittest.skipUnless(HAVE_STACK and os.path.exists(EMOSET_CACHE) and os.path.isdir(WEIGHTS)
                     and os.path.exists(os.path.join(REPO, "external", "renad", "emoset.zip")),
                     "needs CLIP weights, the EmoSet archive and the embedding cache")
class EncoderAndCache(unittest.TestCase):
    def test_cache_shape_and_fresh_encoding(self):
        import zipfile

        from vision_model.backbone import ClipEncoder, decode_image
        from vision_model.features import load_cache

        cache = load_cache(EMOSET_CACHE)
        self.assertEqual((9200, 512), cache["feats"].shape)
        self.assertTrue(np.allclose(np.linalg.norm(cache["feats"], axis=1), 1.0, atol=1e-4))
        self.assertEqual(9200, len(set(cache["image_ids"].tolist())))
        with zipfile.ZipFile(os.path.join(REPO, "external", "renad", "emoset.zip")) as z:
            imgs = [decode_image(z.read(str(p))) for p in cache["zip_path"][:4]]
        fresh = ClipEncoder("cpu").encode_images(imgs)
        self.assertGreater(float((fresh * cache["feats"][:4]).sum(1).min()), 0.9999)


if __name__ == "__main__":
    unittest.main()
