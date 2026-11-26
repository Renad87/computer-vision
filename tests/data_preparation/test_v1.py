"""v1 tests: near-duplicate candidates, human-confirmed groups and quarantine, the review gate, PV-Test merge."""
import argparse
import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest

from .test_build import read_bytes
from .helpers import HAVE_IMAGING, PACKAGE_ROOT, SKIP_MSG, jpeg_bytes, mini_emoset_zip, mini_places_dir, recompress


def rec(image_id, split, source="emoset118k", path=None):
    return {"image_id": image_id, "split": split, "source_dataset": source, "image_sha256": image_id.ljust(64, "0")[:64],
            "image_path": path or f"datasets/images/x/{image_id}.jpg"}


def pair(a, b, decision, by="phash+clip"):
    return {"image_id_a": a, "image_id_b": b, "decision": decision, "nominated_by": by, "phash_hamming": 3,
            "clip_cosine": 0.97, "reviewer_id": "fixture_reviewer", "date": "2026-11-25"}


@unittest.skipUnless(HAVE_IMAGING, SKIP_MSG)
class NearDuplicateSearch(unittest.TestCase):
    def test_recompressed_copy_is_a_phash_candidate(self):
        from data_preparation.common import hamming, phash64
        a = jpeg_bytes(11, size=(200, 160))
        b = recompress(a, quality=55)
        c = jpeg_bytes(12, size=(200, 160))
        self.assertNotEqual(a, b)
        self.assertLessEqual(hamming(phash64(a), phash64(b)), 6)
        self.assertGreater(hamming(phash64(a), phash64(c)), 6)

    def test_candidates_find_the_pair_and_skip_identical_files(self):
        import numpy as np
        from data_preparation.common import phash64
        from data_preparation.neardup import candidates
        a = jpeg_bytes(21, size=(200, 160))
        imgs = {"img:x:a": a, "img:x:b": recompress(a, 50), "img:x:c": jpeg_bytes(22, size=(200, 160))}
        recs = [rec(i, "train") for i in sorted(imgs)]
        ph = {i: phash64(d) for i, d in imgs.items()}
        rng = np.random.default_rng(0)
        emb = {}
        for r in recs:
            v = rng.normal(size=8)
            emb[r["image_path"]] = v / np.linalg.norm(v)
        pairs, dist = candidates(recs, ph, emb)
        self.assertEqual([(p["image_id_a"], p["image_id_b"]) for p in pairs], [("img:x:a", "img:x:b")])
        self.assertIn("phash", pairs[0]["nominated_by"])


class GroupsAndQuarantine(unittest.TestCase):
    def test_group_across_splits_keeps_most_protected(self):
        from data_preparation.neardup import groups_and_quarantine
        recs = [rec("img:e:a", "train"), rec("img:e:b", "val"), rec("img:e:c", "test"), rec("img:e:d", "train")]
        pairs = [pair("img:e:a", "img:e:b", "same_image"), pair("img:e:b", "img:e:c", "same_image"),
                 pair("img:e:a", "img:e:d", "different")]
        group_of, quarantine, esc, sizes = groups_and_quarantine(recs, pairs)
        self.assertEqual(sizes, [3])
        self.assertEqual({q["image_id"] for q in quarantine}, {"img:e:a", "img:e:b"})
        self.assertTrue(all(q["kept_split"] == "test" and q["reason"] == "near_duplicate_across_splits"
                            and q["evidence"]["human_confirmed"] for q in quarantine))
        self.assertNotIn("img:e:d", group_of)
        self.assertEqual(esc, [])

    def test_group_inside_one_split_stays_with_a_group_id(self):
        from data_preparation.neardup import groups_and_quarantine
        recs = [rec("img:e:a", "train"), rec("img:e:b", "train")]
        group_of, quarantine, _, _ = groups_and_quarantine(recs, [pair("img:e:a", "img:e:b", "same_image")])
        self.assertEqual(quarantine, [])
        self.assertEqual(group_of, {"img:e:a": "g:000001", "img:e:b": "g:000001"})

    def test_two_evaluation_sets_are_escalated(self):
        from data_preparation.neardup import groups_and_quarantine
        recs = [rec("img:e:a", "test"), rec("img:p:b", "ood_test", source="places365_sample")]
        _, quarantine, esc, _ = groups_and_quarantine(recs, [pair("img:e:a", "img:p:b", "same_image")])
        self.assertEqual(len(esc), 1)
        self.assertEqual(quarantine, [])


