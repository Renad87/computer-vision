"""Every valid fixture passes; every invalid fixture fails with the error code in its file name."""
import os
import unittest

from contracts import apcd
from contracts.schema import ERROR_CODES
from contracts.tools.build_fixtures import DEFAULT_CALIBRATION, render
from contracts.validate import CONTRACTS, validate_file

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "contracts", "fixtures")
CORPUS = os.path.join(FIXTURES, "valid", "poetry_record", "poetry_fixtures_v1.jsonl")
TAXONOMY = os.path.join(ROOT, "contracts", "taxonomy", "taxonomy_v1.json")


def fixture_files(kind):
    for contract in sorted(os.listdir(os.path.join(FIXTURES, kind))):
        folder = os.path.join(FIXTURES, kind, contract)
        for name in sorted(os.listdir(folder)):
            if name.endswith((".json", ".jsonl")):
                yield contract, name, os.path.join(folder, name)


def run(contract, path, mode):
    corpus = CORPUS if contract == "recommendations" else None
    return validate_file(contract, path, mode=mode, corpus_path=corpus)


class ValidFixtures(unittest.TestCase):
    def test_taxonomy_file_is_valid(self):
        self.assertEqual([], [str(i) for i in validate_file("taxonomy", TAXONOMY)])

    def test_valid_fixtures_pass_in_fixture_mode(self):
        files = list(fixture_files("valid"))
        self.assertGreaterEqual(len(files), 15)
        for contract, name, path in files:
            with self.subTest(fixture=f"{contract}/{name}"):
                self.assertEqual([], [str(i) for i in run(contract, path, "fixture")])

    def test_valid_fixtures_are_rejected_in_production_mode(self):
        for contract, name, path in fixture_files("valid"):
            with self.subTest(fixture=f"{contract}/{name}"):
                self.assertIn("E_FIXTURE_IN_PRODUCTION", {i.code for i in run(contract, path, "production")})

    def test_every_contract_has_a_valid_fixture(self):
        covered = {contract for contract, _, _ in fixture_files("valid")}
        self.assertEqual(set(CONTRACTS) - {"taxonomy"}, covered)  # the valid taxonomy is the real file


class InvalidFixtures(unittest.TestCase):
    def test_each_invalid_fixture_reports_its_code(self):
        for contract, name, path in fixture_files("invalid"):
            expected = name.split("__", 1)[0]
            mode = "production" if "__production" in name else "fixture"
            with self.subTest(fixture=f"{contract}/{name}"):
                self.assertIn(expected, ERROR_CODES)
                self.assertIn(expected, {i.code for i in run(contract, path, mode)})

    def test_every_error_code_and_contract_has_an_invalid_fixture(self):
        files = list(fixture_files("invalid"))
        self.assertEqual(set(ERROR_CODES), {name.split("__", 1)[0] for _, name, _ in files})
        self.assertEqual(set(CONTRACTS), {contract for contract, _, _ in files})


@unittest.skipUnless(apcd.available() and os.path.isfile(DEFAULT_CALIBRATION),
                     "needs the APCD zip and the visual module calibration file")
class FixturesUpToDate(unittest.TestCase):
    def test_fixture_files_equal_a_fresh_build(self):
        files, _, _ = render()
        on_disk = {}
        for kind in ("valid", "invalid"):
            for contract in os.listdir(os.path.join(FIXTURES, kind)):
                folder = os.path.join(FIXTURES, kind, contract)
                for name in os.listdir(folder):
                    with open(os.path.join(folder, name), encoding="utf-8") as fh:
                        on_disk[f"{kind}/{contract}/{name}"] = fh.read()
        self.assertEqual(sorted(files), sorted(on_disk), "fixture files differ from the builder's list")
        for relative, text in files.items():
            self.assertEqual(text, on_disk[relative], f"{relative} was edited by hand; rebuild with "
                                                      "python3 -m contracts.tools.build_fixtures")


if __name__ == "__main__":
    unittest.main()
