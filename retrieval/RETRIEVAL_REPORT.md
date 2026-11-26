# Retrieval report: engine 1.0.0 (milestone M5, owner Mohammed)

- **Status:** implemented and tested, 2026-11-26.
- **Authorship:** the code was written by Claude (`claude-opus-5-5`) in a Claude Code session, at the project owner's request, on Mohammed's behalf. Mohammed owns the component and the presentation; this report does not claim that he typed the code.
- **Authoritative method:** `docs/RETRIEVAL_METHOD.md` (identical to `handoff/mohammed_m5/RETRIEVAL_METHOD.md`). Contracts: `contracts/CONTRACTS.md` v1.0.0 (draft).
- **What this report contains:** engineering results only. **No human relevance metric is reported**: no blind rating exists yet. Every "agreement" number below is computed against AI-draft labels or the hand-derived fixture expectations, not against human judgment.

## 1. Method as implemented

| Step | File | Implementation |
|---|---|---|
| Preprocessing N0/N1/N2 | `retrieval/preprocess.py` | NFC; remove U+064B–U+0652, U+0670 and tatweel; fold أ إ آ ٱ → ا; keep ى and ة; punctuation → space; N1 strips ال/وال/بال/كال/فال/لل with ≥ 3 letters left; N2 also strips one proclitic و ف ب ك ل, except protected words (taxonomy query terms plus فراق، وداع، وادي، بكاء). Negations لا ما لم لن ليس are never removed. |
| Bag of Words, TF-IDF, cosine | `retrieval/tfidf.py` | Sparse dict vectors. Smoothed: `tf = count`, `idf = ln((1+N)/(1+df)) + 1`. Lecture: `tf = count/total`, `idf = ln(N/(1+df))`. Both L2-normalized; cosine = dot product. |
| T | `retrieval/engine.py` (`CorpusIndex.text_score`) | `T = 0.7·cos(q, verse) + 0.3·cos(q, meaning)`; `cos(q, verse)` when the record has no `meaning_ar`; `null` for an empty query. Query = taxonomy `query_terms_ar` of the confirmed items (focus 2, primary 1, secondary 0.5) + concept terms (0.5), no emotion terms. |
| E, ρ, V, anchors, tiers | `retrieval/labels.py` | E = 1.0 primary, 0.6 secondary, otherwise not eligible (also for `neutral`, `ambiguous`, `not_annotated`). ρ from `taxonomy.relation_weights`, symbolic only when allowed. V = weighted coverage, `null` without items. Anchors = focus, else all items. |
| Score, order, diversity, abstention | `retrieval/rank.py` | `final` = weighted mean of the non-null components (no min-max). Order: tier, final, secondary-emotion match, verse_id. Unique verse and text hash; one verse per poem; one per poet unless fewer than k would remain; near-duplicate cosine > 0.8; at most one tier-3 item. Abstention reasons in the order of method section 7. |
| Explanations | `retrieval/explain.py` | Template ids and Arabic sentences from method section 8, filled only from taxonomy names and record fields; evidence spans copied from the record. |
| Interface | `retrieval/engine.py` | `recommend(profile, corpus, query) -> dict` (pure) and `RetrievalEngine` (index built once, `reload()` for a new snapshot). |
| Discovery | `retrieval/discover.py` | APCD extract or full zip; suggestions only, never written to a corpus. |
| Experiment A | `evaluation/retrieval/run_experiments.py` | B1-lecture, B1, B3, B4, B5, B5-noTier over the 24 development profiles. |
| Blind sheet, metrics | `evaluation/retrieval/make_review_sheet.py`, `metrics.py` | Pooled shuffled sheet with the method hidden; metrics refuse to run without complete ratings. |

## 2. Deviations and interpretations (to confirm with Omar)

1. **The E gate is kept in every baseline.**
   - The `recommendations` contract requires `scores.emotion` and `matched.emotion_role ∈ {primary, secondary}` for every item.
   - So B1 and B1-lecture rank only emotion-eligible records, by T alone (weights `{0, 0, 1, 0}`).
   - They therefore isolate the text-ranking signal, not "text retrieval without emotion".
