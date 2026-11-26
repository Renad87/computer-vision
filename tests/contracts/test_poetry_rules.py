"""Display rule and record-level rules of the poetry_record contract."""
import copy
import os
import unittest

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, load_jsonl, text_sha256, validate_records

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORPUS = os.path.join(ROOT, "contracts", "fixtures", "valid", "poetry_record", "poetry_fixtures_v1.jsonl")
TAXONOMY = load_taxonomy()


def fixtures():
    records, issues = load_jsonl(CORPUS)
    assert not issues
    return [r for _, r in records]


def human_reviewed(record):
    """A copy of a fixture shaped like a real, human-reviewed production record."""
    r = copy.deepcopy(record)
    r.pop("fixture")
    r["annotation"] = {"annotator_id": "annotator_A", "method": "human", "model_id": None, "date": "2026-11-25"}
    r["review"] = {"status": "reviewed", "reviewers": ["reviewer_B"],
                   "decisions": [{"reviewer_id": "reviewer_B", "dimension": "all", "decision": "accept",
                                  "note": None, "date": "2026-11-25"}]}
    return r


def codes(records, mode="production"):
    return {i.code for i in validate_records("poetry_record", list(enumerate(records, 1)),
                                             Context(taxonomy=TAXONOMY, mode=mode))}


class DisplayRule(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures()[0]
        self.real = human_reviewed(self.fixture)

    def test_synthetic_fixtures_are_displayable_only_in_fixture_mode(self):
        self.assertTrue(display_allowed(self.fixture, "fixture"))
        self.assertFalse(display_allowed(self.fixture, "production"))

    def test_human_reviewed_record_is_displayable(self):
        self.assertTrue(display_allowed(self.real, "production"))

    def test_unreviewed_and_unreviewed_ai_drafts_are_hidden(self):
        r = copy.deepcopy(self.real)
        r["review"] = {"status": "not_reviewed", "reviewers": [], "decisions": []}
        self.assertFalse(display_allowed(r))
        r = copy.deepcopy(self.real)
        r["annotation"].update(method="ai_draft", model_id="some-llm")
        self.assertFalse(display_allowed(r))
        r["annotation"]["method"] = "ai_draft_human_reviewed"
        self.assertTrue(display_allowed(r))

    def test_disputed_attribution_is_hidden(self):
        r = copy.deepcopy(self.real)
        r["attribution_status"] = "disputed"
        self.assertFalse(display_allowed(r))

    def test_development_mode_admits_unreviewed_drafts_only_there(self):
        draft = copy.deepcopy(self.real)
        draft["annotation"].update(method="ai_draft", model_id="claude-opus-5-5")
        draft["review"] = {"status": "not_reviewed", "reviewers": [], "decisions": []}
        self.assertTrue(display_allowed(draft, "development"))
        self.assertFalse(display_allowed(draft, "production"))
        self.assertFalse(display_allowed(draft, "fixture"))
        self.assertFalse(display_allowed(self.fixture, "development"))  # synthetic fixtures stay in fixture mode
        self.assertTrue(display_allowed(self.real, "development"))      # reviewed records remain visible
        disputed = copy.deepcopy(draft)
        disputed["attribution_status"] = "disputed"
        self.assertFalse(display_allowed(disputed, "development"))

    def test_text_must_be_verified_and_intact(self):
        r = copy.deepcopy(self.real)
        r["text_original"] += " "
        self.assertFalse(display_allowed(r))
        r = copy.deepcopy(self.real)
        r["text_verification"]["method"] = "not_verified"
        self.assertFalse(display_allowed(r))


class RecordRules(unittest.TestCase):
    def setUp(self):
        self.records = fixtures()
        self.real = human_reviewed(self.records[0])

    def test_real_record_passes_in_production(self):
        self.assertEqual(set(), codes([self.real]))

    def test_fixture_corpus_passes_in_fixture_mode(self):
        self.assertEqual(set(), codes(self.records, "fixture"))

    def test_reviewer_must_differ_from_annotator(self):
        self.real["review"]["reviewers"] = ["annotator_A"]
        self.assertIn("E_STATUS_CONFLICT", codes([self.real]))

    def test_has_emotion_needs_a_primary_emotion(self):
        self.real["emotions"]["primary"] = []
        self.assertIn("E_STATUS_CONFLICT", codes([self.real]))

    def test_neutral_records_carry_no_emotions(self):
        self.real["emotion_status"] = "neutral"
        self.assertIn("E_STATUS_CONFLICT", codes([self.real]))

    def test_evoked_emotion_needs_a_short_justification(self):
        entry = self.real["emotions"]["secondary"][0]
        self.assertEqual("evoked", entry["basis"])
        entry["justification_ar"] = None
        self.assertIn("E_REQUIRED", codes([self.real]))
        entry["justification_ar"] = " ".join(["كلمة"] * 16)
        self.assertIn("E_RANGE", codes([self.real]))

    def test_attribution_rules(self):
        r = copy.deepcopy(self.real)
        r["evidence_ids"] = []
        self.assertIn("E_STATUS_CONFLICT", codes([r]))
        r = copy.deepcopy(self.real)
        r["attribution_status"] = "apcd_only"
        self.assertIn("E_STATUS_CONFLICT", codes([r]))  # poem_id is kept only for source_verified records

    def test_ai_draft_needs_model_id(self):
        self.real["annotation"].update(method="ai_draft_human_reviewed", model_id=None)
        self.assertIn("E_REQUIRED", codes([self.real]))

    def test_spans_use_code_point_offsets_on_the_diacritized_text(self):
        for record in self.records:
            text = record["text_original"]
            spans = [a["evidence_span"] for a in record["visual_associations"] if a["evidence_span"]]
            spans += [e["evidence_span"] for role in ("primary", "secondary") for e in record["emotions"][role]
                      if e["evidence_span"]]
            for s in spans:
                self.assertEqual(s["text"], text[s["start"]:s["end"]])
        shifted = copy.deepcopy(self.real)
        shifted["visual_associations"][0]["evidence_span"]["start"] += 1
        self.assertIn("E_SPAN", codes([shifted]))

    def test_text_hash_must_match(self):
        self.real["text_sha256"] = text_sha256("نص آخر")
        self.assertIn("E_APCD_TEXT", codes([self.real]))

    def test_duplicate_apcd_row(self):
        other = human_reviewed(self.records[1])
        other["apcd_row"] = self.real["apcd_row"]
        self.assertIn("E_DUP_ID", codes([self.real, other]))


if __name__ == "__main__":
    unittest.main()
