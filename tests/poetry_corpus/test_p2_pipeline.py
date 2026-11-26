"""P2 parallel pipeline: worker checker, exports and merge bookkeeping."""
import json
import os
import tempfile
import unittest

from contracts import apcd
from contracts.validate import display_allowed
from poetry_corpus.tools import coverage as C
from poetry_corpus.tools import export_corpus as E
from poetry_corpus.tools import merge_worker as M
from poetry_corpus.tools.check_worker_spec import check


def corpus():
    return [r for _, r in C.load_records(C.record_files())]


@unittest.skipUnless(apcd.available(), "needs the APCD zip")
class WorkerChecker(unittest.TestCase):
    def test_a_verse_already_in_the_corpus_is_refused(self):
        with open(os.path.join(C.ROOT, "poetry_corpus", "drafts", "p1_b01_ai_draft_specs_v1.json"), encoding="utf-8") as fh:
            spec = json.load(fh)
        verse = {k: v for k, v in spec["verses"][2].items() if k != "n"}
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"worker": "t", "model_id": "claude-opus-5-5", "date": "2026-11-26", "verses": [verse]},
                          fh, ensure_ascii=False)
            problems, total = check(path)
        self.assertEqual(1, total)
        self.assertIn("row already in the corpus", [m for _, _, m in problems])

    def test_missing_top_level_fields_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "w.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"verses": []}, fh)
            problems, _ = check(path)
        self.assertTrue(problems)


class Exports(unittest.TestCase):
    def test_exports_cover_the_whole_corpus_and_only_approved_records_reach_production(self):
        records = corpus()
        with tempfile.TemporaryDirectory() as tmp:
            summary = E.export(tmp, check_apcd=False)
            with open(os.path.join(tmp, "corpus_all_v1.jsonl"), encoding="utf-8") as fh:
                exported = [json.loads(line) for line in fh]
            with open(os.path.join(tmp, "production_eligible_v1.jsonl"), encoding="utf-8") as fh:
                production = [json.loads(line) for line in fh if line.strip()]
            with open(os.path.join(tmp, "corpus_all_v1.csv"), encoding="utf-8-sig") as fh:
                csv_rows = sum(1 for _ in fh) - 1
            self.assertTrue(os.path.isfile(os.path.join(tmp, "corpus_all_v1.xlsx")))
        self.assertEqual(0, summary["issues"])
        self.assertEqual(sorted(r["verse_id"] for r in records), [r["verse_id"] for r in exported])
        self.assertEqual(len(records), csv_rows)
        self.assertEqual([r["verse_id"] for r in records if display_allowed(r, "production")],
                         [r["verse_id"] for r in production])
        self.assertTrue(all(display_allowed(r, "production") for r in production))

    def test_copyright_status_is_derived_for_every_record(self):
        statuses = {E.copyright_status(r) for r in corpus()}
        self.assertTrue(statuses <= {"public_domain_classical", "public_domain_all", "us_risk", "unverified"})


class MergeLog(unittest.TestCase):
    def test_merged_batches_match_the_log(self):
        if not os.path.isfile(M.LOG):
            self.skipTest("no merge yet")
        with open(M.LOG, encoding="utf-8") as fh:
            entries = [json.loads(line) for line in fh if line.strip()]
        batches = {e["batch"]: e for e in entries}
        for batch, entry in batches.items():
            with self.subTest(batch=batch):
                recs = [r for _, r in C.load_records([os.path.join(C.RECORDS_DIR, f"{batch}_ai_drafts_v1.jsonl")])]
                self.assertEqual(entry["merged"], len(recs))
                self.assertEqual(entry["ids"], [recs[0]["verse_id"], recs[-1]["verse_id"]])


if __name__ == "__main__":
    unittest.main()
