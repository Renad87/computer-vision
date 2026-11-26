"""Candidate discovery, Experiment A runner, blind review sheet and the metrics refusal rule."""
import csv
import json
import os
import tempfile
import unittest

from contracts import apcd
from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, validate_document, validate_records
from evaluation.retrieval import make_review_sheet, metrics, run_experiments
from retrieval import discover
from retrieval.engine import load_corpus

from .helpers import APCD_EXTRACT, DEV_CORPUS

TAXONOMY = load_taxonomy()


@unittest.skipUnless(os.path.isfile(APCD_EXTRACT), "the APCD extract is not distributed; download APCD (see README)")
class Discover(unittest.TestCase):
    def test_extract_rows_are_copied_verbatim(self):
        rows = dict(discover.iter_extract(APCD_EXTRACT))
        found = discover.discover(discover.iter_extract(APCD_EXTRACT), "scene_group.desert", "lit_emotion.longing",
                                  TAXONOMY, limit=50)
        self.assertTrue(found)
        self.assertEqual(list(discover.COLUMNS), list(found[0]))
        for c in found:
            row = rows[c["apcd_row"]]
            self.assertEqual(row[apcd.VERSE], c["text"])
            self.assertEqual(row[apcd.POET], c["poet"])
            self.assertEqual(row[apcd.ERA], c["era"])
            self.assertTrue(c["matched_terms"])
        counts = [len(c["matched_terms"].split("|")) for c in found]
        self.assertEqual(counts, sorted(counts, reverse=True))

    def test_apcd_row_numbers_match_the_full_dataset(self):
        if not apcd.available():
            self.skipTest("APCD zip not available")
        found = discover.discover(discover.iter_extract(APCD_EXTRACT), "scene_group.sea", "lit_emotion.awe",
                                  TAXONOMY, limit=200)
        sample = sorted(c["apcd_row"] for c in found)[:3]
        full = apcd.get_rows(sample)
        for c in found:
            if c["apcd_row"] in full:
                self.assertEqual(full[c["apcd_row"]][apcd.VERSE], c["text"])

    def test_exclusion_and_bad_cell(self):
        rows = list(discover.iter_extract(APCD_EXTRACT))
        first = discover.discover(rows, "scene_group.desert", "lit_emotion.longing", TAXONOMY, limit=5)
        skip = [c["apcd_row"] for c in first]
        again = discover.discover(rows, "scene_group.desert", "lit_emotion.longing", TAXONOMY, limit=5,
                                  exclude_rows=skip)
        self.assertFalse(set(skip) & {c["apcd_row"] for c in again})
        with self.assertRaises(ValueError):
            discover.parse_cell("lit_emotion.joy:scene_group.sea", TAXONOMY)

    def test_cli_writes_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "c.csv")
            code = discover.main(["--cell", "tag.moon:lit_emotion.awe", "--apcd-extract", APCD_EXTRACT,
                                  "--limit", "10", "--out", out])
            self.assertEqual(0, code)
            with open(out, encoding="utf-8", newline="") as fh:
                self.assertEqual(list(discover.COLUMNS), next(csv.reader(fh)))


class Evaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.runs = os.path.join(cls.tmp.name, "runs")
        cls.summary, _ = run_experiments.run(DEV_CORPUS, "p0_ai_drafts_v1", "2000-01-01", cls.runs,
                                             latency_repeats=1)
        cls.corpus_map = {r["verse_id"]: r for r in load_corpus(DEV_CORPUS)}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_experiment_a_methods_run_and_validate(self):
        ctx = Context(taxonomy=TAXONOMY, mode="development", corpus=self.corpus_map)
        for _, method, _ in run_experiments.METHODS:
            path = os.path.join(self.runs, f"{method}__p0_ai_drafts_v1__2000-01-01.jsonl")
            with open(path, encoding="utf-8") as fh:
                docs = [json.loads(line) for line in fh]
            self.assertEqual(24, len(docs))
            for doc in docs:
                self.assertEqual([], validate_document("recommendations", doc, ctx), method)
            self.assertEqual(0, self.summary["methods"][method]["contract_issues"])
        self.assertEqual(24, self.summary["methods"]["hybrid"]["status_and_reason_match_expected"])

    def test_review_sheet_is_blind_and_pooled(self):
        out = os.path.join(self.tmp.name, "review")
        sheet, mapping_path, n = make_review_sheet.build(self.runs, "p0_ai_drafts_v1", "2000-01-01", out)
        with open(sheet, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        self.assertEqual(n, len(rows))
        self.assertEqual(list(make_review_sheet.SHEET_COLUMNS), list(rows[0]))
        self.assertFalse(any("method" in c for c in rows[0]))
        self.assertTrue(all(r[c] == "" for r in rows for c in make_review_sheet.RATING_COLUMNS))
        with open(mapping_path, encoding="utf-8") as fh:
            mapping = json.load(fh)
        self.assertEqual({r["sheet_item_id"] for r in rows}, set(mapping["items"]))
        ids = [r["sheet_item_id"] for r in rows]
        self.assertNotEqual(sorted(ids), ids)  # shuffled
        again, _, _ = make_review_sheet.build(self.runs, "p0_ai_drafts_v1", "2000-01-01", out)
        with open(again, encoding="utf-8", newline="") as fh:
            self.assertEqual(ids, [r["sheet_item_id"] for r in csv.DictReader(fh)])  # fixed seed
        # An unrated sheet imports nothing, and metrics refuse to run.
        records, incomplete = make_review_sheet.import_sheet(sheet, "R1", mapping_path)
        self.assertEqual(([], n), (records, incomplete))
        with self.assertRaises(metrics.MissingRatings):
            metrics.compute({}, mapping, make_review_sheet.load_runs(self.runs, "p0_ai_drafts_v1", "2000-01-01"))
        with self.assertRaises(metrics.MissingRatings):
            metrics.load_ratings([os.path.join(self.tmp.name, "absent.jsonl")])

    def test_metric_arithmetic_on_synthetic_values(self):
        # Synthetic numbers to check the arithmetic only. They are not ratings and never reach a report.
        self.assertAlmostEqual(3 / 1 + 2 / 1.584962500721156, metrics.dcg([3, 2]))
        result = metrics.bootstrap([0.0, 0.0, 0.0])
        self.assertEqual(0.0, result["mean_diff"])
        self.assertEqual([0.0, 0.0], result["ci95"])

    def test_imported_records_validate(self):
        out = os.path.join(self.tmp.name, "review2")
        sheet, mapping_path, _ = make_review_sheet.build(self.runs, "p0_ai_drafts_v1", "2000-01-01", out)
        with open(sheet, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        rows[0].update(visual_fit="2", emotion_fit="1", overall="2")  # synthetic test values, not a judgment
        filled = os.path.join(out, "filled.csv")
        with open(filled, "w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=make_review_sheet.SHEET_COLUMNS)
            w.writeheader()
            w.writerows(rows)
        records, incomplete = make_review_sheet.import_sheet(filled, "test_rater", mapping_path,
                                                             timestamp="2000-01-01T00:00:00Z")
        self.assertEqual((1, len(rows) - 1), (len(records), incomplete))
        issues = validate_records("evaluation_record", [(1, r) for r in records],
                                  Context(taxonomy=TAXONOMY, mode="production"))
        self.assertEqual([], issues)
        self.assertTrue(records[0]["blind"])


if __name__ == "__main__":
    unittest.main()
