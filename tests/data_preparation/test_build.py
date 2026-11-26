"""Data-preparation tests on tiny synthetic inputs (temp dirs only; never under datasets/)."""
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, validate_records

from .helpers import HAVE_IMAGING, PACKAGE_ROOT, SKIP_MSG, jpeg_bytes, mini_emoset_zip, mini_places_dir

TAX = load_taxonomy()
FIXTURES = os.path.join(PACKAGE_ROOT, "fixtures", "dataset", "valid")


def fixture_records(prefix):
    name = next(n for n in sorted(os.listdir(FIXTURES)) if n.startswith(prefix))
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
        return [json.loads(x) for x in fh if x.strip()]


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def validate(records):
    return validate_records("image_manifest", list(enumerate(records, 1)), Context(taxonomy=TAX, mode="production"))


def rec(image_id, split, sha, scene=None, emotion="img_emotion.awe", source="emoset118k"):
    """A minimal record for duplicate-rule tests."""
    return {"image_id": image_id, "source_dataset": source, "split": split, "image_sha256": sha,
            "scene_label": scene, "scene_label_status": "labeled" if scene else "unavailable",
            "emotion_label": emotion, "emotion_label_status": "labeled" if emotion else "unavailable"}


@unittest.skipUnless(HAVE_IMAGING, SKIP_MSG)
class EmoSetV09(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.zip = mini_emoset_zip(os.path.join(self.root, "fixture_emoset.zip"))

    def tearDown(self):
        self.tmp.cleanup()

    def build(self):
        from data_preparation.build import build_v09
        return build_v09(self.zip, self.root)

    def test_v09_fields_and_values_match_fixture_V02(self):
        recs, issues, build, _ = self.build()
        self.assertEqual(issues, [])
        self.assertEqual(len(recs), 8 * 4)
        shape = fixture_records("V02_")[0]
        for r in recs:
            self.assertEqual(set(r), set(shape) - {"fixture"})
            for k in ("schema_version", "taxonomy_version", "source_dataset", "split_origin", "near_dup_group",
                      "scene_label", "scene_label_status", "scene_label_source", "emotion_label_status",
                      "emotion_label_source", "review_status"):
                self.assertEqual(r[k], shape[k], k)
            self.assertNotIn("scene_source_raw", r)
            self.assertEqual(r["image_id"], "img:emoset118k:" + r["source_image_id"])
            emo = r["emotion_label"].split(".", 1)[1]
            self.assertEqual(r["image_path"], f"datasets/images/emoset/{r['split']}/{emo}/{r['source_image_id']}.jpg")
            self.assertEqual(r["annotation_provenance"]["annotators"], [])
            self.assertIsNone(r["annotation_provenance"]["date"])

    def test_rebuild_is_byte_identical_and_validator_exits_0(self):
        _, _, b1, _ = self.build()
        path = os.path.join(self.root, b1["manifest"])
        first = read_bytes(path)
        first_build = read_bytes(path.replace(".jsonl", ".build.json"))
        _, _, b2, _ = self.build()
        self.assertEqual(first, read_bytes(path))
        self.assertEqual(first_build, read_bytes(path.replace(".jsonl", ".build.json")))
        proc = subprocess.run([sys.executable, "-m", "contracts.validate", "image_manifest", path],
                              cwd=PACKAGE_ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_exact_duplicate_in_same_split_is_quarantined(self):
        data = jpeg_bytes(424242)
        self.zip = mini_emoset_zip(os.path.join(self.root, "fixture_dup.zip"),
                                   extra=[("emoset/train/awe/fixture_dupa.jpg", data),
                                          ("emoset/train/awe/fixture_dupb.jpg", data)])
        recs, issues, build, state = self.build()
        self.assertEqual(issues, [])
        ids = {r["image_id"] for r in recs}
        self.assertIn("img:emoset118k:fixture_dupa", ids)
        self.assertNotIn("img:emoset118k:fixture_dupb", ids)
        self.assertEqual([q["reason"] for q in state["quarantine"]], ["exact_duplicate_same_split"])

    def test_small_image_is_excluded_not_upscaled(self):
        from .helpers import jpeg_bytes as jb
        self.zip = mini_emoset_zip(os.path.join(self.root, "fixture_small.zip"),
                                   extra=[("emoset/val/fear/fixture_tiny.jpg", jb(7, size=(40, 90)))])
        recs, issues, build, state = self.build()
        self.assertEqual(issues, [])
        self.assertNotIn("img:emoset118k:fixture_tiny", {r["image_id"] for r in recs})
        self.assertEqual(state["excluded"][0]["reason"], "smaller_than_64px")

    def test_reader_class_indices_follow_taxonomy_class_order(self):
        from data_preparation.reader import read_rows
        _, _, b, _ = self.build()
        order = TAX.class_order["img_emotion"]
        with open(os.path.join(self.root, b["manifest"]), encoding="utf-8") as fh:
            labels = {json.loads(x)["image_path"]: json.loads(x)["emotion_label"] for x in fh}
        for path, s, e, split in read_rows(os.path.join(self.root, b["manifest"])):
            self.assertIsNone(s)
            self.assertEqual(order[e], labels[path])


@unittest.skipUnless(HAVE_IMAGING, SKIP_MSG)
class PlacesConversion(unittest.TestCase):
    def test_labels_ood_rule_and_windows_paths(self):
        from data_preparation.sources import iter_places
        with tempfile.TemporaryDirectory() as root:
            mini_places_dir(root, [("desert-sand", "fixture_p1", "desert", "desert/sand", "train"),
                                   ("bar", "fixture_p2", "__other__", "bar", "val"),
                                   ("airport_terminal", "fixture_p3", "__ood__", "airport_terminal", "test")])
            recs = {r["source_image_id"]: r for r, _, _ in iter_places(root, TAX)}
        self.assertEqual(recs["fixture_p1"]["image_path"], "datasets/images/places365/desert-sand/fixture_p1.jpg")
        self.assertEqual((recs["fixture_p1"]["scene_label"], recs["fixture_p1"]["scene_source_raw"]),
                         ("scene.desert", "desert/sand"))
        self.assertEqual(recs["fixture_p2"]["scene_label"], "scene.other")
        ood = recs["fixture_p3"]
        self.assertEqual((ood["split"], ood["scene_label"], ood["scene_label_status"], ood["scene_label_source"]),
                         ("ood_test", None, "excluded_ood", None))
        for r in recs.values():
            self.assertEqual(r["emotion_label_status"], "unavailable")
            self.assertNotIn("\\", r["image_path"])

    def test_conversion_equals_map_places365_for_every_listed_category(self):
        from data_preparation.sources import iter_places
        with open(os.path.join(PACKAGE_ROOT, "references", "derived", "places365_category_mapping.csv"),
                  encoding="utf-8") as fh:
            table = list(csv.DictReader(fh))
        rows = [(t["folder_name"], f"fixture_cat_{i:03d}", t["old_label"], t["places365_category"], "train")
                for i, t in enumerate(table)]
        with tempfile.TemporaryDirectory() as root:
            mini_places_dir(root, rows)
            recs = [r for r, _, _ in iter_places(root, TAX)]
        self.assertEqual(len(recs), len(table))
        for r, t in zip(recs, table):
            self.assertEqual((r["scene_label"], r["scene_label_status"]), TAX.map_places365(t["places365_category"]))
            self.assertEqual(r["scene_label"] or "", t["scene_label"])


class DuplicateRules(unittest.TestCase):
    def test_across_splits_keeps_most_protected_copy(self):
        from data_preparation.cleaning import exact_duplicates
        recs = [rec("img:emoset118k:a", "train", "1" * 64), rec("img:emoset118k:b", "test", "1" * 64),
                rec("img:emoset118k:c", "val", "1" * 64)]
        kept, quarantine, esc, _ = exact_duplicates(recs)
        self.assertEqual([r["image_id"] for r in kept], ["img:emoset118k:b"])
        self.assertEqual({q["image_id"] for q in quarantine}, {"img:emoset118k:a", "img:emoset118k:c"})
        self.assertTrue(all(q["reason"] == "exact_duplicate_across_splits" and q["kept_split"] == "test"
                            for q in quarantine))
        self.assertEqual(esc, [])

    def test_same_split_label_conflict_quarantines_all(self):
        from data_preparation.cleaning import exact_duplicates
        recs = [rec("img:emoset118k:a", "train", "2" * 64, emotion="img_emotion.awe"),
                rec("img:emoset118k:b", "train", "2" * 64, emotion="img_emotion.fear")]
        kept, quarantine, _, _ = exact_duplicates(recs)
        self.assertEqual(kept, [])
        self.assertEqual({q["reason"] for q in quarantine}, {"exact_duplicate_label_conflict"})

    def test_two_evaluation_splits_of_different_sources_are_escalated(self):
        from data_preparation.cleaning import exact_duplicates
        recs = [rec("img:emoset118k:a", "test", "3" * 64),
                rec("img:places365_sample:b", "ood_test", "3" * 64, scene=None, emotion=None,
                    source="places365_sample")]
        kept, quarantine, esc, _ = exact_duplicates(recs)
        self.assertEqual(len(esc), 1)
        self.assertEqual(quarantine, [])

    def test_train_row_without_label_is_rejected_by_the_validator(self):
        r = fixture_records("V01_")[0]
        r = {k: v for k, v in r.items() if k != "fixture"}
        r.update(scene_label=None, scene_label_status="unavailable", scene_label_source=None, split="train")
        r.pop("scene_source_raw", None)
        self.assertIn("E_STATUS_CONFLICT", {i.code for i in validate([r])})


WORKDIR = os.path.abspath(os.environ.get("SHADEN_M2_WORKDIR", PACKAGE_ROOT))


class RealManifests(unittest.TestCase):
    """Checks on the real manifests in the work folder (env SHADEN_M2_WORKDIR, default the package root);
    skipped when they have not been built on this machine."""

    def test_built_manifests_pass_the_validator(self):
        mdir = os.path.join(WORKDIR, "datasets", "manifests")
        names = [n for n in os.listdir(mdir) if n.endswith(".jsonl")] if os.path.isdir(mdir) else []
        if not names:
            self.skipTest("no real manifest built")
        for n in names:
            proc = subprocess.run([sys.executable, "-m", "contracts.validate", "image_manifest",
                                   os.path.join(mdir, n)], cwd=PACKAGE_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{n}: {proc.stdout[:500]}")

    def test_v09_counts(self):
        path = os.path.join(WORKDIR, "datasets", "manifests", "manifest_v0.9_emotion.jsonl")
        if not os.path.exists(path):
            self.skipTest("manifest_v0.9_emotion.jsonl not built")
        from collections import Counter
        with open(path, encoding="utf-8") as fh:
            recs = [json.loads(x) for x in fh]
        c = Counter((r["split"], r["emotion_label"]) for r in recs)
        expected = {"train": 600, "val": 150, "test": 400}
        for (split, emo), n in c.items():
            self.assertEqual(n, expected[split], (split, emo))
        self.assertEqual(len(recs), 9200)


if __name__ == "__main__":
    unittest.main()
