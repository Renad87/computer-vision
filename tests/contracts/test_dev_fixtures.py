"""Synthetic development inputs for the retrieval engine (fixtures/) and the development corpus mode."""
import json
import os
import unittest

from contracts.taxonomy import load_taxonomy
from contracts.tools.build_dev_fixtures import CORPUS, OUT, render
from contracts.validate import Context, display_allowed, load_jsonl, validate_document, validate_file

TAXONOMY = load_taxonomy()


def load(relative):
    with open(os.path.join(OUT, relative), encoding="utf-8") as fh:
        return json.load(fh)


def codes(contract, doc, mode, corpus=None):
    return {i.code for i in validate_document(contract, doc, Context(taxonomy=TAXONOMY, mode=mode, corpus=corpus))}


class DevelopmentFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = load("dev_profiles/index.json")["profiles"]
        cls.corpus = {r["verse_id"]: r for _, r in load_jsonl(CORPUS)[0]}

    def test_files_equal_a_fresh_build(self):
        rendered = render()
        on_disk = {}
        for folder in ("dev_profiles", "dev_queries", "synthetic_inference", "dev_examples"):
            for name in os.listdir(os.path.join(OUT, folder)):
                with open(os.path.join(OUT, folder, name), encoding="utf-8") as fh:
                    on_disk[f"{folder}/{name}"] = fh.read()
        self.assertEqual(sorted(rendered), sorted(on_disk))
        for relative, text in rendered.items():
            self.assertEqual(text, on_disk[relative], f"{relative}: rebuild with python3 -m contracts.tools.build_dev_fixtures")

    def test_profiles_are_valid_synthetic_and_rejected_in_production(self):
        self.assertGreaterEqual(len(self.index), 15)
        for entry in self.index:
            profile = load(entry["profile"])
            with self.subTest(profile=entry["profile"]):
                self.assertEqual(set(), codes("image_profile", profile, "fixture"))
                self.assertIn("E_FIXTURE_IN_PRODUCTION", codes("image_profile", profile, "production"))
                self.assertTrue(profile["fixture"])
                self.assertEqual("synthetic_query", profile["origin"])
                self.assertIsNone(profile["source_inference"])
                self.assertFalse(any(i["suggested_by_model"] for i in profile["confirmed_visual_items"]))

    def test_required_coverage(self):
        profiles = [load(e["profile"]) for e in self.index]
        items = {i["id"] for p in profiles for i in p["confirmed_visual_items"]}
        for group in ("sea", "desert", "greenery", "heritage", "sky_night"):
            self.assertIn(f"scene_group.{group}", items)
        self.assertGreaterEqual(len({p["selected_lit_emotion"] for p in profiles}), 6)
        self.assertTrue(any(i["user_selection"] == "focus" for p in profiles for i in p["confirmed_visual_items"]))
        self.assertTrue(any(p["symbolic_allowed"] for p in profiles))
        self.assertTrue(any(p["emotion_only_allowed"] and not p["confirmed_visual_items"] for p in profiles))
        reasons = {e["expected"]["abstain"] for e in self.index}
        self.assertTrue({"cell_not_covered", "no_visual_match_emotion_only_off"} <= reasons)

    def test_pairs_share_the_visual_profile_when_only_the_emotion_differs(self):
        by_name = {e["profile"]: load(e["profile"]) for e in self.index}
        for entry in self.index:
            if not entry["pair"]:
                continue
            with self.subTest(profile=entry["profile"]):
                self.assertIn(entry["pair"], {os.path.basename(e["profile"])[:-5] for e in self.index})
                a, b = by_name[entry["profile"]], by_name[f"dev_profiles/{entry['pair']}.json"]
                if a["selected_lit_emotion"] != b["selected_lit_emotion"]:
                    self.assertEqual(a["confirmed_visual_items"], b["confirmed_visual_items"])

    def test_expected_verses_exist_in_the_development_corpus(self):
        for entry in self.index:
            for tier in ("tier1", "tier2", "tier3"):
                for verse_id in entry["expected"][tier]:
                    self.assertIn(verse_id, self.corpus, entry["profile"])

    def test_queries_use_the_development_corpus_and_never_production(self):
        for entry in self.index:
            query = load(entry["query"])
            with self.subTest(query=entry["query"]):
                self.assertEqual("development", query["corpus_mode"])
                self.assertEqual(set(), codes("retrieval_query", query, "development"))
                self.assertIn("E_FIXTURE_IN_PRODUCTION", codes("retrieval_query", query, "production"))
                self.assertEqual(load(entry["profile"])["profile_id"], query["profile_id"])

    def test_synthetic_inference_is_not_a_model_prediction(self):
        for name in sorted(os.listdir(os.path.join(OUT, "synthetic_inference"))):
            doc = load(f"synthetic_inference/{name}")
            with self.subTest(file=name):
                self.assertTrue(doc["fixture"])
                self.assertTrue(doc["model_version"].endswith("-synthetic"))
                self.assertEqual(set(), codes("inference_output", doc, "fixture"))
                self.assertIn("E_FIXTURE_IN_PRODUCTION", codes("inference_output", doc, "production"))

    def test_development_examples(self):
        for name in sorted(os.listdir(os.path.join(OUT, "dev_examples"))):
            path = os.path.join(OUT, "dev_examples", name)
            with self.subTest(file=name):
                self.assertEqual([], [str(i) for i in validate_file("recommendations", path, mode="development",
                                                                    corpus_path=CORPUS)])
                prod = {i.code for i in validate_file("recommendations", path, mode="production", corpus_path=CORPUS)}
                self.assertIn("E_FIXTURE_IN_PRODUCTION", prod)

    def test_ai_drafts_only_appear_in_development_mode(self):
        for verse_id, record in self.corpus.items():
            with self.subTest(verse=verse_id):
                self.assertTrue(display_allowed(record, "development"))
                self.assertFalse(display_allowed(record, "production"))
                self.assertFalse(display_allowed(record, "fixture"))


if __name__ == "__main__":
    unittest.main()
