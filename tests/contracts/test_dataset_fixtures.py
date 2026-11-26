"""Synthetic image_manifest fixtures for dataset engineering (fixtures/dataset/)."""
import json
import os
import re
import subprocess
import sys
import unittest

from contracts.taxonomy import load_taxonomy
from contracts.tools.build_dataset_fixtures import CATEGORIES, LICENSE, OUT, render
from contracts.validate import Context, load_jsonl, validate_records

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TAXONOMY = load_taxonomy()
REQUESTED = {"scene_only", "emotion_only", "both_labels", "missing_scene_metadata", "unmapped_scene",
             "unsupported_scene", "exact_duplicate", "cross_split_leakage", "invalid_annotation"}


def records_of(relative):
    records, problems = load_jsonl(os.path.join(OUT, *relative.split("/")))
    assert not problems, problems
    return records


def found_issues(relative, mode):
    issues = validate_records("image_manifest", records_of(relative), Context(taxonomy=TAXONOMY, mode=mode))
    return [[i.code, i.path] for i in issues]


class DatasetFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(OUT, "expected_outcomes.json"), encoding="utf-8") as fh:
            cls.cases = json.load(fh)["cases"]

    def test_files_equal_a_fresh_build(self):
        rendered, on_disk = render(), {}
        for dirpath, dirnames, filenames in os.walk(OUT):
            dirnames[:] = [d for d in dirnames if d != "__pycache__"]
            for name in filenames:
                if name.startswith("."):
                    continue
                path = os.path.join(dirpath, name)
                with open(path, encoding="utf-8") as fh:
                    on_disk[os.path.relpath(path, OUT).replace(os.sep, "/")] = fh.read()
        self.assertEqual(sorted(rendered), sorted(on_disk))
        for relative, text in rendered.items():
            self.assertEqual(text, on_disk[relative],
                             f"{relative}: rebuild with python3 -m contracts.tools.build_dataset_fixtures")

    def test_expected_outcomes_match_the_validator(self):
        for case in self.cases:
            for mode, expected in case["expected"].items():
                with self.subTest(file=case["file"], mode=mode):
                    found = found_issues(case["file"], mode)
                    self.assertEqual(expected["issues"], found)
                    self.assertEqual(expected["codes"], sorted({code for code, _ in found}))
                    self.assertEqual(expected["exit_code"], 1 if found else 0)
                    self.assertEqual(case["records"], len(records_of(case["file"])))

    def test_valid_files_pass_and_are_rejected_in_production(self):
        valid = [c for c in self.cases if c["file"].startswith("valid/")]
        self.assertGreaterEqual(len(valid), 10)
        for case in valid:
            with self.subTest(file=case["file"]):
                self.assertEqual([], case["expected"]["fixture"]["issues"])
                self.assertEqual(["E_FIXTURE_IN_PRODUCTION"], case["expected"]["production"]["codes"])
                self.assertEqual(case["records"], len(case["expected"]["production"]["issues"]))

    def test_invalid_files_are_named_after_their_first_code(self):
        invalid = [c for c in self.cases if c["file"].startswith("invalid/")]
        self.assertGreaterEqual(len(invalid), 20)
        for case in invalid:
            with self.subTest(file=case["file"]):
                code = os.path.basename(case["file"]).split("_", 1)[1].split("__")[0]
                self.assertIn(code, case["expected"]["fixture"]["codes"])
                self.assertNotEqual([], case["expected"]["fixture"]["issues"])

    def test_every_record_is_marked_synthetic(self):
        for case in self.cases:
            for line, record in records_of(case["file"]):
                with self.subTest(file=case["file"], line=line):
                    self.assertIs(True, record.get("fixture"))
                    self.assertTrue(record["source_image_id"].startswith("fixture_"))
                    self.assertTrue(re.split(r"[\\/]", record["image_path"])[-1].startswith("fixture_"))
                    self.assertEqual(LICENSE, record["license_terms"])
                    provenance = record.get("annotation_provenance") or {}
                    self.assertTrue(provenance.get("protocol", "SYNTHETIC FIXTURE").startswith("SYNTHETIC FIXTURE"))
                    self.assertTrue(all(a.startswith("fixture_") for a in provenance.get("annotators", [])))

    def test_requested_cases_are_covered(self):
        categories = {c["category"] for c in self.cases}
        self.assertEqual(set(CATEGORIES), categories)
        self.assertTrue(REQUESTED <= categories)
        for category in REQUESTED:
            kinds = {c["file"].split("/")[0] for c in self.cases if c["category"] == category}
            with self.subTest(category=category):
                self.assertTrue(kinds)
        codes = {code for c in self.cases for code in c["expected"]["fixture"]["codes"]}
        self.assertTrue({"E_DUP_ID", "E_SPLIT_LEAK", "E_STATUS_CONFLICT", "E_UNKNOWN_ID", "E_FORMAT", "E_ENUM",
                         "E_UNKNOWN_FIELD", "E_RANGE", "E_REQUIRED", "E_VERSION"} <= codes)
        statuses = {(r["scene_label_status"], r["emotion_label_status"])
                    for c in self.cases if c["file"].startswith("valid/") for _, r in records_of(c["file"])}
        self.assertTrue({s for s, _ in statuses} >= {"labeled", "unavailable", "unmapped", "excluded_ood"})
        self.assertTrue({e for _, e in statuses} >= {"labeled", "labeled_set", "unavailable"})

    def test_quarantined_images_are_not_in_the_resolved_manifests(self):
        quarantined = {r["image_id"] for _, r in records_of("reports_examples/quarantine_example.jsonl")}
        self.assertTrue(all(r["fixture"] is True for _, r in records_of("reports_examples/quarantine_example.jsonl")))
        for relative in ("valid/V10_leak_resolved_by_quarantine.jsonl", "valid/V11_mini_unified_manifest_v1_shape.jsonl"):
            ids = {r["image_id"] for _, r in records_of(relative)}
            self.assertEqual(set(), ids & quarantined, relative)
        kept = {r["kept_image_id"] for _, r in records_of("reports_examples/quarantine_example.jsonl")}
        self.assertIn("img:places365_sample:fixture_places_kept_test_0007",
                      kept & {r["image_id"] for _, r in records_of("valid/V10_leak_resolved_by_quarantine.jsonl")})

    def test_command_line_exit_codes(self):
        for case in (self.cases[0], self.cases[-1]):
            path = os.path.join(OUT, *case["file"].split("/"))
            result = subprocess.run([sys.executable, "-m", "contracts.validate", "image_manifest", path,
                                     "--mode", "fixture"], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(case["expected"]["fixture"]["exit_code"], result.returncode, result.stdout)


if __name__ == "__main__":
    unittest.main()