@unittest.skipUnless(HAVE_IMAGING, SKIP_MSG)
class BuildV1(unittest.TestCase):
    def test_review_gate_then_valid_manifest(self):
        import numpy as np
        from data_preparation.build_v1 import ReviewPending, build_v1
        from data_preparation.common import read_csv, write_csv
        from data_preparation.neardup import CANDIDATE_FIELDS
        with tempfile.TemporaryDirectory() as w:
            places = mini_places_dir(os.path.join(w, "places"),
                                     [("desert-sand", "fixture_p1", "desert", "desert/sand", "train"),
                                      ("bar", "fixture_p2", "__other__", "bar", "val"),
                                      ("airport_terminal", "fixture_p3", "__ood__", "airport_terminal", "test")])
            base = jpeg_bytes(77, size=(160, 120))
            z = mini_emoset_zip(os.path.join(w, "fixture_emoset.zip"), per_split={"train": 1, "val": 1, "test": 1},
                                extra=[("emoset/train/awe/fixture_near_a.jpg", base),
                                       ("emoset/test/awe/fixture_near_b.jpg", recompress(base, 50))])
            # synthetic embeddings (orthogonal, so only pHash nominates the re-compressed pair)
            from data_preparation.sources import iter_emoset, iter_places
            paths = [r["image_path"] for r, _, _ in iter_places(places)] + [r["image_path"] for r, _, _ in iter_emoset(z)]
            feats = np.eye(len(paths), 64 if len(paths) <= 64 else len(paths), dtype=np.float32)
            os.makedirs(os.path.join(w, "datasets", "cache"))
            np.savez(os.path.join(w, "datasets", "cache", "clip_embeddings.npz"), feats=feats, paths=np.array(paths))
            args = argparse.Namespace(places_dir=places, emoset_zip=z, clip_features=None, near_dup_decisions=None)
            with self.assertRaises(ReviewPending):
                build_v1(args, w)
            dec = os.path.join(w, "datasets", "review", "near_duplicate_decisions.csv")
            rows = read_csv(dec)
            self.assertEqual([(r["image_id_a"], r["image_id_b"]) for r in rows],
                             [("img:emoset118k:fixture_near_a", "img:emoset118k:fixture_near_b")])
            for r in rows:
                r.update(decision="same_image", reviewer_id="fixture_reviewer", date="2026-11-25")
            write_csv(dec, rows, CANDIDATE_FIELDS)
            recs, issues, build, state = build_v1(args, w)
            self.assertEqual(issues, [])
            ids = {r["image_id"] for r in recs}
            self.assertNotIn("img:emoset118k:fixture_near_a", ids)          # train copy quarantined
            self.assertIn("img:emoset118k:fixture_near_b", ids)             # test copy kept
            ood = [r for r in recs if r["source_image_id"] == "fixture_p3"][0]
            self.assertEqual((ood["split"], ood["scene_label_status"]), ("ood_test", "excluded_ood"))
            proc = subprocess.run([sys.executable, "-m", "contracts.validate", "image_manifest",
                                   os.path.join(w, build["manifest"])], cwd=PACKAGE_ROOT, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout)
            first = read_bytes(os.path.join(w, build["manifest"]))
            build_v1(args, w)
            self.assertEqual(first, read_bytes(os.path.join(w, build["manifest"])))


@unittest.skipUnless(HAVE_IMAGING, SKIP_MSG)
class PVTestMerge(unittest.TestCase):
    def test_merge_union_agreement_and_freeze(self):
        from data_preparation import pv_test
        from data_preparation.common import write_csv
        with tempfile.TemporaryDirectory() as w:
            img_dir = os.path.join(w, "datasets", "images", "pv_test")
            os.makedirs(img_dir)
            for i in (1, 2):
                with open(os.path.join(img_dir, f"pv_{i:04d}.jpg"), "wb") as fh:
                    fh.write(jpeg_bytes(300 + i, size=(128, 96)))
            ev = os.path.join(w, "evaluation", "pv_test")
            f = pv_test.SHEET_FIELDS
            write_csv(os.path.join(ev, "annotation_sheet_A.csv"), [
                {"pv_id": "pv_0001", "scene": "scene.desert", "acceptable_img_emotions": "img_emotion.awe",
                 "acceptable_lit_emotions": "lit_emotion.awe", "annotator_id": "fixture_ann_A", "date": "2026-11-26"},
                {"pv_id": "pv_0002", "scene": "scene.sky", "acceptable_img_emotions": "img_emotion.contentment",
                 "acceptable_lit_emotions": "lit_emotion.serenity", "annotator_id": "fixture_ann_A",
                 "date": "2026-11-26"}], f)
            write_csv(os.path.join(ev, "annotation_sheet_B.csv"), [
                {"pv_id": "pv_0001", "scene": "scene.desert", "acceptable_img_emotions": "img_emotion.contentment",
                 "acceptable_lit_emotions": "lit_emotion.longing", "annotator_id": "fixture_ann_B", "date": "2026-11-26"},
                {"pv_id": "pv_0002", "scene": "scene.sea_coast", "acceptable_img_emotions": "img_emotion.awe",
                 "acceptable_lit_emotions": "lit_emotion.awe", "annotator_id": "fixture_ann_B", "date": "2026-11-26"}], f)
            with self.assertRaises(SystemExit):           # pv_0002 disagrees -> needs adjudication
                pv_test.merge(w, "2026-11-26")
            write_csv(os.path.join(ev, "adjudication.csv"),
                      [{"pv_id": "pv_0002", "scene": "scene.sky", "adjudicator_id": "fixture_omar",
                        "date": "2026-11-26"}], ["pv_id", "scene", "adjudicator_id", "date"])
            pv_test.merge(w, "2026-11-26")
            path = os.path.join(w, "datasets", "manifests", "pv_test_v1.jsonl")
            with open(path, encoding="utf-8") as fh:
                recs = [json.loads(x) for x in fh]
            self.assertEqual(recs[0]["acceptable_img_emotions"], ["img_emotion.awe", "img_emotion.contentment"])
            self.assertEqual((recs[0]["review_status"], recs[0]["scene_ambiguous"]), ("human_double", False))
            self.assertEqual((recs[1]["review_status"], recs[1]["scene_ambiguous"]), ("adjudicated", True))
            self.assertTrue(os.path.exists(path.replace(".jsonl", ".sha256")))
            with self.assertRaises(SystemExit):           # frozen: never overwritten
                pv_test.merge(w, "2026-11-26")


if __name__ == "__main__":
    unittest.main()
