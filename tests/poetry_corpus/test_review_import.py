"""Review import (Workstream C): only unambiguous human ACCEPTs change records; v2 = v1 + those changes."""
import copy
import hashlib
import json
import os
import unittest

from contracts.validate import display_allowed, load_jsonl, validate_file
from poetry_corpus.review import build_priority_review as O
from poetry_corpus.review import import_review as I
from poetry_corpus.tools.review_sheet import read_review

WORKBOOK = os.path.join(I.ROOT, "poetry_corpus", "review", "renad", "Renad_Poetry_Review_41..xlsx")
WORKBOOK_SHA = "9a9a4e0f961f73c7df907e056226a516645255c6c348833609552a9fdb431226"
V1 = os.path.join(I.EXPORTS, "corpus_all_v1.jsonl")
V2 = os.path.join(I.EXPORTS, "corpus_all_v2.jsonl")
PROD_V2 = os.path.join(I.EXPORTS, "production_eligible_v2.jsonl")
PENDING = {"pv:verse:000005", "pv:verse:000007", "pv:verse:000018", "pv:verse:000024", "pv:verse:000031"}


def records(path):
    return [r for _, r in load_jsonl(path)[0]]


@unittest.skipUnless(os.path.isfile(WORKBOOK), "the reviewer's returned workbook is not distributed")
class RenadImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1 = records(V1)
        cls.by_id = {r["verse_id"]: r for r in cls.v1}
        cls.results = I.classify(read_review(WORKBOOK), cls.by_id)

    def test_workbook_copy_is_byte_identical(self):
        self.assertEqual(WORKBOOK_SHA, I.sha256_file(WORKBOOK))

    def test_classification(self):
        self.assertEqual(40, len(self.results))
        self.assertTrue(all(r["text_match"] for r in self.results))
        pending = {r["verse_id"] for r in self.results if r["status"] == I.PENDING}
        self.assertEqual(PENDING, pending)
        self.assertEqual(35, sum(r["status"] == I.IMPORTED for r in self.results))
        self.assertTrue(all(r["visual"] is None for r in self.results), "P0 sheet has no visual column")

    def test_v2_is_v1_plus_imports_only(self):
        v2 = records(V2)
        self.assertEqual([r["verse_id"] for r in self.v1], [r["verse_id"] for r in v2])
        changed = {n["verse_id"] for o, n in zip(self.v1, v2) if o != n}
        self.assertEqual(35, len(changed))
        self.assertFalse(changed & PENDING)
        for old, new in zip(self.v1, v2):
            if new["verse_id"] not in changed:
                continue
            self.assertEqual({k: v for k, v in old.items() if k not in ("annotation", "review")},
                             {k: v for k, v in new.items() if k not in ("annotation", "review")})
            self.assertEqual("ai_draft_human_reviewed", new["annotation"]["method"])
            self.assertEqual(old["annotation"]["model_id"], new["annotation"]["model_id"])
            self.assertEqual(["human:renad"], new["review"]["reviewers"])
            self.assertEqual([("emotion", "accept")], [(d["dimension"], d["decision"]) for d in new["review"]["decisions"]])

    def test_exports_validate_and_display_counts(self):
        self.assertEqual([], validate_file("poetry_record", V2, mode="production"))
        self.assertEqual([], validate_file("poetry_record", PROD_V2, mode="production"))
        v2 = records(V2)
        self.assertEqual(35, sum(display_allowed(r, "production") for r in v2))
        self.assertEqual(len(v2), sum(display_allowed(r, "development") for r in v2))
        self.assertEqual({r["verse_id"] for r in v2 if display_allowed(r, "production")},
                         {r["verse_id"] for r in records(PROD_V2)})


class ClassifyRules(unittest.TestCase):
    """Synthetic sheet rows (test data) on a copy of a real record; nothing is written."""

    def setUp(self):
        self.record = copy.deepcopy(records(V1)[0])
        self.vid = self.record["verse_id"]

    def row(self, **cells):
        base = {"verse_id": self.vid, "text_original": self.record["text_original"], "decision": "",
                "corrected_primary": "", "corrected_secondary": "", "note": ""}
        base.update(cells)
        return base

    def one(self, record=None, **cells):
        return I.classify([self.row(**cells)], {self.vid: record or self.record})[0]

    def test_never_imports_non_accept(self):
        for cells in ({"decision": "REJECT", "note": "x"}, {"decision": "REJECT", "corrected_primary": "الحزن والأسى"},
                      {"decision": "UNSURE", "note": "x"}, {"decision": "CORRECT", "corrected_primary": "الحزن والأسى"},
                      {"decision": "ACCEPT", "corrected_secondary": "الحزن والأسى"}, {"decision": ""},
                      {"decision": "ACCEPT", "text_original": self.record["text_original"] + " "}):
            self.assertEqual(I.PENDING, self.one(**cells)["status"], cells)

    def test_accept_applies_contract_fields(self):
        result = self.one(decision="accept")
        self.assertEqual(I.IMPORTED, result["status"])
        new = I.apply([self.record], [result], "human:test", "2026-11-25")[0]
        self.assertEqual("reviewed", new["review"]["status"])
        self.assertEqual("not_reviewed", self.record["review"]["status"], "input must not be modified")

    def test_visual_only_row_on_reviewed_record(self):
        reviewed = I.apply([self.record], [self.one(decision="ACCEPT")], "human:a", "2026-11-25")[0]
        ok = self.one(record=reviewed, visual_decision="ACCEPT")
        self.assertEqual(I.IMPORTED, ok["status"])
        final = I.apply([reviewed], [ok], "human:b", "2026-11-26")[0]
        self.assertEqual(["human:a", "human:b"], final["review"]["reviewers"])
        self.assertEqual(["emotion", "visual"], [d["dimension"] for d in final["review"]["decisions"]])
        dup = self.one(record=reviewed, decision="ACCEPT", visual_decision="ACCEPT")
        self.assertEqual(I.PENDING, dup["status"], "emotion decided twice")
        self.assertEqual(I.PENDING, self.one(record=reviewed, visual_decision="REJECT", note="x")["status"])


class OmarPackage(unittest.TestCase):
    def test_package_is_blank_verbatim_and_new(self):
        with open(os.path.join(O.OUT_DIR, "priority_v1_manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        v2 = {r["verse_id"]: r for r in records(V2)}
        rows = read_review(os.path.join(O.OUT_DIR, manifest["files"]["xlsx"]))
        ids = [r["verse_id"] for r in rows]
        self.assertEqual(manifest["verse_ids"], ids)
        self.assertTrue(40 <= len(ids) <= 60)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertFalse(set(ids) & PENDING)
        for row in rows:
            self.assertEqual(v2[row["verse_id"]]["text_original"], row["text_original"])
            for field in O.REVIEWER_FIELDS:
                self.assertEqual("", str(row.get(field, "") or "").strip())
            record = v2[row["verse_id"]]
            if row["review_scope"] == O.SCOPE_VISUAL:
                self.assertEqual("reviewed", record["review"]["status"])
            else:
                self.assertEqual("not_reviewed", record["review"]["status"])
        self.assertEqual(manifest["corpus_sha256"], I.sha256_file(V2))


if __name__ == "__main__":
    unittest.main()
