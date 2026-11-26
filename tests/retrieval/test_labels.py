"""E, rho, V, anchors and tiers on small in-memory records (structure only; no verse text involved)."""
import unittest

from contracts.taxonomy import load_taxonomy
from retrieval import labels as L

RW = load_taxonomy().relation_weights


def record(primary=(), secondary=(), status="has_emotion", assoc=()):
    return {"emotion_status": status,
            "emotions": {"primary": [{"id": e} for e in primary], "secondary": [{"id": e} for e in secondary]},
            "visual_associations": [{"target": t, "relation": r} for t, r in assoc]}


def items(*pairs):
    return [{"id": i, "user_selection": s, "suggested_by_model": False} for i, s in pairs]


class Emotion(unittest.TestCase):
    def test_primary_secondary_and_ineligible(self):
        r = record(primary=["lit_emotion.longing"], secondary=["lit_emotion.sadness"])
        self.assertEqual((1.0, "primary"), L.emotion_match(r, "lit_emotion.longing"))
        self.assertEqual((0.6, "secondary"), L.emotion_match(r, "lit_emotion.sadness"))
        self.assertEqual((None, None), L.emotion_match(r, "lit_emotion.joy"))

    def test_missing_emotion_annotation_is_not_eligible(self):
        for status in ("neutral", "ambiguous", "not_annotated"):
            self.assertEqual((None, None), L.emotion_match(record(status=status), "lit_emotion.joy"))

    def test_secondary_lit_emotion_is_a_preference_only(self):
        r = record(primary=["lit_emotion.awe"], secondary=["lit_emotion.serenity"])
        self.assertTrue(L.secondary_match(r, "lit_emotion.serenity"))
        self.assertFalse(L.secondary_match(r, None))


class Visual(unittest.TestCase):
    def test_rho(self):
        self.assertEqual(1.0, L.rho("relation.literal", False, RW))
        self.assertEqual(0.7, L.rho("relation.scene_association", False, RW))
        self.assertEqual(0.4, L.rho("relation.symbolic", True, RW))
        self.assertEqual(0.0, L.rho("relation.symbolic", False, RW))
        for rel in ("relation.negated", "relation.hypothetical", "relation.ambiguous", None):
            self.assertEqual(0.0, L.rho(rel, True, RW), rel)

    def test_v_weighted_coverage_and_null_without_items(self):
        rm = L.relation_map(record(assoc=[("scene_group.sea", "relation.literal"),
                                          ("tag.moon", "relation.scene_association")]))
        its = items(("scene_group.sea", "focus"), ("tag.moon", "primary"), ("tag.stars", "secondary"))
        self.assertAlmostEqual((2 * 1.0 + 1 * 0.7 + 0.5 * 0) / 3.5, L.visual_score(rm, its, False, RW))
        self.assertIsNone(L.visual_score(rm, [], False, RW))

    def test_focus_restricts_anchors(self):
        p = {"confirmed_visual_items": items(("scene_group.greenery", "primary"), ("scene_group.sky_night", "focus"))}
        self.assertEqual(["scene_group.sky_night"], L.anchors(p))
        p = {"confirmed_visual_items": items(("scene_group.greenery", "primary"), ("tag.bird", "secondary"))}
        self.assertEqual(["scene_group.greenery", "tag.bird"], L.anchors(p))

    def test_tiers(self):
        lit = L.relation_map(record(assoc=[("scene_group.sea", "relation.literal")]))
        sym = L.relation_map(record(assoc=[("scene_group.sea", "relation.symbolic")]))
        neg = L.relation_map(record(assoc=[("scene_group.sea", "relation.negated")]))
        a = ["scene_group.sea"]
        self.assertEqual(1, L.natural_tier(lit, a, False))
        self.assertEqual(2, L.natural_tier(sym, a, True))
        self.assertEqual(3, L.natural_tier(sym, a, False))  # symbolic only when allowed
        self.assertEqual(3, L.natural_tier(neg, a, True))   # negated never anchors
        self.assertFalse(L.covers_anchor(neg, a, True))
        self.assertTrue(L.allowed_tier(1, {"emotion_only_allowed": False}, {1, 2, 3}))
        self.assertFalse(L.allowed_tier(3, {"emotion_only_allowed": False}, {1, 2, 3}))
        self.assertFalse(L.allowed_tier(3, {"emotion_only_allowed": True}, {1, 2}))
        self.assertFalse(L.allowed_tier(2, {"emotion_only_allowed": True}, {1}))

    def test_text_alone_never_creates_a_visual_relation(self):
        # A record whose verse names the sea but has no annotated relation is not tier 1.
        rm = L.relation_map(record(assoc=[]))
        self.assertEqual(3, L.natural_tier(rm, ["scene_group.sea"], True))


if __name__ == "__main__":
    unittest.main()