2. **Methods without tiers report `tier = 1` for every item** (B1-lecture, B1, B3, B5-noTier).
   - The contract requires a tier of 1–3 and checks the order by tier.
   - In these runs, "1" means "single pool". The tier-2 and tier-3 disclosure sentences still follow the record's real tier.
3. **B3 `labels_exact`:**
   - E-eligible, plus a literal or scene_association relation with any confirmed item (no focus restriction, no symbolic);
   - V = 1.0, weights `{0.5, 0.5, 0, 0}`, so the ranking reduces to primary before secondary, then verse_id.
4. **B4 `labels_weighted`:** the query weights 0.45/0.35/0.20 with T = null. The weights are renormalized to E and V, as method section 5 prescribes for null components.
5. **The lecture cosine is clamped to [0, 1]:** negative IDF can make it negative.
   - The slide writes `log` with no base (Unit8_Part2, p. 9), so the natural log is used.
   - Any base gives the same cosine, because a change of base multiplies every IDF by the same positive constant.
6. **N0 also drops any other combining mark or invisible format character (category Mn/Cf)** instead of turning it into a space, so a stray mark cannot split a word. The current corpora contain only the standard diacritics, so this changes nothing today.
7. **Explanations:**
   - one visual sentence per item, describing the strongest anchor relation (literal, then association, then symbolic);
   - an evoked primary emotion without an evidence span uses its `justification_ar` in the T_EMOTION_PRIMARY sentence;
   - `T_DRAFT_DISCLOSURE` is added in development mode and, defensively, for any record that is not human-reviewed.
8. **`timings_ms` is `null` in `recommend()`,** so that the output is byte-identical. `RetrievalEngine.recommend(..., with_timings=True)` fills it.
9. **`min_score` (θ) > 0:** no abstention code exists for "all candidates below θ". The engine would report `diversity_exhausted`. This cannot happen in v1 (θ = 0). Open question 3.
10. **A record whose visual dimension is `not_annotated` gets V = 0, not null.** The method makes V null only when the profile has no items, and a null V would favour unannotated records in tier 3. Such records can never be tier 1 or 2, because text never creates a visual relation.
11. **The output carries `"fixture": true` when the profile or the query is a fixture,** so the production validator rejects it.

## 3. Preprocessing evidence (N0 vs N1 vs N2)

Source: `preprocessing` in `evaluation/retrieval/runs/summary__*__2026-11-26.json`. Hybrid method, 24 development profiles, 427 query tokens per variant.

| Corpus | Variant | Verse vocabulary | Query tokens found in the vocabulary | Mean records with verse cosine > 0 | Profiles whose hybrid result differs from N1 |
|---|---|---|---|---|---|
| p0 (40) | N0 | 324 | 5 | 0.21 | 3 (DP05, DP10, DP24) |
| p0 (40) | N1 | 318 | 50 | 2.13 | — |
| p0 (40) | N2 | 314 | 58 | 2.42 | 0 |
| export (1,053) | N0 | 5,383 | 245 | 32.7 | 19 |
| export (1,053) | N1 | 4,876 | 335 | 92.0 | — |
| export (1,053) | N2 | 4,436 | 350 | 99.1 | 12 |

- **N0 is too strict.**
  - Verses write the article (`البحر`, `الليل`, `الروض`), while the query terms have none (`بحر`, `ليل`, `روض`).
  - On p0, N0 reaches 3 query words (`فلك`، `ماء`، `منازل`), N1 reaches 16 (for example `بحر`، `ليل`، `روض`، `بيداء`، `سماء`، `غصن`) and N2 reaches 19.
  - Example, verse `pv:verse:000015`: N0 keeps `البحر` and `الهوجاء`; N1 gives `بحر` and `هوجاء`, so the sea query matches.
- **N2 is unsafe.**
  - Of 51 tokens that N2 changes on p0, many are wrong: «بكاؤكما» → «كاؤكما»، «برية» → «رية»، «بغداد» → «غداد»، «وطني» → «طني»، «بيننا» → «يننا»، «وقفت» → «قفت»، «فتوح» → «توح»، «بديلا» → «ديلا»، «فيما» → «يما».
  - It also turns «ليلى» into «يلى» (tested in `tests/retrieval/test_preprocess_tfidf.py`).
  - The gain over N1 is small: +8 query tokens on p0 and +15 on the export.
