"""Content and validation rules of the shared taxonomy."""
import copy
import json
import unittest

from contracts.taxonomy import DEFAULT_PATH, load_taxonomy, normalize_places365_name, validate_taxonomy


def load_doc():
    with open(DEFAULT_PATH, encoding="utf-8") as fh:
        return json.load(fh)


def codes(doc):
    issues = []
    validate_taxonomy(doc, issues)
    return {i.code for i in issues}


class TaxonomyContent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tax = load_taxonomy()

    def test_sizes(self):
        self.assertEqual(17, len(self.tax.class_order["scene"]))
        self.assertEqual(8, len(self.tax.class_order["img_emotion"]))
        self.assertEqual(34, len(self.tax.class_order["tag"]))
        self.assertEqual(13, len(self.tax.exposed_tags))
        self.assertEqual(9, len(self.tax.ids("scene_group")))
        self.assertEqual(8, len(self.tax.ids("lit_emotion")))
        self.assertEqual(6, len(self.tax.ids("relation")))

    def test_scene_order_matches_the_visual_module_head(self):
        self.assertEqual(
            ["desert", "sea_coast", "mountains_valleys", "rivers_lakes", "forest", "garden", "farmland_rural", "sky",
             "snow_ice", "modern_city", "old_city_market", "historic_monument", "place_of_worship", "home_interior",
             "camp_tents", "library_books", "__other__"],
            self.tax.external_names["scene"])
        self.assertEqual("scene.other", self.tax.class_order["scene"][-1])

    def test_emotion_order_matches_emoset_and_renad(self):
        self.assertEqual(["amusement", "awe", "contentment", "excitement", "anger", "disgust", "fear", "sadness"],
                         self.tax.external_names["img_emotion"])

    def test_exposed_tags(self):
        self.assertEqual({f"tag.{t}" for t in ("horse", "falcon", "bird", "flower", "moon", "stars", "teapot",
                                               "boat_ship", "sea", "fog", "mosque", "road", "child")},
                         set(self.tax.exposed_tags))

    def test_pilot_sets(self):
        self.assertEqual({"scene_group.desert", "scene_group.sea", "scene_group.greenery", "scene_group.heritage",
                          "scene_group.sky_night"}, set(self.tax.pilot["scene_groups"]))
        self.assertEqual({"lit_emotion.sadness", "lit_emotion.longing", "lit_emotion.awe", "lit_emotion.serenity",
                          "lit_emotion.joy"}, set(self.tax.pilot["lit_emotions"]))

    def test_suggestions_are_explicit_and_never_user_only(self):
        self.assertEqual({("img_emotion.sadness", "lit_emotion.sadness"), ("img_emotion.awe", "lit_emotion.awe"),
                          ("img_emotion.contentment", "lit_emotion.serenity"), ("img_emotion.amusement", "lit_emotion.joy"),
                          ("img_emotion.excitement", "lit_emotion.joy"), ("img_emotion.fear", "lit_emotion.fear")},
                         self.tax.suggestion_pairs)
        self.assertFalse({to for _, to in self.tax.suggestion_pairs} & self.tax.user_only)
        self.assertEqual({"lit_emotion.longing", "lit_emotion.loneliness", "lit_emotion.pride"}, self.tax.user_only)

    def test_relation_weights(self):
        self.assertEqual({"relation.literal": 1.0, "relation.scene_association": 0.7, "relation.symbolic": 0.4,
                          "relation.negated": 0.0, "relation.hypothetical": 0.0, "relation.ambiguous": 0.0},
                         self.tax.relation_weights)

    def test_unsupported_scenes_have_no_group(self):
        grouped = {s for g in self.tax.ids("scene_group") for s in self.tax.group_members(g)[0]}
        self.assertEqual({"scene.home_interior", "scene.library_books", "scene.other"},
                         set(self.tax.class_order["scene"]) - grouped)

    def test_places365_mapping(self):
        self.assertEqual(("scene.desert", "labeled"), self.tax.map_places365("/d/desert/sand"))
        self.assertEqual(("scene.desert", "labeled"), self.tax.map_places365("desert-sand"))
        self.assertEqual(("scene.sea_coast", "labeled"), self.tax.map_places365("Coast"))
        self.assertEqual(("scene.other", "labeled"), self.tax.map_places365("conference_room"))
        self.assertEqual((None, "excluded_ood"), self.tax.map_places365("airport_terminal"))
        self.assertEqual((None, "unmapped"), self.tax.map_places365("volcano"))

    def test_normalization(self):
        self.assertEqual("lake/natural", normalize_places365_name(" /l/Lake-Natural "))
        self.assertEqual("desert_road", normalize_places365_name("desert road"))

    def test_every_label_has_criteria_and_provenance(self):
        for label_id, entry in self.tax.labels.items():
            with self.subTest(label=label_id):
                for field in ("name_ar", "definition_ar", "include_ar", "exclude_ar", "examples", "provenance"):
                    self.assertTrue(entry.get(field), field)


class TaxonomyValidation(unittest.TestCase):
    def test_real_file_is_valid(self):
        self.assertEqual(set(), codes(load_doc()))

    def test_duplicate_label(self):
        doc = load_doc()
        doc["labels"].append(copy.deepcopy(doc["labels"][0]))
        self.assertIn("E_DUP_ID", codes(doc))

    def test_user_only_emotion_cannot_be_suggested(self):
        doc = load_doc()
        doc["suggestion_map"].append({"from": "img_emotion.anger", "to": "lit_emotion.pride"})
        self.assertIn("E_STATUS_CONFLICT", codes(doc))

    def test_scene_groups_need_query_terms(self):
        doc = load_doc()
        entry = next(e for e in doc["labels"] if e["id"] == "scene_group.sea")
        del entry["query_terms_ar"]
        self.assertIn("E_REQUIRED", codes(doc))

    def test_category_listed_twice(self):
        doc = load_doc()
        doc["places365_mapping"]["background_for_scene_other"].append("beach")
        self.assertIn("E_STATUS_CONFLICT", codes(doc))

    def test_class_order_must_cover_the_layer(self):
        doc = load_doc()
        doc["model_outputs"]["scene"]["class_order"].pop()
        self.assertTrue({"E_RANGE", "E_STATUS_CONFLICT"} <= codes(doc))

    def test_group_member_must_exist(self):
        doc = load_doc()
        doc["scene_groups"]["scene_group.desert"]["scenes"].append("scene.jungle")
        self.assertIn("E_UNKNOWN_ID", codes(doc))

    def test_unsupported_major_version(self):
        doc = load_doc()
        doc["schema_version"] = "2.0.0"
        self.assertIn("E_VERSION", codes(doc))


if __name__ == "__main__":
    unittest.main()
