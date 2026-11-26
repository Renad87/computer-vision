"""APCD verification of the poetry fixtures, and the validator command line."""
import copy
import os
import subprocess
import sys
import unittest

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, load_jsonl, text_sha256, validate_file, validate_records

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VALID = os.path.join(ROOT, "contracts", "fixtures", "valid")
CORPUS = os.path.join(VALID, "poetry_record", "poetry_fixtures_v1.jsonl")


@unittest.skipUnless(apcd.available(), "APCD zip not available (set PV_APCD_ZIP)")
class ApcdVerification(unittest.TestCase):
    def test_known_row_is_read_verbatim(self):
        row = apcd.get_rows([1874])[1874]
        self.assertEqual(8, len(row))
        self.assertEqual("المُتَنَبّي", row[apcd.POET])
        self.assertTrue(row[apcd.VERSE].startswith(row[apcd.SHATR_RIGHT]))

    def test_poetry_fixtures_match_their_apcd_rows(self):
        issues = validate_file("poetry_record", CORPUS, mode="fixture", apcd_zip=apcd.DEFAULT_ZIP)
        self.assertEqual([], [str(i) for i in issues])

    def test_text_that_differs_from_apcd_is_reported(self):
        records, _ = load_jsonl(CORPUS)
        record = copy.deepcopy(records[0][1])
        record["text_original"] += "ـ"
        record["text_sha256"] = text_sha256(record["text_original"])
        ctx = Context(taxonomy=load_taxonomy(), mode="fixture", apcd_zip=apcd.DEFAULT_ZIP)
        self.assertIn("E_APCD_TEXT", {i.code for i in validate_records("poetry_record", [(1, record)], ctx)})


class CommandLine(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "contracts.validate", *args], cwd=ROOT,
                              capture_output=True, text=True, timeout=120)

    def test_valid_file_exits_zero(self):
        result = self.run_cli("image_profile", os.path.join(VALID, "image_profile", "profile_focus.json"),
                              "--mode", "fixture")
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("", result.stdout)

    def test_invalid_file_exits_one_with_coded_lines(self):
        path = os.path.join(ROOT, "contracts", "fixtures", "invalid", "image_manifest", "E_ENUM__unknown_split.jsonl")
        result = self.run_cli("image_manifest", path, "--mode", "fixture")
        self.assertEqual(1, result.returncode)
        self.assertTrue(result.stdout.startswith("E_ENUM\tL1:split\t"), result.stdout)

    def test_missing_file_exits_two(self):
        self.assertEqual(2, self.run_cli("image_profile", os.path.join(VALID, "missing.json")).returncode)

    def test_unknown_contract_exits_two(self):
        self.assertEqual(2, self.run_cli("not_a_contract", CORPUS).returncode)


if __name__ == "__main__":
    unittest.main()