- **Decision:** N1 stays the default, as the method specifies.

## 4. TF-IDF: lecture formula vs smoothed formula

- **Hand calculation:** three documents `[a b]`, `[a c]`, `[a b b]` (test `test_smoothed_matches_hand_calculation`).

  | Term | df | Smoothed IDF | Lecture IDF |
  |---|---|---|---|
  | a | 3 | 1.0 | ln(3/4) < 0 |
  | b | 2 | ln(4/3) + 1 | 0 |
  | c | 1 | ln 2 + 1 | ln(3/2) |

  Terms with lecture IDF ≤ 0: `a, b` (df ≥ N − 1).
- **On the real corpora,** no term reaches df ≥ N − 1 (p0: N = 40; export: N = 1,053). The lecture formula then equals the smoothed one minus about 1.0009 for every term. The most frequent term `بحر` (df 72) has smoothed IDF 3.670 and lecture IDF 2.669.
- **Effect on results:**
  - p0: B1 and B1-lecture return identical results for all 24 profiles.
  - Export: they differ on 4 profiles (DP17, DP18, DP20, DP21).
- **Why it matters:** the subtraction is not a uniform rescaling. Rare and common terms change relative weight, so a frequent term could even get zero weight. The smoothed formula keeps every weight positive.

## 5. Engineering results on the fixture scenarios (not human judgments)

- **Fixture scenarios (p0, 40 records):** all 24 profiles in `fixtures/dev_profiles/index.json` match the hand-derived expectations: tier-1 and tier-2 sets, the tier-3 choice taken from the listed candidates, status and abstention reason. No disagreement needs to be raised with Omar.
- **Contract:** every output of every method validates with `python3 -m contracts.validate recommendations ... --mode development --corpus ...` (0 issues in all 288 documents).
- **Covered by tests:**
  - same scene with different emotions;
  - changed focus;
  - literal matches and permitted symbolic matches;
  - emotion-only fallback;
  - missing annotations (DP16 falcon, DP17 worship → `cell_not_covered`);
  - unsupported scene (DP15, emotion only);
  - empty results and abstention;
  - duplicates and diversity;
  - production eligibility;
  - determinism and latency.

### Experiment A, descriptive only

- **Columns:**
  - *anchored* = returned items whose draft labels relate them to an anchor;
  - *match exp.* = status and reason equal to the hand-derived expectation (p0 only);
  - *in exp. set* = returned items inside the hand-derived eligible set (p0 only).
- **Latency:** warm, prebuilt index, 20 repeats × 24 profiles. Measured on the shared M5 laptop while other sessions were training and building the corpus.

**p0_ai_drafts_v1 (40 records, sha256 `692bc0f8…`)**

| Code | Method | ok / partial / abstained | Items | Anchored | Primary emotion | Tier 3 | Jaccard vs B5 | Match exp. (of 24) | In exp. set | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|---|---|
| B1-lecture | tfidf_lecture | 24 / 0 / 0 | 72 | 21 | 52 | 0 | 0.27 | 5 | 30 | 0.067 | 0.100 |
| B1 | tfidf | 24 / 0 / 0 | 72 | 21 | 52 | 0 | 0.27 | 5 | 30 | 0.064 | 0.097 |
| B3 | labels_exact | 5 / 10 / 9 | 27 | 25 | 27 | 0 | 0.77 | 20 | 25 | 0.030 | 0.043 |
| B4 | labels_weighted | 5 / 14 / 5 | 32 | 29 | 32 | 3 | 1.00 | 24 | 32 | 0.030 | 0.045 |
| B5 | hybrid | 5 / 14 / 5 | 32 | 29 | 32 | 3 | 1.00 | 24 | 32 | 0.049 | 0.096 |
| B5-noTier | hybrid_no_tier | 24 / 0 / 0 | 72 | 26 | 72 | 0 | 0.38 | 5 | 34 | 0.069 | 0.101 |

