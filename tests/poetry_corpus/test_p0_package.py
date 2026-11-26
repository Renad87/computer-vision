"""Renad's P0 review package: draft records, workbook, CSV, zip and the returned-sheet checker."""
import collections
import csv
import json
import os
import tempfile
import unittest
import zipfile

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, load_jsonl, validate_records
from poetry_corpus.tools import build_p0_drafts as B
from poetry_corpus.tools.review_sheet import (CONTRACT_COLUMNS, CSV_COLUMNS, DECISIONS, NONE_AR, PDF, RLE,
                                              REVIEWER_FIELDS, SHEET_REVIEW, build_rows, check_review,
                                              read_review, write_workbook)
from poetry_corpus.tools.xlsx import read_validations

TAXONOMY = load_taxonomy()
XLSX = os.path.join(B.OUT_DIR, B.FILES[0])
CSV_PATH = os.path.join(B.OUT_DIR, B.FILES[1])


def drafts():
    records, issues = load_jsonl(B.RECORDS)
    assert not issues
    return [r for _, r in records]


class DraftRecords(unittest.TestCase):
    def setUp(self):
        self.records = drafts()

    def test_contract_valid_in_production_mode(self):
        issues = validate_records("poetry_record", list(enumerate(self.records, 1)),
                                  Context(taxonomy=TAXONOMY, mode="production"))
        self.assertEqual([], [str(i) for i in issues])

    def test_forty_verses_five_per_literary_emotion(self):
        self.assertEqual(40, len(self.records))
        counts = collections.Counter(r["emotions"]["primary"][0]["id"] for r in self.records)
        self.assertEqual({e: 5 for e in B.EMOTION_ORDER}, dict(counts))

    def test_all_annotations_are_ai_drafts_pending_review(self):
        for r in self.records:
            with self.subTest(verse=r["verse_id"]):
                self.assertEqual("ai_draft", r["annotation"]["method"])
                self.assertEqual("claude-opus-5-5", r["annotation"]["model_id"])
                self.assertEqual({"status": "not_reviewed", "reviewers": [], "decisions": []}, r["review"])
                self.assertFalse(display_allowed(r))
                self.assertNotIn("fixture", r)

    def test_stable_ids_and_unique_rows(self):
        self.assertEqual([f"pv:verse:{n:06d}" for n in range(1, 41)], [r["verse_id"] for r in self.records])
        self.assertEqual(40, len({r["apcd_row"] for r in self.records}))

    def test_attribution_comes_only_from_the_knowledge_base(self):
        for r in self.records:
            with self.subTest(verse=r["verse_id"]):
                verified = r["attribution_status"] == "source_verified"
                self.assertEqual(verified, r["poem_id"] is not None)
                self.assertEqual(verified, bool(r["evidence_ids"]))
                self.assertIn(r["attribution_status"], ("source_verified", "apcd_only"))


@unittest.skipUnless(apcd.available() and os.path.isfile(B.DEFAULT_KB), "needs the APCD zip and the history KB")
class AgainstApcd(unittest.TestCase):
    def test_every_record_matches_its_apcd_row(self):
        issues = validate_records("poetry_record", list(enumerate(drafts(), 1)),
                                  Context(taxonomy=TAXONOMY, mode="production", apcd_zip=apcd.DEFAULT_ZIP))
        self.assertEqual([], [str(i) for i in issues])

    def test_records_equal_a_fresh_build(self):
        with open(B.SPECS, encoding="utf-8") as fh:
            specs = json.load(fh)
        rows = apcd.get_rows([s["apcd_row"] for s in specs["verses"]])
        self.assertEqual(drafts(), B.build_records(specs, rows, B.load_kb(B.DEFAULT_KB)))


