"""P1+ corpus batches: stable ids, no reused APCD rows, verbatim APCD text, drafts only, P0 untouched."""
import glob
import hashlib
import json
import os
import unittest

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, validate_records
from poetry_corpus.tools import build_batch as B
from poetry_corpus.tools import coverage as C

TAXONOMY = load_taxonomy()
P0_RECORDS = os.path.join(C.RECORDS_DIR, "p0_ai_drafts_v1.jsonl")
P0_SHA256 = "692bc0f8da490396a3f6c0d6d797f02986a0eaf991ddbecb5041cce281f43b68"  # as sent to Renad and Mohammed
SPECS = sorted(glob.glob(os.path.join(C.ROOT, "poetry_corpus", "drafts", "p[1-9]_*_ai_draft_specs_v1.json")))
MODEL_ID = r"^claude-[a-z0-9.-]+$"  # each batch names the model that drafted it


def load_spec(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def batch_records():
    """[(batch, [records])] in build order."""
    out = []
    for path in SPECS:
        batch = load_spec(path)["batch"]
        out.append((batch, [r for _, r in C.load_records([B.records_path(batch)])]))
    return out


def all_records():
    return [r for _, r in C.load_records(C.record_files())]


class P0Untouched(unittest.TestCase):
    def test_p0_file_is_byte_identical(self):
        with open(P0_RECORDS, "rb") as fh:
            self.assertEqual(P0_SHA256, hashlib.sha256(fh.read()).hexdigest())

    def test_p0_ids_stay_1_to_40(self):
        ids = [r["verse_id"] for _, r in C.load_records([P0_RECORDS])]
        self.assertEqual([f"pv:verse:{n:06d}" for n in range(1, 41)], ids)


class CorpusIdentity(unittest.TestCase):
    def test_every_spec_has_its_record_file(self):
        self.assertTrue(SPECS, "no P1 batch spec found")
        for path in SPECS:
            batch = load_spec(path)["batch"]
            self.assertTrue(os.path.isfile(B.records_path(batch)), batch)

    def test_ids_are_unique_and_batches_continue_from_41(self):
        records = all_records()
        ids = [r["verse_id"] for r in records]
        self.assertEqual(len(ids), len(set(ids)))
        expected = 41
        for batch, recs in batch_records():
            with self.subTest(batch=batch):
                numbers = [B.verse_number(r["verse_id"]) for r in recs]
                self.assertEqual(list(range(expected, expected + len(recs))), numbers)
                expected += len(recs)

    def test_no_apcd_row_or_verse_text_is_reused(self):
        records = all_records()
        rows = [r["apcd_row"] for r in records]
        texts = [r["text_sha256"] for r in records]
        self.assertEqual(len(rows), len(set(rows)), "an APCD row appears twice in the corpus")
        self.assertEqual(len(texts), len(set(texts)), "the same verse text appears twice in the corpus")

    def test_specs_store_no_verse_text(self):
        for path in SPECS:
            for v in load_spec(path)["verses"]:
                self.assertNotIn("text", v)
                self.assertNotIn("text_original", v)


class DraftStatus(unittest.TestCase):
    def test_batches_are_ai_drafts_pending_review(self):
        for batch, recs in batch_records():
            for r in recs:
                with self.subTest(verse=r["verse_id"]):
                    self.assertEqual("ai_draft", r["annotation"]["method"])
                    self.assertRegex(r["annotation"]["model_id"], MODEL_ID)
                    self.assertEqual(f"ai:{r['annotation']['model_id']}", r["annotation"]["annotator_id"])
                    self.assertEqual({"status": "not_reviewed", "reviewers": [], "decisions": []}, r["review"])
                    self.assertNotIn("fixture", r)
                    self.assertFalse(display_allowed(r, "production"))
                    self.assertTrue(display_allowed(r, "development"))

    def test_attribution_is_apcd_only_unless_the_kb_verifies_it(self):
        for batch, recs in batch_records():
            for r in recs:
                with self.subTest(verse=r["verse_id"]):
                    verified = r["attribution_status"] == "source_verified"
                    self.assertIn(r["attribution_status"], ("apcd_only", "source_verified"))
                    self.assertEqual(verified, bool(r["evidence_ids"]))
                    self.assertEqual(verified, r["poem_id"] is not None)

    def test_contract_valid_in_development_mode(self):
        for batch, recs in batch_records():
            with self.subTest(batch=batch):
                issues = validate_records("poetry_record", list(enumerate(recs, 1)),
                                          Context(taxonomy=TAXONOMY, mode="development"))
                self.assertEqual([], [str(i) for i in issues])


class Coverage(unittest.TestCase):
    def test_symbolic_relations_do_not_count_as_tier1(self):
        record = next(r for r in all_records() if r["verse_id"] == "pv:verse:000097")
        cells = C.cell_members([record], TAXONOMY)
        self.assertEqual([record], cells[("scene_group.sea", "lit_emotion.awe")]["symbolic"])
        self.assertEqual([], cells[("scene_group.sea", "lit_emotion.awe")]["tier1"])
        self.assertEqual([record], cells[("scene_group.sky_night", "lit_emotion.awe")]["tier1"])

    def test_unreviewed_drafts_do_not_count_in_production(self):
        summary = C.summarize(all_records(), TAXONOMY, "production")
        self.assertEqual(0, summary["displayable_records"])
        self.assertEqual(25, summary["pilot_cells_empty"])

    def test_reports_match_the_records(self):
        corpus = []
        for batch, recs in batch_records():
            with self.subTest(batch=batch):
                json_path, md_path = B.report_paths(batch)
                with open(json_path, encoding="utf-8") as fh:
                    report = json.load(fh)
                if not corpus:
                    corpus = [r for _, r in C.load_records([P0_RECORDS])]
                corpus = corpus + recs
                spec = load_spec(next(p for p in SPECS if load_spec(p)["batch"] == batch))
                fresh, _ = B.make_report(spec, recs, corpus, TAXONOMY, report["corpus"]["target_tier1_poems_per_cell"])
                self.assertEqual(fresh, report)
                self.assertTrue(os.path.isfile(md_path))


@unittest.skipUnless(apcd.available(), "needs the APCD zip")
class AgainstApcd(unittest.TestCase):
    def test_text_equals_the_apcd_row(self):
        records = [r for _, recs in batch_records() for r in recs]
        rows = apcd.get_rows([r["apcd_row"] for r in records])
        for r in records:
            with self.subTest(verse=r["verse_id"]):
                row = rows[r["apcd_row"]]
                self.assertEqual(row[apcd.VERSE], r["text_original"])
                self.assertEqual(hashlib.sha256(row[apcd.VERSE].encode("utf-8")).hexdigest(), r["text_sha256"])
                self.assertEqual(row[apcd.POET], r["poet"]["name_apcd"])

    def test_validator_with_apcd_in_development_mode(self):
        for batch, recs in batch_records():
            with self.subTest(batch=batch):
                issues = validate_records("poetry_record", list(enumerate(recs, 1)),
                                          Context(taxonomy=TAXONOMY, mode="development", apcd_zip=apcd.DEFAULT_ZIP))
                self.assertEqual([], [str(i) for i in issues])

    @unittest.skipUnless(os.path.isfile(B.DEFAULT_KB), "needs the history KB")
    def test_record_files_equal_a_fresh_build(self):
        for path in SPECS:
            with self.subTest(spec=os.path.basename(path)):
                spec, records, _ = B.build(path, apcd.DEFAULT_ZIP, B.DEFAULT_KB)
                self.assertEqual([r for _, r in C.load_records([B.records_path(spec["batch"])])], records)


if __name__ == "__main__":
    unittest.main()
