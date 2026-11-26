"""P1+ review packages: verbatim text, empty reviewer cells, priority subsets, and Renad's P0 package untouched."""
import glob
import hashlib
import json
import os
import unittest
import zipfile

from contracts.taxonomy import load_taxonomy
from poetry_corpus.tools import build_review_package as R
from poetry_corpus.tools import coverage as C
from poetry_corpus.tools.build_batch import records_path
from poetry_corpus.tools.review_sheet import REVIEWER_FIELDS, check_review, read_review

TAXONOMY = load_taxonomy()
PACKAGES = sorted(glob.glob(os.path.join(R.PACKAGES_DIR, "*", "manifest.json")))
RENAD_P0 = {  # Renad's original package as handed over; it must never change
    "README_AR.md": "1a51fbbb06bb934a9bb2b85db8f2dff598b22d173326b7e79929096b8d3c32d5",
    "Renad_Poetry_Review_40.xlsx": "cf9dcc93ad4a3b76f9962f084a27a920816647c1454755961c9c9aadade74042",
    "Renad_Poetry_Review_Package.zip": "4ede60c373a103a10b623c994c32c14a80e21d57d3662e632ac59e5d455d9475",
    "annotation_guide_ar.md": "50b3928176f9b2e398cc0585f67c6407893d15e2babf5e5ac0147ba0f7a99d31",
    "renad_review_sheet_p0.csv": "4395a347c111cbbbbd779ad8bd1675a536da86874ef1fadc3f43c52207ef21bd",
}


def package(manifest_path):
    with open(manifest_path, encoding="utf-8") as fh:
        manifest = json.load(fh)
    records = [r for b in manifest["batches"] for _, r in C.load_records([records_path(b)])]
    return os.path.dirname(manifest_path), manifest, records


@unittest.skipUnless(os.path.isdir(os.path.join(C.ROOT, "handoff", "renad_p0")), "the P0 package is not distributed")
class RenadPackageUntouched(unittest.TestCase):
    def test_p0_package_files_are_byte_identical(self):
        folder = os.path.join(C.ROOT, "handoff", "renad_p0")
        for name, digest in RENAD_P0.items():
            with open(os.path.join(folder, name), "rb") as fh:
                self.assertEqual(digest, hashlib.sha256(fh.read()).hexdigest(), name)


class ReviewPackages(unittest.TestCase):
    def test_packages_exist(self):
        self.assertTrue(PACKAGES, "no review package found")

    def test_sheets_match_the_records_and_are_blank(self):
        for path in PACKAGES:
            folder, manifest, records = package(path)
            text = {r["verse_id"]: r["text_original"] for r in records}
            for key, ids in (("full_xlsx", "full_verse_ids"), ("full_csv", "full_verse_ids"),
                             ("priority_xlsx", "priority_verse_ids"), ("priority_csv", "priority_verse_ids")):
                with self.subTest(package=manifest["package"], file=key):
                    rows = read_review(os.path.join(folder, manifest["files"][key]))
                    self.assertEqual(manifest[ids], [r["verse_id"] for r in rows])
                    for row in rows:
                        self.assertEqual(text[row["verse_id"]], row["text_original"])
                        for field in REVIEWER_FIELDS + ("visual_decision",):
                            self.assertEqual("", str(row.get(field, "") or "").strip())

    def test_priority_subset_is_part_of_the_package_and_excludes_p0(self):
        for path in PACKAGES:
            _, manifest, records = package(path)
            with self.subTest(package=manifest["package"]):
                self.assertTrue(set(manifest["priority_verse_ids"]) <= set(manifest["full_verse_ids"]))
                self.assertEqual([r["verse_id"] for r in records], manifest["full_verse_ids"])
                self.assertTrue(all(int(v.rsplit(":", 1)[1]) > 40 for v in manifest["full_verse_ids"]))
                for vid in manifest["priority_verse_ids"]:
                    self.assertIn(manifest["priority_levels"][vid], manifest["compact_levels"])

    def test_priority_levels_match_a_fresh_computation(self):
        for path in PACKAGES:
            _, manifest, records = package(path)
            seed = []
            for prior in manifest["prior_packages"]:
                _, m, recs = package(os.path.join(R.PACKAGES_DIR, prior, "manifest.json"))
                seed += [r for r in recs if r["verse_id"] in m["priority_levels"]]
            cells = R.all_cells(TAXONOMY) if manifest.get("cells") == "all" else None
            assigned, _ = R.priority_levels(records, TAXONOMY, seed, cells)
            self.assertEqual(manifest["priority_levels"], dict(sorted(assigned.items(), key=lambda kv: kv[0])))

    def test_zip_holds_the_package_files(self):
        if not glob.glob(os.path.join(R.PACKAGES_DIR, "*", "*.zip")):
            self.skipTest("package zips (duplicates of the files) are not distributed")
        for path in PACKAGES:
            folder, manifest, _ = package(path)
            zips = glob.glob(os.path.join(folder, "*.zip"))
            self.assertEqual(1, len(zips))
            with zipfile.ZipFile(zips[0]) as archive:
                for name in archive.namelist():
                    with open(os.path.join(folder, name), "rb") as fh:
                        self.assertEqual(fh.read(), archive.read(name), name)

    def test_no_review_is_recorded_in_the_records(self):
        for path in PACKAGES:
            _, _, records = package(path)
            for r in records:
                self.assertEqual("not_reviewed", r["review"]["status"])


class Checker(unittest.TestCase):
    def setUp(self):
        folder, self.manifest, records = package(PACKAGES[0])
        self.rows = read_review(os.path.join(folder, self.manifest["files"]["priority_csv"]))
        wanted = set(self.manifest["priority_verse_ids"])
        self.records = [r for r in records if r["verse_id"] in wanted]

    def test_blank_template_passes_until_final(self):
        self.assertEqual([], check_review(self.rows, self.records, visual=True)[0])
        fields = {f for _, f, _ in check_review(self.rows, self.records, final=True, visual=True)[0]}
        self.assertEqual({"decision", "visual_decision"}, fields)

    def test_visual_decisions_are_checked(self):
        rows = [dict(r) for r in self.rows]
        rows[0].update({"decision": "ACCEPT", "visual_decision": "MAYBE"})
        rows[1].update({"decision": "ACCEPT", "visual_decision": "REJECT"})
        rows[2].update({"decision": "ACCEPT", "visual_decision": "ACCEPT"})
        issues = {(v, f) for v, f, _ in check_review(rows, self.records, visual=True)[0]}
        self.assertIn((rows[0]["verse_id"], "visual_decision"), issues)
        self.assertIn((rows[1]["verse_id"], "note"), issues)
        self.assertNotIn((rows[2]["verse_id"], "visual_decision"), issues)


if __name__ == "__main__":
    unittest.main()