**corpus_all_v1 export (1,053 AI drafts, sha256 `c78b05a4…`, validated by the corpus workstream with 0 issues)**

| Code | Method | ok / partial / abstained | Items | Anchored | Primary emotion | Tier 3 | Jaccard vs B5 | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| B1-lecture | tfidf_lecture | 24 / 0 / 0 | 72 | 56 | 46 | 0 | 0.42 | 0.964 | 1.304 |
| B1 | tfidf | 24 / 0 / 0 | 72 | 56 | 46 | 0 | 0.42 | 0.964 | 1.292 |
| B3 | labels_exact | 20 / 1 / 3 | 61 | 59 | 60 | 0 | 0.28 | 0.671 | 0.763 |
| B4 | labels_weighted | 20 / 3 / 1 | 64 | 62 | 63 | 2 | 0.39 | 0.668 | 0.767 |
| B5 | hybrid | 20 / 3 / 1 | 64 | 62 | 63 | 2 | 1.00 | 0.740 | 0.891 |
| B5-noTier | hybrid_no_tier | 24 / 0 / 0 | 72 | 62 | 71 | 0 | 0.89 | 1.035 | 1.441 |

- **Reading guide (descriptive only):**
  - Without tiers, B1 and B5-noTier always return 3 verses, even when no verse is related to the image (DP04, DP08, DP12 on p0). Tiers turn those cases into honest abstentions.
  - On p0, B4 equals B5 because most cells have at most 3 eligible verses. On the 1,053 export, T reorders the eligible verses (Jaccard 0.39 between B4 and B5).
  - Whether that reordering helps is a question for the human ratings.
- **Pairs:** paired profiles that differ only in emotion never share an item on either corpus (DP01/02, 03/04, 05/06, 07/08, 19/20). On the export, DP11 and DP12 return the same verses: literal sky and fear verses now exist, so the symbolic permission no longer matters.

### Latency

| Corpus | Index build | Cold `recommend()` p50 / p95 (index rebuilt every call) | Warm `RetrievalEngine` hybrid p50 / p95 |
|---|---|---|---|
| p0, 40 records | 1.5 ms | 1.39 / 1.46 ms | 0.049 / 0.096 ms |
| export, 1,053 records | 41.9 ms | 33.12 / 33.89 ms | 0.74 / 0.89 ms |

Both are below the method target (p95 < 100 ms for ≤ 1,000 records). The application should use the warm path.

## 6. Human evaluation: prepared, not done

- **Blind sheets:** the union of every method's top 3, shuffled with seed 20261126, method hidden:
  - `evaluation/retrieval/review/sheet__p0_ai_drafts_v1__2026-11-26.csv` (98 items);
  - `evaluation/retrieval/review/sheet__corpus_all_v1__2026-11-26.csv` (151 items).
- **Method mapping:** kept in the matching `mapping__*.json` files, which must not be shown to raters.
- **Status:** no rating exists. `metrics.py` refuses to compute (exit code 3) until the sheets are completed by human raters and imported with `make_review_sheet.py import`.
- **Not reported until then:** P@3, nDCG@3, emotion and visual relevance, abstention correctness and the bootstrap comparisons.
- **Rules:** weights and thresholds stay at their provisional values. No tuning was done, and none may be done on PV-Test.

## 7. Word2Vec

Not attempted: it is optional, needs the owner's approval to install `gensim`, and was not needed for completion.

## 8. Known limitations

- Every record is an unreviewed AI draft. Production mode returns `empty_corpus` until reviewed records are merged (`poetry_corpus/exports/production_eligible_v1.jsonl` is empty).
- Records that share a full hemistich (2 pairs in the export's `duplicate_report_v1.md`) are not treated as duplicates. The method's duplicate rule is the same `text_sha256`, and their cosine may stay below 0.8. None of these pairs was returned together in the 144 export runs (6 methods × 24 profiles).
- T counts exact token overlap only. Synonyms that are not taxonomy query terms are invisible to it (the lecture's own limitation of TF-IDF).
