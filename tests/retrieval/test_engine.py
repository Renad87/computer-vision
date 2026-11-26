"""recommend(): fixture expectations, pairs, contract validity, production safety, determinism, latency."""
import copy
import json
import random
import time
import unittest

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, display_allowed, validate_document
from retrieval.engine import ENGINE_VERSION, CorpusIndex, RetrievalEngine, expanded_query, load_corpus, recommend

from .helpers import DEV_CORPUS, SNAPSHOT, scenarios

TAXONOMY = load_taxonomy()


def codes(doc, mode, corpus_map=None):
    return {i.code for i in validate_document("recommendations", doc, Context(taxonomy=TAXONOMY, mode=mode,
                                                                              corpus=corpus_map))}


class Engine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.corpus = load_corpus(DEV_CORPUS)
        cls.corpus_map = {r["verse_id"]: r for r in cls.corpus}
        cls.scenarios = scenarios()
        cls.engine = RetrievalEngine(cls.corpus)
        cls.results = {s["name"]: recommend(s["profile"], cls.corpus, s["query"]) for s in cls.scenarios}

    def by_tier(self, doc):
        out = {1: [], 2: [], 3: []}
        for it in doc["items"]:
            out[it["tier"]].append(it["verse_id"])
        return out

    # ------------------------------------------------------------------ expectations (fixtures/dev_profiles)
    def test_all_24_profiles_match_hand_derived_expectations(self):
        self.assertEqual(24, len(self.scenarios))
        for s in self.scenarios:
            with self.subTest(profile=s["name"]):
                doc, ex = self.results[s["name"]], s["expected"]
                got = self.by_tier(doc)
                reason = doc["abstention"]["reason_code"] if doc["abstention"] else None
                self.assertEqual(ex["status"], doc["status"])
                self.assertEqual(ex["abstain"], reason)
                self.assertLessEqual(set(got[1]), set(ex["tier1"]))
                self.assertLessEqual(set(got[2]), set(ex["tier2"]))
                self.assertLessEqual(set(got[3]), set(ex["tier3"]))
                self.assertLessEqual(len(got[3]), 1)
                k = s["query"]["k"]
                if len(ex["tier1"]) + len(ex["tier2"]) <= k:  # everything eligible fits: all of it is returned
                    self.assertEqual(set(ex["tier1"]), set(got[1]))
                    self.assertEqual(set(ex["tier2"]), set(got[2]))
                    if ex["tier3"] and len(ex["tier1"]) + len(ex["tier2"]) < k:
                        self.assertEqual(1, len(got[3]))

    def test_same_scene_different_emotion_changes_the_result(self):
        names = {s["name"]: s for s in self.scenarios}
        checked = 0
        for s in self.scenarios:
            pair = names.get(s["pair"])
            if not pair or s["profile"]["selected_lit_emotion"] == pair["profile"]["selected_lit_emotion"]:
                continue
            a = [i["verse_id"] for i in self.results[s["name"]]["items"]]
            b = [i["verse_id"] for i in self.results[pair["name"]]["items"]]
            self.assertTrue(a != b or not a or not b, (s["name"], pair["name"]))
            checked += 1
        self.assertGreaterEqual(checked, 10)

    def test_changed_focus_changes_tier1(self):
        sky = {i["verse_id"] for i in self.results["DP09_focus_sky_serenity"]["items"]}
        green = {i["verse_id"] for i in self.results["DP10_focus_greenery_serenity"]["items"]}
        self.assertNotEqual(sky, green)

    def test_secondary_emotion_ranks_below_primary(self):
        doc = self.results["DP06_greenery_joy"]
        roles = [i["matched"]["emotion_role"] for i in doc["items"]]
        self.assertEqual(roles, sorted(roles, key=lambda r: r != "primary"))

    def test_empty_query_gives_null_t(self):
        doc = self.results["DP14_emotion_only_longing"]
        self.assertTrue(doc["items"])
        for it in doc["items"]:
            self.assertIsNone(it["scores"]["text"])
            self.assertIsNone(it["scores"]["visual"])
            self.assertEqual(3, it["tier"])

    def test_text_score_is_filled_for_visual_queries(self):
        for it in self.results["DP05_greenery_serenity"]["items"]:
            self.assertIsNotNone(it["scores"]["text"])
            self.assertGreaterEqual(it["scores"]["text"], 0.0)
            self.assertLessEqual(it["scores"]["text"], 1.0)

    def test_tier2_and_tier3_are_disclosed(self):
        for name, tier in (("DP11_sky_fear_symbolic", 2), ("DP14_emotion_only_longing", 3)):
            it = self.results[name]["items"][0]
            self.assertEqual(tier, it["tier"])
            self.assertIn("T_TIER_DISCLOSURE", it["explanation"]["template_ids"])

    def test_diversity_one_verse_per_poem_and_poet_relaxed_only_to_fill_k(self):
        for name, doc in self.results.items():
            keys = [(self.corpus_map[i["verse_id"]]["poet"]["name_apcd"],
                     self.corpus_map[i["verse_id"]]["source"]["meter_apcd"],
                     self.corpus_map[i["verse_id"]]["source"]["rhyme_apcd"]) for i in doc["items"]]
            self.assertEqual(len(keys), len(set(keys)), name)
            self.assertEqual(len(doc["items"]), len({i["verse_id"] for i in doc["items"]}), name)
        poets = [i["poet_name_apcd"] for i in self.results["DP05_greenery_serenity"]["items"]]
        self.assertEqual(3, len(poets))  # two verses by one poet, relaxed because only three are eligible

    # ------------------------------------------------------------------ contract
    def test_every_output_validates_with_the_corpus(self):
        for name, doc in self.results.items():
            with self.subTest(profile=name):
                self.assertEqual(set(), codes(doc, "development", self.corpus_map))
                self.assertEqual(ENGINE_VERSION, doc["engine_version"])
                for it in doc["items"]:
                    self.assertIn("T_DRAFT_DISCLOSURE", it["explanation"]["template_ids"])
                    self.assertEqual(self.corpus_map[it["verse_id"]]["text_original"], it["text_original"])

    def test_expanded_queries_validate(self):
        for s in self.scenarios:
            q = expanded_query(s["profile"], s["query"])
            issues = validate_document("retrieval_query", q, Context(taxonomy=TAXONOMY, mode="development"))
            self.assertEqual([], issues, s["name"])
            self.assertEqual(bool(s["profile"]["confirmed_visual_items"]) or bool(s["profile"]["concept_id"]),
                             bool(q["query_terms_ar"]))

    def test_altering_any_validated_invariant_fails(self):
        doc = self.results["DP05_greenery_serenity"]
        self.assertEqual("ok", doc["status"])
        self.assertGreater(doc["items"][0]["scores"]["final"], doc["items"][-1]["scores"]["final"])

        def broken(mutate):
            d = copy.deepcopy(doc)
            mutate(d)
            return codes(d, "development", self.corpus_map)

        cases = {
            "final": lambda d: d["items"][0]["scores"].__setitem__("final", 0.01),
            "order": lambda d: [d["items"].reverse()] + [it.__setitem__("rank", n) for n, it in enumerate(d["items"], 1)],
            "rank": lambda d: d["items"][0].__setitem__("rank", 2),
            "emotion": lambda d: d["items"][0]["scores"].__setitem__("emotion", 0.6),
            "disclosure": lambda d: (d["items"][0]["explanation"]["template_ids"].remove("T_DRAFT_DISCLOSURE"),
                                     d["items"][0]["explanation"]["sentences_ar"].pop()),
            "sentences": lambda d: d["items"][0]["explanation"]["sentences_ar"].pop(),
            "text": lambda d: d["items"][0].__setitem__("text_original", d["items"][0]["text_original"] + " "),
            "span": lambda d: d["items"][0]["explanation"]["evidence_spans"][0].__setitem__("text", "x"),
            "status": lambda d: d.__setitem__("status", "partial"),
            "duplicate": lambda d: d["items"].__setitem__(1, dict(copy.deepcopy(d["items"][0]), rank=2)),
            "two_tier3": lambda d: [it.__setitem__("tier", 3) for it in d["items"]],
            "poet": lambda d: d["items"][0].__setitem__("poet_name_apcd", "x"),
        }
        for name, mutate in cases.items():
            with self.subTest(case=name):
                self.assertTrue(broken(mutate), name)

    # ------------------------------------------------------------------ production safety
    def test_production_mode_over_the_dev_corpus_abstains_with_empty_corpus(self):
        for s in self.scenarios:
            q = dict(s["query"], corpus_mode="production")
            doc = recommend(s["profile"], self.corpus, q)
            self.assertEqual("abstained", doc["status"])
            self.assertEqual("empty_corpus", doc["abstention"]["reason_code"])
            self.assertIsNone(doc["abstention"]["coverage_gap"])

    def test_development_outputs_fail_in_production_mode(self):
        for name, doc in self.results.items():
            self.assertIn("E_FIXTURE_IN_PRODUCTION", codes(doc, "production"), name)

    def test_production_shows_only_human_reviewed_records(self):
        # In-memory test copy: one record marked as human-reviewed. Never written anywhere.
        reviewed = copy.deepcopy(self.corpus_map["pv:verse:000021"])
        reviewed["annotation"]["method"] = "ai_draft_human_reviewed"
        reviewed["review"] = {"status": "reviewed", "reviewers": ["test_reviewer"],
                              "decisions": [{"reviewer_id": "test_reviewer", "dimension": "all", "decision": "accept",
                                             "note": None, "date": "2026-11-26"}]}
        corpus = [r for r in self.corpus if r["verse_id"] != "pv:verse:000021"] + [reviewed]
        self.assertEqual(1, sum(display_allowed(r, "production") for r in corpus))
        s = next(x for x in self.scenarios if x["name"] == "DP05_greenery_serenity")
        profile = {k: v for k, v in s["profile"].items() if k != "fixture"}
        query = {k: v for k, v in s["query"].items() if k != "fixture"}
        query.update(corpus_mode="production", corpus_version="test_reviewed_v1")
        doc = recommend(profile, corpus, query)
        self.assertEqual(["pv:verse:000021"], [i["verse_id"] for i in doc["items"]])
        self.assertNotIn("T_DRAFT_DISCLOSURE", doc["items"][0]["explanation"]["template_ids"])
        self.assertEqual(set(), codes(doc, "production", {r["verse_id"]: r for r in corpus}))

    # ------------------------------------------------------------------ purity, determinism, latency
    def test_byte_identical_and_order_independent(self):
        shuffled = list(self.corpus)
        random.Random(7).shuffle(shuffled)
        for s in self.scenarios:
            a = json.dumps(recommend(s["profile"], self.corpus, s["query"]), ensure_ascii=False, sort_keys=False)
            b = json.dumps(recommend(s["profile"], self.corpus, s["query"]), ensure_ascii=False, sort_keys=False)
            c = json.dumps(recommend(s["profile"], shuffled, s["query"]), ensure_ascii=False, sort_keys=False)
            d = json.dumps(self.engine.recommend(s["profile"], s["query"]), ensure_ascii=False, sort_keys=False)
            self.assertEqual(a, b)
            self.assertEqual(a, c)
            self.assertEqual(a, d)

    def test_inputs_are_not_mutated(self):
        corpus = copy.deepcopy(self.corpus)
        for s in self.scenarios:
            p, q = copy.deepcopy(s["profile"]), copy.deepcopy(s["query"])
            recommend(p, corpus, q)
            self.assertEqual(s["profile"], p)
            self.assertEqual(s["query"], q)
        self.assertEqual(self.corpus, corpus)

    def test_latency_p95_under_100ms(self):
        cold, warm = [], []
        for _ in range(5):
            for s in self.scenarios:
                t = time.perf_counter()
                recommend(s["profile"], self.corpus, s["query"])
                cold.append((time.perf_counter() - t) * 1000)
                t = time.perf_counter()
                self.engine.recommend(s["profile"], s["query"])
                warm.append((time.perf_counter() - t) * 1000)
        p95 = lambda v: sorted(v)[int(0.95 * (len(v) - 1))]
        self.assertLess(p95(cold), 100.0)
        self.assertLess(p95(warm), 100.0)

    def test_timings_are_optional(self):
        s = self.scenarios[0]
        doc = self.engine.recommend(s["profile"], s["query"], with_timings=True)
        self.assertGreaterEqual(doc["timings_ms"]["total"], 0)
        self.assertEqual(set(), codes(doc, "development", self.corpus_map))
        self.assertIsNone(recommend(s["profile"], self.corpus, s["query"])["timings_ms"])

    def test_unsupported_method_is_refused(self):
        s = self.scenarios[0]
        with self.assertRaises(ValueError):
            recommend(s["profile"], self.corpus, dict(s["query"], method="w2v"))

    def test_index_is_reused_and_reload_switches_snapshot(self):
        engine = RetrievalEngine(self.corpus)
        first = engine.index("development")
        self.assertIs(first, engine.index("development"))
        engine.reload(self.corpus[:10])
        self.assertIsNot(first, engine.index("development"))
        self.assertEqual(10, len(engine.index("development").records))
        index = CorpusIndex(self.corpus, "development")
        s = self.scenarios[4]
        self.assertEqual(recommend(s["profile"], self.corpus, s["query"]),
                         recommend(s["profile"], self.corpus, s["query"], index=index))


class Snapshot(unittest.TestCase):
    """The latest corpus export (written by the corpus workstream) loads without code changes."""

    def test_latest_snapshot_outputs_validate(self):
        try:
            corpus = load_corpus(SNAPSHOT)
        except (OSError, ValueError) as exc:  # the export may be absent or being rewritten
            self.skipTest(f"snapshot unavailable: {exc}")
        corpus_map = {r["verse_id"]: r for r in corpus}
        engine = RetrievalEngine(corpus)
        for s in scenarios():
            q = dict(s["query"], corpus_version="corpus_all_v1")
            doc = engine.recommend(s["profile"], q)
            self.assertEqual(set(), codes(doc, "development", corpus_map), s["name"])
            self.assertLessEqual(sum(1 for i in doc["items"] if i["tier"] == 3), 1)
        if not any(display_allowed(r, "production") for r in corpus):  # no human review merged yet
            s = scenarios()[0]
            doc = engine.recommend(s["profile"], dict(s["query"], corpus_mode="production"))
            self.assertEqual("empty_corpus", doc["abstention"]["reason_code"])


if __name__ == "__main__":
    unittest.main()
