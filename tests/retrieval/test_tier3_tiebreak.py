"""Engine 1.1.0: inside tier 3, among equal scores, a scene-neutral verse ranks before one that literally depicts a
scene group the user did not confirm (evaluation/retrieval/quality_diagnosis/REPORT.md)."""
import os
import unittest

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, validate_document
from retrieval import labels as L
from retrieval.engine import ENGINE_VERSION, RetrievalEngine, expanded_query, load_corpus
from retrieval.rank import select, sort_key

from .helpers import ROOT

TAXONOMY = load_taxonomy()
SNAPSHOT_V2 = os.path.join(ROOT, "poetry_corpus", "exports", "corpus_all_v2.jsonl")


def assoc(target, relation):
    return {"target": target, "relation": relation}


def cand(verse_id, tier, final, conflict=False, secondary=False):
    return {"record": {"verse_id": verse_id, "text_sha256": verse_id, "poet": {"name_apcd": verse_id},
                       "source": {}}, "tier": tier, "scores": {"final": final}, "secondary_match": secondary,
            "scene_conflict": conflict}


class SceneConflict(unittest.TestCase):
    def test_unconfirmed_literal_scene_group_is_a_conflict(self):
        rm = L.relation_map({"visual_associations": [assoc("scene_group.mountains", L.LITERAL)]})
        self.assertTrue(L.scene_conflict(rm, ["scene_group.sea"]))
        self.assertTrue(L.scene_conflict(rm, []))
        self.assertFalse(L.scene_conflict(rm, ["scene_group.mountains"]))

    def test_tags_and_non_literal_relations_are_not_conflicts(self):
        rm = L.relation_map({"visual_associations": [assoc("tag.moon", L.LITERAL),
                                                     assoc("scene_group.desert", L.SCENE_ASSOCIATION),
                                                     assoc("scene_group.sky_night", L.SYMBOLIC)]})
        self.assertFalse(L.scene_conflict(rm, ["scene_group.sea"]))
        self.assertFalse(L.scene_conflict({}, ["scene_group.sea"]))


class Ordering(unittest.TestCase):
    def test_tie_prefers_scene_neutral_over_lower_verse_id(self):
        a = cand("pv:verse:000001", 3, 0.45, conflict=True)
        b = cand("pv:verse:000002", 3, 0.45, conflict=False)
        self.assertEqual(["pv:verse:000002", "pv:verse:000001"],
                         [c["record"]["verse_id"] for c in sorted([a, b], key=sort_key)])

    def test_the_tie_break_never_overrides_the_score_or_the_secondary_emotion(self):
        high_conflict = cand("pv:verse:000009", 3, 0.50, conflict=True)
        low_neutral = cand("pv:verse:000001", 3, 0.45, conflict=False)
        self.assertEqual("pv:verse:000009", sorted([low_neutral, high_conflict], key=sort_key)[0]["record"]["verse_id"])
        sec_conflict = cand("pv:verse:000009", 3, 0.45, conflict=True, secondary=True)
        self.assertEqual("pv:verse:000009", sorted([low_neutral, sec_conflict], key=sort_key)[0]["record"]["verse_id"])

    def test_select_takes_the_neutral_tier3_fill(self):
        pool = sorted([cand("pv:verse:000010", 1, 0.8), cand("pv:verse:000001", 3, 0.45, conflict=True),
                       cand("pv:verse:000002", 3, 0.45)], key=sort_key)
        chosen = select(pool, 3, {"max_per_poem": 1, "max_per_poet": 1, "near_dup_cosine": 0.8},
                        lambda a, b: 0.0, max_tier3=1)
        self.assertEqual(["pv:verse:000010", "pv:verse:000002"], [c["record"]["verse_id"] for c in chosen])

    def test_candidates_without_the_flag_keep_the_v1_order(self):
        a = cand("pv:verse:000001", 1, 0.8)
        b = cand("pv:verse:000002", 1, 0.8)
        del a["scene_conflict"], b["scene_conflict"]
        self.assertEqual(["pv:verse:000001", "pv:verse:000002"],
                         [c["record"]["verse_id"] for c in sorted([b, a], key=sort_key)])


@unittest.skipUnless(os.path.exists(SNAPSHOT_V2), "corpus_all_v2 export not available")
class OnTheExport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus(SNAPSHOT_V2)
        cls.engine = RetrievalEngine(cls.corpus)
        cls.ctx = Context(taxonomy=TAXONOMY, mode="development", corpus={r["verse_id"]: r for r in cls.corpus})

    def run_profile(self, items, emotion, mode="development"):
        profile = {"schema_version": "1.0.0", "taxonomy_version": TAXONOMY.version, "fixture": False,
                   "profile_id": "0b0e2c43-5b1e-4f7a-9d8e-1c2b3a4d5e6f", "origin": "user_session",
                   "source_inference": {"image_sha256": "0" * 64, "model_version": "1.0.0"},
                   "confirmed_visual_items": [{"id": i, "user_selection": "primary", "suggested_by_model": True}
                                              for i in items],
                   "selected_lit_emotion": emotion, "secondary_lit_emotion": None, "concept_id": None,
                   "symbolic_allowed": True, "emotion_only_allowed": True}
        query = {"schema_version": "1.0.0", "taxonomy_version": TAXONOMY.version, "fixture": False,
                 "query_id": "6f1d2c3b-4a5e-4b6c-8d7e-9f0a1b2c3d4e", "profile_id": profile["profile_id"],
                 "corpus_version": "corpus_all_v2", "corpus_mode": mode, "method": "hybrid",
                 "preprocessing_variant": "N1", "weights": {"emotion": 0.45, "visual": 0.35, "text": 0.2,
                                                            "semantic": 0.0},
                 "k": 3, "min_score": 0.0, "tiers_enabled": [1, 2, 3],
                 "diversity": {"max_per_poem": 1, "max_per_poet": 1, "near_dup_cosine": 0.8}}
        return self.engine.recommend(profile, expanded_query(profile, query, TAXONOMY))

    def test_engine_version(self):
        self.assertEqual("1.1.0", ENGINE_VERSION)

    def test_tier3_fill_for_an_uncovered_tag_is_scene_neutral(self):
        doc = self.run_profile(["tag.child"], "lit_emotion.awe")  # no child verse exists: one tier-3 fill
        self.assertEqual([3], [i["tier"] for i in doc["items"]])
        rec = {r["verse_id"]: r for r in self.corpus}[doc["items"][0]["verse_id"]]
        self.assertFalse(L.scene_conflict(L.relation_map(rec), ["tag.child"]))
        self.assertEqual([], validate_document("recommendations", doc, self.ctx))

    def test_tier1_items_are_unchanged_by_the_tie_break(self):
        doc = self.run_profile(["tag.bird"], "lit_emotion.awe")
        self.assertEqual(["pv:verse:000387", "pv:verse:000316"], [i["verse_id"] for i in doc["items"] if i["tier"] == 1])
        self.assertEqual([], validate_document("recommendations", doc, self.ctx))


if __name__ == "__main__":
    unittest.main()