@unittest.skipUnless(os.path.isdir(B.OUT_DIR), "the P0 review package delivered to the reviewer is not distributed")
class ReviewPackage(unittest.TestCase):
    def setUp(self):
        self.records = drafts()
        self.text = {r["verse_id"]: r["text_original"] for r in self.records}

    def test_files_and_zip(self):
        for name in B.FILES:
            self.assertTrue(os.path.isfile(os.path.join(B.OUT_DIR, name)), name)
        with zipfile.ZipFile(os.path.join(B.OUT_DIR, B.ZIP_NAME)) as archive:
            self.assertEqual(B.FILES, archive.namelist())
            for name in B.FILES:
                with open(os.path.join(B.OUT_DIR, name), "rb") as fh:
                    self.assertEqual(fh.read(), archive.read(name), name)

    def test_csv_follows_the_review_contract(self):
        with open(CSV_PATH, "rb") as fh:
            self.assertTrue(fh.read(3) == b"\xef\xbb\xbf", "UTF-8 BOM so Excel shows Arabic correctly")
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            self.assertEqual(CSV_COLUMNS, reader.fieldnames)
            self.assertEqual(CONTRACT_COLUMNS, reader.fieldnames[:len(CONTRACT_COLUMNS)])
            rows = list(reader)
        self.assertEqual(40, len(rows))
        for row in rows:
            with self.subTest(verse=row["verse_id"]):
                self.assertEqual(self.text[row["verse_id"]], row["text_original"])
                self.assertEqual("", "".join(row[f] for f in REVIEWER_FIELDS))
                self.assertEqual("lit_emotion", TAXONOMY.layer(row["proposed_primary"]))
                self.assertTrue(row["evidence_text"] and row["evidence_text"] in row["text_original"])

    def test_workbook_rows_match_the_drafts_exactly(self):
        rows = read_review(XLSX)
        self.assertEqual(40, len(rows))
        for row in rows:
            with self.subTest(verse=row["verse_id"]):
                self.assertEqual(self.text[row["verse_id"]], row["text_original"])
                self.assertEqual("", "".join(str(row.get(f, "")) for f in REVIEWER_FIELDS))
                for value in row.values():
                    self.assertNotIn(RLE, str(value))  # direction marks are only in explanatory sheets
                    self.assertNotIn(PDF, str(value))

    def test_workbook_dropdowns(self):
        names = [TAXONOMY.labels[e]["name_ar"] for e in B.EMOTION_ORDER]
        validations = read_validations(XLSX, 3)
        lists = [formula.strip('"').split(",") for _, formula in validations]
        self.assertEqual([list(DECISIONS), names, names + [NONE_AR]], lists)
        self.assertTrue(all(sqref.endswith("41") for sqref, _ in validations))

    def test_workbook_is_right_to_left(self):
        with zipfile.ZipFile(XLSX) as archive:
            for i in (1, 2, 3):
                self.assertIn('rightToLeft="1"', archive.read(f"xl/worksheets/sheet{i}.xml").decode("utf-8"))
            self.assertIn(SHEET_REVIEW, archive.read("xl/workbook.xml").decode("utf-8"))

    def test_readme_states_the_drafts_are_unreviewed(self):
        with open(os.path.join(B.OUT_DIR, "README_AR.md"), encoding="utf-8") as fh:
            readme = fh.read()
        self.assertIn("ai_draft", readme)
        self.assertIn("40 من 40", readme)


@unittest.skipUnless(os.path.isdir(B.OUT_DIR), "the P0 review package delivered to the reviewer is not distributed")
class ReviewChecker(unittest.TestCase):
    def setUp(self):
        self.records = drafts()
        with open(CSV_PATH, encoding="utf-8-sig", newline="") as fh:
            self.template = list(csv.DictReader(fh))

    def filled(self, changes):
        rows = [dict(r) for r in self.template]
        for i, change in changes.items():
            rows[i].update(change)
        return rows

    def test_empty_template_passes_until_final(self):
        self.assertEqual([], check_review(self.template, self.records)[0])
        self.assertEqual(40, len(check_review(self.template, self.records, final=True)[0]))

    def test_valid_decisions_pass(self):
        rows = self.filled({
            0: {"decision": "ACCEPT"},
            1: {"decision": "CORRECT", "corrected_primary": "الحنين والشوق", "corrected_secondary": NONE_AR},
            2: {"decision": "REJECT", "note": "الإحساس الغالب هنا الحب"},
            3: {"decision": "unsure", "note": "يحتمل الحكمة أكثر من الحزن"},
        })
        issues, normalized = check_review(rows, self.records)
        self.assertEqual([], issues)
        self.assertEqual("lit_emotion.longing", normalized[1]["corrected_primary"])
        self.assertEqual("UNSURE", normalized[3]["decision"])

    def test_invalid_decisions_are_reported(self):
        rows = self.filled({
            0: {"decision": "MAYBE"},
            1: {"decision": "CORRECT"},
            2: {"decision": "REJECT"},
            3: {"decision": "UNSURE", "note": " ".join(["كلمة"] * 21)},
            4: {"decision": "CORRECT", "corrected_primary": "الحب"},
            5: {"decision": "ACCEPT", "corrected_primary": "البهجة والسرور"},
            6: {"text_original": self.template[6]["text_original"] + " "},
        })
        rows.pop()  # one verse missing
        fields = {(verse, field) for verse, field, _ in check_review(rows, self.records)[0]}
        for i, field in ((0, "decision"), (1, "corrected_primary"), (2, "note"), (3, "note"),
                         (4, "corrected_primary"), (5, "corrected_primary"), (6, "text_original"),
                         (39, "verse_id")):
            self.assertIn((self.records[i]["verse_id"], field), fields)

    def test_filled_workbook_round_trip(self):
        rows = build_rows(self.records, TAXONOMY)
        rows[0]["decision"] = ("ACCEPT", "ACCEPT")
        rows[1]["decision"] = ("CORRECT", "CORRECT")
        rows[1]["corrected_primary"] = ("lit_emotion.joy", "البهجة والسرور")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "renad_review_v1.xlsx")
            write_workbook(rows, TAXONOMY, path, B.EMOTION_ORDER)
            issues, normalized = check_review(read_review(path), self.records)
        self.assertEqual([], issues)
        self.assertEqual(["ACCEPT", "CORRECT"], [n["decision"] for n in normalized[:2]])
        self.assertEqual("lit_emotion.joy", normalized[1]["corrected_primary"])


if __name__ == "__main__":
    unittest.main()
