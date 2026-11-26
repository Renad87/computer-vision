"""Narrative of the quality-diagnosis report. build_report.py fills the {{...}} blocks from results.json, the corpus
and the engine output (verse text, spans, justifications and explanations are copied programmatically)."""

TEMPLATE = r"""# Retrieval quality diagnosis: why some verses feel weak or unrelated

- **Date:** 2026-11-26. **Author:** Claude (`claude-opus-5-5`), at the owner's request.
- **Scope:** engine `1.0.0` (frozen copy in `backups/retrieval_v1_0_0/`) against engine `1.1.0` (`retrieval/`), on `poetry_corpus/exports/corpus_all_v2.jsonl` (1,053 records: 35 displayable in production, 1,053 in development).
- **No human relevance judgment exists.** No precision or nDCG is computed. All numbers are transparent proxies, and the side-by-side lists are there so that a human can judge.
- **Reproduce** (standard library only):

  ```bash
  python3 -m evaluation.retrieval.quality_diagnosis.diagnose        # results.json
  python3 -m evaluation.retrieval.quality_diagnosis.build_report    # REPORT.md (+ corpus stats, weak examples)
  ```

- **Files:**

  | File | Content |
  |---|---|
  | `grid.py` | profile and query builders, mirroring `backend/service.py` |
  | `diagnose.py` | the grid runs, the candidate fixes and the metrics |
  | `build_report.py` + `report_template.py` | build this report; every verse, span, justification and explanation is copied programmatically |
  | `results.json` | every number in this report, the per-cell lists for seven options, the coverage matrices, the corpus label statistics and the weak examples |

## 1. How the runs were made

- **Profiles:**
  - built like `backend.service.build_profile`: `origin = user_session`, confirmed items with `user_selection = "primary"` as the frontend sends them, `secondary_lit_emotion = null`;
  - the production `QUERY_DEFAULTS` from `backend/settings.py`: hybrid, N1, 0.45/0.35/0.20, k = 3, `min_score` 0, tiers 1–3, diversity 1/1/0.8;
  - queries expanded with `retrieval.engine.expanded_query`.
- **Grid, 552 cells per mode × 2 modes:**
  - the 9 scene groups plus the 13 exposed tags, as single items, plus 12 realistic group + tag combinations (for example `sky_night+moon`, `sea+boat_ship`);
  - × the 8 literary emotions;
  - × two settings: **default** (frontend default: symbolic off, emotion-only off) and **permissive** (both on);
  - plus 8 no-item profiles (one per emotion), where the backend forces emotion-only.
- **Contract check:** every engine output, both versions, was validated with `contracts.validate.validate_document("recommendations", …)` and the corpus cross-check, in its own mode. Result: **{{VALIDATION}}.**
- **Tests:**
  - `tests/retrieval`: 58 tests (the 49 existing tests + 9 new), all pass;
  - the full suite `python3 -m unittest discover -s tests -t .`: 225 tests, OK, 30 skipped (ML tests).

## 2. Root causes, ranked by impact

| # | Root cause | Evidence (this run) | Where the fix belongs |
|---|---|---|---|
| 1 | **Too few eligible verses in production.** Only 35 displayable records exist, and 16 of them have no visual association at all, so they can only ever be emotion-only fills. | <ul><li>**Default settings:** 85.8% of single-item profiles abstain (96 `cell_not_covered`, 55 `no_visual_match_emotion_only_off`), and 63.5% of the two-item combinations abstain.</li><li>**Targets with zero tier-1 records for every emotion:** city, worship, and the tags horse, falcon, flower, teapot, boat_ship, sea, fog, mosque, road and child.</li><li>Section 3.4 has the count of eligible records per target and emotion.</li></ul> | Corpus review: promote reviewed records, guided by the coverage gaps. Not the engine. |
| 2 | **The emotion-only fill (tier 3) is visually unrelated by construction, and was chosen by `verse_id`.** In production, T = 0 for almost every tier-3 candidate, so all of them tie at final 0.45 (primary emotion). The order rule then picks the lowest `verse_id`. | <ul><li>**Production, permissive:** 81.3% of the returned single-item results are tier 3. They come from only 21 distinct verses; one verse (W4) is the fill in 33 cells.</li><li>**Fills that literally depict a different scene than the one confirmed:** 35.6% (single items) and 31.5% (combinations) in production; 64.2% in development single items.</li><li>A profile without items always returns exactly one verse.</li></ul> | **Engine 1.1.0 (implemented):** a scene-neutral tie-break inside tier 3 (section 5). Showing tier 3 at all stays a methodology and UI decision. |
| 3 | **Label gaps and inconsistencies** between a scene group and the matching tag, or between a label and the record's own span. | <ul><li>W9: a verse that names «البحر» is labelled `scene_group.sea` only, so a `tag.sea` photo receives it as an emotion-only fill.</li><li>W10: a verse about «منازل» is labelled desert/scene_association only, not heritage.</li><li>**Span-implied relations:** 124 relations are implied by the records' own literal spans (32 of them `tag.sea`). Adding them in memory lowers development single-item abstention from 27.3% to 19.9%, and production from 85.8% to 84.1%.</li></ul> | Corpus team (human review of the 124 candidates). Not an engine rule. |
| 4 | **Labels that need context outside the verse, or a "literal" mention that is not what the verse is about.** | <ul><li>**Production:** 3 of the 26 associations carry a justification that refers to the rest of the poem («الضمير يعود…», «في القصيدة»). W1 is labelled *literal* with the span «وَاِنظُر إِلَيهِ».</li><li>**Development:** 33 such justifications and 29 such `meaning_ar` texts.</li><li>Only 1,076 of the 1,499 literal spans (71.8%) contain a taxonomy query term for their target. Most of the others are genuine synonyms (مهامه، سباسب، جداول، حمائم). Some are place names (بغداد، دمشق، حلب as city or heritage, W12), time words (الصبح، الأصيل as sky_night) or incidental mentions (W11).</li></ul> | Annotation guideline and review: mark context-dependent associations `relation.ambiguous` (ρ = 0) or add a `text_note`; restrict "literal" to visible things. |
| 5 | **T (TF-IDF) is small, but it decides the order inside ties, sometimes from accidental matches.** | <ul><li>**Size:** over all emotion-eligible candidates, median T = 0 (p90 0.038 in development, 0 in production). Over the tier-1 candidates, median 0.038 and p90 0.100 (development). The maximum is 0.48, so T adds at most 0.10 to final.</li><li>**Order:** T never lifts a scene_association above a literal item with the same E (0 cases in the returned lists).</li><li>**Influence:** it changes the top-3 order in 198 of the 232 non-abstaining development default cells, and the set in 172.</li><li>**Accidental matches:** polysemy and proper names give T > 0 to unrelated verses (W6 فلك، W7 شعب، W8 صخر in `meaning_ar`, W13 سبيل).</li><li>**Missed matches:** N1 misses 236 of 1,214 query-term occurrences in the verses (19.4%), 101 with a proclitic and 135 with a suffix. Several exposed tags have no query token in the development vocabulary at all (fog, child, road, teapot; section 4).</li></ul> | <ul><li>Taxonomy `query_terms_ar` (contract owner): drop or qualify polysemous terms, add attested synonyms.</li><li>N2 preprocessing is a small, optional gain.</li></ul> |
| 6 | **Weights.** Not a root cause. | <ul><li>Changing ρ(scene_association) from 0.7 to 0.5 changes nothing measurable (literal share 99.4% → 99.7% in development).</li><li>The E gate dominates by design: a primary-emotion association (0.695 + 0.2T) outranks a secondary-emotion literal verse (0.62 + 0.2T).</li></ul> | No weight change is recommended. |
| 7 | **Diversity.** Minor. | <ul><li>Lists with a duplicate poet: 2 production single-item lists and 4 production combinations, all Ibn Khafaja (W15).</li><li>They appear only through the documented relaxation when fewer than k candidates remain. Development has none.</li></ul> | None. Working as specified. |

## 3. Coverage

### 3.1 Production, default settings: returned tiers per cell

`—` means the cell abstained; `1` means one tier-1 verse; `11` means two. Columns are the literary emotions.

{{COVERAGE_PROD_DEFAULT}}

### 3.2 Production, permissive settings (symbolic and emotion-only allowed)

{{COVERAGE_PROD_PERMISSIVE}}

### 3.3 Development, default settings

{{COVERAGE_DEV_DEFAULT}}

### 3.4 Tier-1-eligible records per cell

Each cell reads `primary-literal / primary-scene_association / secondary-emotion (any tier-1 relation)`.

**Production:**

{{ELIGIBLE_PROD}}

**Development:**

{{ELIGIBLE_DEV}}

## 4. Answers to the questions

1. **Limited eligible verses?**
   - **Production:** yes, and it is the first cause (section 3.4). Most of the 22 × 8 cells have zero tier-1 records.
   - **Development:** most scene-group cells have 10 or more, while teapot, fog, road and child have none, and falcon has 2 records in all.
2. **Inaccurate AI labels?** Partly.
   - Literal labels are mostly defensible. 71.8% of the spans contain a query term; the others are mostly real synonyms, which are listed in `results.json → corpus_label_stats.development.frequent_literal_span_tokens_not_in_query_terms`.
   - The weak cases are:
     - place names treated as visual scenes (W12);
     - time words for sky_night;
     - incidental mentions (W11);
     - context-dependent associations (W1–W3; 33 justifications in development);
     - scene-group and tag inconsistencies (W9, 124 span-implied relations).
   - **Scene associations:** 79 of the 84 in development have no evidence span. The contract does not require one, so a missing span says nothing about quality. W2/W3 (context) and the «الربيع» association in production (pv:verse:000026, a good match) look the same to a span check.
3. **Weak visual matching? Does scene_association (0.7) tie with literal?**
   - `V = Σ w·ρ / Σ w`. With the same E, a literal verse leads an association by 0.105 in final, and T never closed that gap in the returned lists.
   - The weakness is not ρ; it is *what* gets labelled literal or associated (answer 2).
   - Demoting associations that have no evidence span (`assoc_needs_evidence`) raises production abstention: from 85.8% to 88.1% (single items) and from 63.5% to 71.9% (combinations). It also removes good verses (pv:verse:000026, pv:verse:000027), so it is not recommended.
4. **Weights?** No change is supported by the proxies (section 6, `assoc_rho_0_5`, `meaning_weight_*`). Under the rules, weights must not change without judged development data.
5. **Missing meaning or context?**
   - `meaning_ar` helps T with synonyms. For example, in W11 the meaning contains the query token «ابل», while the verse has «ركب».
   - It also brings proper names and context into T (W8).
   - `meaning_weight_0` raises the literal-span-has-term share slightly (development combinations 89.2% → 90.6%), but lowers T > 0 from 97.2% to 93.7% and changes few lists.
   - Context dependence is a labelling problem (answer 2).
6. **Arabic preprocessing and `query_terms_ar`:**
   - N0/N1 normalization itself is correct: diacritics, alef forms and tatweel are handled, and no case of a broken word was found.
   - The gaps:
     - **No light stemming:** N1 misses 19.4% of term occurrences ({{N1_COUNTS}}). Examples of missed forms: {{N1_EXAMPLES}}.
     - **Polysemous or proper-name terms:** فلك (ship and orbit), شعب (pass and people), صخر (rock and the name Sakhr), سبيل (road and "way/means"), دار, مدينة (Medina), جنة (paradise).
     - **Query tokens absent from the development vocabulary**, per target: {{OOV}}.
   - `preprocess_N2` changes little: T > 0 +0.3 pp, verse-has-term +0.3 pp.
7. **Does T discriminate?**
   - It is near zero for most candidates (T distribution below).
   - It works as a tie-breaker among records with equal E and V. In development that matters: 85% of the lists change in order without T, 74% in membership.
   - Without T, ties fall back to `verse_id` order, which is arbitrary. So T should stay, and its query terms should be cleaned (answer 6).

   {{T_DIST}}

8. **Does the tier-3 fallback inject unrelated verses?**
   - Yes, by design, whenever emotion-only is on. It is on whenever the user confirms no item, and when the user turns it on.
   - In production, permissive, 81.3% of the returned items are tier-3 fills.
   - **Before 1.1.0:** the fill was the lowest `verse_id` among ties, so the same verse served up to 33 cells, and 35.6% of the fills depicted another scene.
   - **After 1.1.0:** 13.2% (single items) and 12.4% (combinations) in production; 32.8% in development single items, and 0% for no-item profiles in development (from 50%).
   - Gating tier 3 on T > 0 (`tier3_needs_text`) would make every no-item profile abstain (100%), and in tier 3, T > 0 often comes from polysemy (W6–W8, W13). It is rejected.

## 5. What changed: engine 1.1.0

- **The change:** inside tier 3 only, when two candidates have the same tier, the same final score (rounded to 12 decimals) and the same secondary-emotion match, a verse **without** a literal association to a scene group the user did not confirm ranks first. `verse_id` remains the last tie-break.
- **What it does not change:**
  - scores, tiers, eligibility, diversity, explanations and abstention;
  - the contract ordering (tier, then final descending).
  - At most one tier-3 item is still returned.
- **Files:**

  | File | Change |
  |---|---|
  | `retrieval/labels.py` | new `scene_conflict(rel_map, item_ids)` |
  | `retrieval/engine.py` | sets `scene_conflict` on tier-3 candidates; `ENGINE_VERSION = "1.1.0"` |
  | `retrieval/rank.py` | `sort_key` gains the key after the secondary match; candidates without the flag sort as in 1.0.0 |
  | `tests/retrieval/test_tier3_tiebreak.py` | 9 tests |

- **Backup:** `backups/retrieval_v1_0_0/` (v1.0.0, still runnable; `diagnose.py` uses it as the baseline).
- **Effect on the grid:** {{CHANGES}}

| Proxy (tier-3 fills that literally depict an unconfirmed scene group) | v1.0.0 | 1.1.0 |
|---|---|---|
{{CONFLICT_ROWS}}

- **Owner approval needed:**
  - `docs/RETRIEVAL_METHOD.md` section 5 (not owned by this agent) still lists the order as "tier, final, secondary emotion, verse_id". It should add "then, in tier 3, scene-neutral first".
  - If the owner rejects the change, restore `backups/retrieval_v1_0_0/*.py` into `retrieval/`, delete the new test file, and set the version back to 1.0.0.

## 6. Candidate fixes compared with v1.0.0 on the same grid

Shares are over the returned items of each group. "tier-3 fill depicts other scene" is computed over tier-3 items only. Options marked *(rec.)* exist only in `diagnose.py` and are recommendations, not engine changes.

| Option | What it does |
|---|---|
| `v1_0_0` | the baseline |
| `engine_1_1_0` | **implemented** |
| `drop_T` | removes T (method `labels_weighted`); diagnostic only |
| `assoc_needs_evidence` *(rec., rejected)* | tier 1 needs a literal relation, or a scene_association with a span |
| `assoc_rho_0_5` *(rec., rejected)* | ρ(scene_association) = 0.5 |
| `meaning_weight_0` / `meaning_weight_0_5` *(rec., not supported)* | T without `meaning_ar` / with equal weight |
| `tier3_needs_text` *(rec., rejected)* | a tier-3 fill needs T > 0 |
| `min_score_0_5` *(rec., rejected)* | θ = 0.5 for all tiers. It mostly deletes tier-3 fills (final 0.45–0.55) and raises abstention (production combinations 63.5% → 76.0%). The engine would then report `diversity_exhausted`, since no reason code for θ exists. |
| `preprocess_N2` *(rec., optional)* | N2 instead of N1 |
| `tier3_scene_neutral` | the 1.1.0 rule simulated on v1.0.0 (identical lists in all 1,104 cells) |
| `implied_relations` *(rec. for the corpus)* | adds the 124 span-implied relations in memory |

### Production, default settings, single items

{{OPTIONS:production:default/single}}

### Production, default settings, two-item combinations

{{OPTIONS:production:default/combo}}

### Production, permissive settings, single items

{{OPTIONS:production:permissive/single}}

### Production, no confirmed item (emotion-only forced)

{{OPTIONS:production:default/none}}

### Development, default settings, single items

{{OPTIONS:development:default/single}}

### Development, default settings, two-item combinations

{{OPTIONS:development:default/combo}}

### Development, permissive settings, single items

{{OPTIONS:development:permissive/single}}

### Development, no confirmed item

{{OPTIONS:development:default/none}}

## 7. Fifteen weak recommendations (v1.0.0), with their numbers

Verse text, spans, justifications, `meaning_ar` and the explanation sentences are copied from the record and from the engine output.

{{WEAK_EXAMPLES}}

## 8. Side-by-side lists for human judgment

{{SIDE_BY_SIDE}}

## 9. Recommendations and who must approve them

| # | Recommendation | Owner / approval | Evidence |
|---|---|---|---|
| R1 | Keep the 1.1.0 tier-3 tie-break and add it to `docs/RETRIEVAL_METHOD.md` section 5 | Method owner (Mohammed); Omar for the engine version in integration | Section 5 |
| R2 | Review and add the 124 span-implied relations, and make sure scene-group and tag labels agree (for example `scene_group.sea` ⇒ `tag.sea` when the span names the sea) | Corpus workstream, human reviewers. **Never auto-applied.** The list is reproducible with `diagnose.implied_corpus` | `implied_relations` lowers development single-item abstention from 27.3% to 19.9%; W9 |
| R3 | Annotation guideline: an association that depends on another verse becomes `relation.ambiguous` (ρ = 0) or gets a `text_note`; "literal" only for visible things (no bare place names, no time words) | Corpus and annotation owner | W1–W3, W10, W12; 33 context justifications in development |
| R4 | Taxonomy `query_terms_ar`: remove or qualify polysemous terms (فلك، شعب، صخر، سبيل، دار، مدينة، جنة), and add attested synonyms from `frequent_literal_span_tokens_not_in_query_terms` (for example حمائم، جداول، غدران، مهامه، سباسب، طود، سفح، جامع، منبر) | Taxonomy / contract owner (semver bump, consumers approve) | W6–W8, W13; 19.4% N1 misses |
| R5 | Grow the reviewed production corpus, prioritizing the zero-coverage cells of section 3.4 (pilot groups × pilot emotions first). Optionally show the coverage gap in the UI instead of an emotion-only fill | Corpus workstream; UI owner | Root cause 1 |
| R6 | Do **not** adopt `assoc_needs_evidence`, `tier3_needs_text`, `min_score_0_5`, `assoc_rho_0_5` or `meaning_weight_*` | — | Section 6 |
| R7 | Optional: evaluate N2 on judged development data once ratings exist | Method owner | +0.3 pp proxies only |

What was **not** changed: contracts, corpus, taxonomy, backend, frontend, weights, tiers, the E gate, the score formula, diversity, explanations and abstention.
"""
