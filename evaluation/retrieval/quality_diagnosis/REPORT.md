# Retrieval quality diagnosis: why some verses feel weak or unrelated

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
- **Contract check:** every engine output, both versions, was validated with `contracts.validate.validate_document("recommendations", …)` and the corpus cross-check, in its own mode. Result: **engine 1.0.0: 1104 documents, 0 issues; engine 1.1.0: 1104 documents, 0 issues.**
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

| target | sadness | longing | loneliness | awe | serenity | joy | pride | fear |
|---|---|---|---|---|---|---|---|---|
| `scene_group.desert` | 1 | 1 | — | — | — | — | — | — |
| `scene_group.sea` | 1 | — | 1 | — | — | — | — | — |
| `scene_group.mountains` | — | — | — | 1 | — | — | — | — |
| `scene_group.water` | — | — | — | — | 1 | 11 | 1 | — |
| `scene_group.greenery` | — | — | — | — | 11 | 111 | 1 | — |
| `scene_group.sky_night` | 11 | 1 | — | 1 | 111 | 11 | — | — |
| `scene_group.heritage` | — | — | — | 11 | — | — | 1 | — |
| `scene_group.city` | — | — | — | — | — | — | — | — |
| `scene_group.worship` | — | — | — | — | — | — | — | — |
| `tag.horse` | — | — | — | — | — | — | — | — |
| `tag.falcon` | — | — | — | — | — | — | — | — |
| `tag.bird` | 1 | — | 1 | — | 1 | 1 | — | — |
| `tag.flower` | — | — | — | — | — | — | — | — |
| `tag.moon` | — | — | — | — | — | 1 | — | — |
| `tag.stars` | 1 | — | — | — | — | — | — | 1 |
| `tag.teapot` | — | — | — | — | — | — | — | — |
| `tag.boat_ship` | — | — | — | — | — | — | — | — |
| `tag.sea` | — | — | — | — | — | — | — | — |
| `tag.fog` | — | — | — | — | — | — | — | — |
| `tag.mosque` | — | — | — | — | — | — | — | — |
| `tag.road` | — | — | — | — | — | — | — | — |
| `tag.child` | — | — | — | — | — | — | — | — |

### 3.2 Production, permissive settings (symbolic and emotion-only allowed)

| target | sadness | longing | loneliness | awe | serenity | joy | pride | fear |
|---|---|---|---|---|---|---|---|---|
| `scene_group.desert` | 13 | 13 | 3 | 3 | 3 | 3 | 3 | 3 |
| `scene_group.sea` | 13 | 3 | 13 | 3 | 3 | 3 | 3 | 3 |
| `scene_group.mountains` | 3 | 3 | 3 | 13 | 3 | 3 | 3 | 3 |
| `scene_group.water` | 3 | 3 | 3 | 3 | 13 | 113 | 13 | 3 |
| `scene_group.greenery` | 3 | 3 | 3 | 3 | 113 | 111 | 13 | 3 |
| `scene_group.sky_night` | 113 | 13 | 3 | 13 | 111 | 113 | 23 | 23 |
| `scene_group.heritage` | 3 | 3 | 3 | 113 | 3 | 3 | 13 | 3 |
| `scene_group.city` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `scene_group.worship` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.horse` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.falcon` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.bird` | 13 | 3 | 13 | 3 | 13 | 13 | 3 | 3 |
| `tag.flower` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.moon` | 23 | 23 | 3 | 3 | 3 | 13 | 23 | 3 |
| `tag.stars` | 13 | 3 | 3 | 3 | 3 | 3 | 3 | 13 |
| `tag.teapot` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.boat_ship` | 3 | 3 | 3 | 3 | 3 | 23 | 3 | 3 |
| `tag.sea` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.fog` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.mosque` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.road` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |
| `tag.child` | 3 | 3 | 3 | 3 | 3 | 3 | 3 | 3 |

### 3.3 Development, default settings

| target | sadness | longing | loneliness | awe | serenity | joy | pride | fear |
|---|---|---|---|---|---|---|---|---|
| `scene_group.desert` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `scene_group.sea` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `scene_group.mountains` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `scene_group.water` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `scene_group.greenery` | 111 | 111 | 111 | 111 | 111 | 111 | 11 | 111 |
| `scene_group.sky_night` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `scene_group.heritage` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `scene_group.city` | 111 | — | 1 | — | — | 1 | 11 | 1 |
| `scene_group.worship` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `tag.horse` | — | 1 | 1 | 1 | — | 1 | 111 | — |
| `tag.falcon` | 1 | — | — | — | — | — | — | 1 |
| `tag.bird` | 111 | 111 | 111 | 11 | 111 | 111 | 1 | 1 |
| `tag.flower` | 111 | 111 | — | 111 | 111 | 111 | — | — |
| `tag.moon` | 11 | 111 | 111 | 111 | 111 | 111 | 1 | — |
| `tag.stars` | 111 | 111 | 111 | 111 | 111 | 11 | 111 | 111 |
| `tag.teapot` | — | — | — | — | — | — | — | — |
| `tag.boat_ship` | 111 | 111 | 11 | 111 | 1 | 11 | 111 | 111 |
| `tag.sea` | 111 | 111 | 111 | 111 | 111 | 111 | 111 | 111 |
| `tag.fog` | — | — | — | — | — | — | — | — |
| `tag.mosque` | 111 | 111 | 111 | 111 | 111 | 11 | 111 | 111 |
| `tag.road` | — | — | — | — | — | — | — | — |
| `tag.child` | — | — | — | — | — | — | — | — |

### 3.4 Tier-1-eligible records per cell

Each cell reads `primary-literal / primary-scene_association / secondary-emotion (any tier-1 relation)`.

**Production:**

| target | sadness | longing | loneliness | awe | serenity | joy | pride | fear |
|---|---|---|---|---|---|---|---|---|
| `scene_group.desert` | 0/0/1 | 0/1/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `scene_group.sea` | 0/0/1 | 0/0/0 | 1/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `scene_group.mountains` | 0/0/0 | 0/0/0 | 0/0/0 | 1/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `scene_group.water` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 1/0/0 | 1/0/1 | 0/0/1 | 0/0/0 |
| `scene_group.greenery` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 2/0/0 | 1/2/2 | 0/0/1 | 0/0/0 |
| `scene_group.sky_night` | 1/0/1 | 0/0/1 | 0/0/0 | 1/0/0 | 2/1/0 | 0/0/2 | 0/0/0 | 0/0/0 |
| `scene_group.heritage` | 0/0/0 | 0/0/0 | 0/0/0 | 1/1/0 | 0/0/0 | 0/0/0 | 0/0/1 | 0/0/0 |
| `scene_group.city` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `scene_group.worship` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.horse` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.falcon` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.bird` | 0/0/1 | 0/0/0 | 0/1/0 | 0/0/0 | 1/0/0 | 0/0/1 | 0/0/0 | 0/0/0 |
| `tag.flower` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.moon` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 1/0/0 | 0/0/0 | 0/0/0 |
| `tag.stars` | 0/0/1 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 1/0/0 |
| `tag.teapot` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.boat_ship` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.sea` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.fog` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.mosque` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.road` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.child` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |

**Development:**

| target | sadness | longing | loneliness | awe | serenity | joy | pride | fear |
|---|---|---|---|---|---|---|---|---|
| `scene_group.desert` | 14/0/16 | 33/8/27 | 21/2/17 | 16/1/13 | 11/2/9 | 14/2/4 | 25/4/7 | 16/8/13 |
| `scene_group.sea` | 18/0/8 | 18/0/6 | 5/0/7 | 21/1/11 | 6/0/4 | 10/1/2 | 13/0/6 | 21/1/11 |
| `scene_group.mountains` | 23/0/10 | 37/0/8 | 8/1/5 | 17/0/6 | 4/0/3 | 11/0/4 | 7/0/1 | 4/0/5 |
| `scene_group.water` | 32/0/9 | 28/1/7 | 5/0/4 | 18/1/5 | 24/0/4 | 22/0/11 | 12/0/2 | 6/0/0 |
| `scene_group.greenery` | 38/1/18 | 38/3/23 | 7/0/8 | 18/3/6 | 37/3/10 | 34/3/28 | 1/0/1 | 2/0/1 |
| `scene_group.sky_night` | 32/1/20 | 28/0/17 | 21/0/11 | 32/0/13 | 14/2/9 | 21/0/7 | 14/0/5 | 22/1/10 |
| `scene_group.heritage` | 43/8/26 | 35/2/16 | 14/1/12 | 28/5/14 | 24/0/4 | 23/1/14 | 19/0/5 | 20/0/4 |
| `scene_group.city` | 2/0/1 | 0/0/0 | 1/0/0 | 0/0/0 | 0/0/0 | 1/0/0 | 1/0/1 | 1/0/0 |
| `scene_group.worship` | 25/3/6 | 17/2/7 | 5/1/2 | 13/0/9 | 11/1/6 | 14/1/3 | 4/0/0 | 6/4/3 |
| `tag.horse` | 0/0/0 | 1/0/0 | 0/0/1 | 0/0/1 | 0/0/0 | 1/0/0 | 5/0/0 | 0/0/0 |
| `tag.falcon` | 0/0/1 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 1/0/0 |
| `tag.bird` | 20/1/16 | 20/0/6 | 2/1/1 | 2/0/0 | 5/0/2 | 11/0/5 | 0/0/1 | 1/0/0 |
| `tag.flower` | 7/0/0 | 5/0/3 | 0/0/0 | 8/0/2 | 10/0/1 | 10/0/9 | 0/0/0 | 0/0/0 |
| `tag.moon` | 2/0/0 | 3/0/1 | 2/0/1 | 5/0/1 | 2/0/1 | 4/0/1 | 0/0/1 | 0/0/0 |
| `tag.stars` | 8/0/7 | 8/0/2 | 7/0/3 | 10/0/3 | 3/0/1 | 1/0/1 | 4/0/3 | 3/0/2 |
| `tag.teapot` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.boat_ship` | 1/0/2 | 4/1/1 | 1/0/1 | 6/0/1 | 0/1/0 | 2/0/0 | 3/0/1 | 4/0/4 |
| `tag.sea` | 13/0/3 | 13/0/2 | 1/0/7 | 18/0/9 | 5/0/3 | 9/0/1 | 10/0/5 | 11/0/8 |
| `tag.fog` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.mosque` | 13/0/1 | 5/0/2 | 2/0/2 | 6/0/5 | 6/1/3 | 2/0/0 | 4/0/0 | 3/0/1 |
| `tag.road` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |
| `tag.child` | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 | 0/0/0 |

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
     - **No light stemming:** N1 misses 19.4% of term occurrences (978 exact matches; 101 occurrences with a proclitic and 135 with a suffix are missed). Examples of missed forms: ابلي، اثارهم، ازهارها، اغصانها، امواجه، انهارها، ايكه، ايكها، ايوانه، بابل، باغصان، بايك، بايوان، بحارا، بحرا، بخيل، بدار، بدجلة، برمل، بشاطئ.
     - **Polysemous or proper-name terms:** فلك (ship and orbit), شعب (pass and people), صخر (rock and the name Sakhr), سبيل (road and "way/means"), دار, مدينة (Medina), جنة (paradise).
     - **Query tokens absent from the development vocabulary**, per target: `scene_group.desert`: بادية، خيام، خيمة، ظعائن، كثبان، مفازة، هجير; `scene_group.sea`: شاطئ، شراع، يم; `scene_group.mountains`: اودية، جليد، ذروة، صخر، قمة، هضبة; `scene_group.water`: ساقية، شلال، نبع، ينبوع; `scene_group.greenery`: بستان، حقل، زرع، سنابل، نرجس; `scene_group.sky_night`: هلال; `scene_group.heritage`: اسوار، خرائب، سوق; `scene_group.city`: حاضرة، شارع، شوارع، عمران، ميدان; `scene_group.worship`: اذان، كنيسة، مئذنة، معبد، منارة; `tag.horse`: ادهم، افراس، جواد، جياد، خيول، سابح، صهوة، مهر; `tag.falcon`: باز، بازي، شاهين، صقر، صقور; `tag.bird`: طيور، عندليب، غراب، هزار; `tag.flower`: اقحوان، بنفسج، زهرة، شقائق، نرجس، وردة، ياسمين; `tag.moon`: اقمار، هلال; `tag.teapot`: اباريق، ابريق، دلة; `tag.boat_ship`: زورق، شراع، قارب; `tag.sea`: يم; `tag.fog`: سديم، ضباب; `tag.mosque`: مئذنة، منارة; `tag.road`: درب، دروب، طرق، طريق، فج، مسالك; `tag.child`: اطفال، صبي، صبية، صغار، طفل، غلام، وليد.
   - `preprocess_N2` changes little: T > 0 +0.3 pp, verse-has-term +0.3 pp.
7. **Does T discriminate?**
   - It is near zero for most candidates (T distribution below).
   - It works as a tie-breaker among records with equal E and V. In development that matters: 85% of the lists change in order without T, 74% in membership.
   - Without T, ties fall back to `verse_id` order, which is arbitrary. So T should stay, and its query terms should be cleaned (answer 6).

   | T over | mode | n | =0 | (0,0.05) | [0.05,0.1) | [0.1,0.2) | [0.2,0.3) | [0.3,0.5) | median | p90 |
   |---|---|---|---|---|---|---|---|---|---|---|
   | all E-eligible candidates | production | 1897 | 1731 | 49 | 19 | 32 | 41 | 25 | 0.0 | 0.0 |
   | all E-eligible candidates | development | 56975 | 48120 | 4381 | 3329 | 1097 | 44 | 4 | 0.0 | 0.038 |
   | tier-1 candidates | production | 190 | 64 | 40 | 14 | 28 | 28 | 16 | 0.0372 | 0.2997 |
   | tier-1 candidates | development | 10522 | 2600 | 3774 | 3110 | 994 | 40 | 4 | 0.0384 | 0.0996 |

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
- **Effect on the grid:** 83 of 2 × 552 cells change (4 development no-item, 21 development permissive, 2 production no-item, 56 production permissive). **In every changed cell the tier-1 and tier-2 items are identical; only the tier-3 fill differs.**

| Proxy (tier-3 fills that literally depict an unconfirmed scene group) | v1.0.0 | 1.1.0 |
|---|---|---|
| production, permissive, single items | 35.6% | 13.2% |
| production, permissive, combinations | 31.5% | 12.4% |
| production, no-item profiles | 37.5% | 12.5% |
| development, permissive, single items | 64.2% | 32.8% |
| development, no-item profiles | 50.0% | 0.0% |

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

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `engine_1_1_0` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `drop_T` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 0.0% | 0.0% | 2 |
| `assoc_needs_evidence` | 88.1% | 0.15 | 0.0% | 100.0% | 40.7% | 55.6% | 0.0% | 70.4% | 0.0% | 3 |
| `assoc_rho_0_5` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `meaning_weight_0` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 38.2% | 0.0% | 2 |
| `meaning_weight_0_5` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `tier3_needs_text` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `min_score_0_5` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `preprocess_N2` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `assoc_needs_evidence+tier3_needs_text` | 88.1% | 0.15 | 0.0% | 100.0% | 40.7% | 55.6% | 0.0% | 70.4% | 0.0% | 3 |
| `tier3_scene_neutral` | 85.8% | 0.19 | 0.0% | 73.5% | 32.4% | 50.0% | 26.5% | 64.7% | 0.0% | 2 |
| `implied_relations` | 84.1% | 0.21 | 0.0% | 75.7% | 37.8% | 54.0% | 24.3% | 64.9% | 0.0% | 2 |

### Production, default settings, two-item combinations

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `engine_1_1_0` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `drop_T` | 63.5% | 0.57 | 0.0% | 69.1% | 29.1% | 50.9% | 30.9% | 0.0% | 0.0% | 4 |
| `assoc_needs_evidence` | 71.9% | 0.44 | 0.0% | 100.0% | 38.1% | 57.1% | 0.0% | 71.4% | 0.0% | 6 |
| `assoc_rho_0_5` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `meaning_weight_0` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 38.2% | 0.0% | 4 |
| `meaning_weight_0_5` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `tier3_needs_text` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `min_score_0_5` | 76.0% | 0.36 | 0.0% | 68.6% | 25.7% | 51.4% | 31.4% | 71.4% | 0.0% | 3 |
| `preprocess_N2` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `assoc_needs_evidence+tier3_needs_text` | 71.9% | 0.44 | 0.0% | 100.0% | 38.1% | 57.1% | 0.0% | 71.4% | 0.0% | 6 |
| `tier3_scene_neutral` | 63.5% | 0.57 | 0.0% | 69.1% | 27.3% | 50.9% | 30.9% | 63.6% | 0.0% | 4 |
| `implied_relations` | 62.5% | 0.58 | 0.0% | 69.6% | 28.6% | 51.8% | 30.4% | 62.5% | 0.0% | 4 |

### Production, permissive settings, single items

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.9% | 4.2% | 16.8% | 35.6% | 2 |
| `engine_1_1_0` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.9% | 4.2% | 16.8% | 13.2% | 2 |
| `drop_T` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 13.1% | 4.2% | 0.0% | 35.6% | 2 |
| `assoc_needs_evidence` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.9% | 4.2% | 16.8% | 35.6% | 2 |
| `assoc_rho_0_5` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.9% | 4.2% | 16.8% | 35.6% | 2 |
| `meaning_weight_0` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.4% | 4.2% | 10.3% | 36.2% | 2 |
| `meaning_weight_0_5` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.9% | 4.2% | 16.8% | 35.6% | 2 |
| `tier3_needs_text` | 75.6% | 0.31 | 25.9% | 46.3% | 20.4% | 64.8% | 16.7% | 74.1% | 21.4% | 2 |
| `min_score_0_5` | 81.2% | 0.24 | 7.1% | 59.5% | 26.2% | 59.5% | 21.4% | 69.0% | 33.3% | 2 |
| `preprocess_N2` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 16.4% | 4.2% | 18.2% | 35.6% | 2 |
| `assoc_needs_evidence+tier3_needs_text` | 75.6% | 0.31 | 25.9% | 46.3% | 20.4% | 64.8% | 16.7% | 74.1% | 21.4% | 2 |
| `tier3_scene_neutral` | 0.0% | 1.22 | 81.3% | 11.7% | 5.1% | 15.9% | 4.2% | 16.8% | 13.2% | 2 |
| `implied_relations` | 0.0% | 1.23 | 80.2% | 12.9% | 6.5% | 16.6% | 4.2% | 17.1% | 34.5% | 2 |

### Production, no confirmed item (emotion-only forced)

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `engine_1_1_0` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 12.5% | 0 |
| `drop_T` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `assoc_needs_evidence` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `assoc_rho_0_5` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `meaning_weight_0` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `meaning_weight_0_5` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `tier3_needs_text` | 100.0% | 0.00 | — | — | — | — | — | — | — | 0 |
| `min_score_0_5` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `preprocess_N2` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |
| `assoc_needs_evidence+tier3_needs_text` | 100.0% | 0.00 | — | — | — | — | — | — | — | 0 |
| `tier3_scene_neutral` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 12.5% | 0 |
| `implied_relations` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 37.5% | 0 |

### Development, default settings, single items

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 27.3% | 1.99 | 0.0% | 99.4% | 86.6% | 91.7% | 0.6% | 93.4% | 0.0% | 0 |
| `engine_1_1_0` | 27.3% | 1.99 | 0.0% | 99.4% | 86.6% | 91.7% | 0.6% | 93.4% | 0.0% | 0 |
| `drop_T` | 27.3% | 1.99 | 0.0% | 99.4% | 74.0% | 76.3% | 0.6% | 0.0% | 0.0% | 0 |
| `assoc_needs_evidence` | 27.8% | 1.98 | 0.0% | 100.0% | 87.1% | 92.3% | 0.0% | 93.4% | 0.0% | 0 |
| `assoc_rho_0_5` | 27.3% | 1.99 | 0.0% | 99.7% | 86.9% | 92.0% | 0.3% | 93.4% | 0.0% | 0 |
| `meaning_weight_0` | 27.3% | 1.99 | 0.0% | 99.4% | 86.9% | 92.0% | 0.6% | 88.6% | 0.0% | 0 |
| `meaning_weight_0_5` | 27.3% | 1.99 | 0.0% | 99.4% | 86.6% | 91.4% | 0.6% | 93.4% | 0.0% | 0 |
| `tier3_needs_text` | 27.3% | 1.99 | 0.0% | 99.4% | 86.6% | 91.7% | 0.6% | 93.4% | 0.0% | 0 |
| `min_score_0_5` | 27.3% | 1.99 | 0.0% | 99.4% | 86.6% | 91.7% | 0.6% | 93.4% | 0.0% | 0 |
| `preprocess_N2` | 27.3% | 1.99 | 0.0% | 99.4% | 87.1% | 92.0% | 0.6% | 93.7% | 0.0% | 0 |
| `assoc_needs_evidence+tier3_needs_text` | 27.8% | 1.98 | 0.0% | 100.0% | 87.1% | 92.3% | 0.0% | 93.4% | 0.0% | 0 |
| `tier3_scene_neutral` | 27.3% | 1.99 | 0.0% | 99.4% | 86.6% | 91.7% | 0.6% | 93.4% | 0.0% | 0 |
| `implied_relations` | 19.9% | 2.14 | 0.0% | 99.5% | 87.8% | 92.3% | 0.5% | 89.4% | 0.0% | 0 |

### Development, default settings, two-item combinations

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `engine_1_1_0` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `drop_T` | 0.0% | 2.99 | 0.0% | 100.0% | 76.3% | 82.6% | 0.0% | 0.0% | 0.0% | 0 |
| `assoc_needs_evidence` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `assoc_rho_0_5` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `meaning_weight_0` | 0.0% | 2.99 | 0.0% | 100.0% | 90.6% | 98.3% | 0.0% | 93.7% | 0.0% | 0 |
| `meaning_weight_0_5` | 0.0% | 2.99 | 0.0% | 100.0% | 88.5% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `tier3_needs_text` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `min_score_0_5` | 0.0% | 2.95 | 0.0% | 100.0% | 89.0% | 97.5% | 0.0% | 97.2% | 0.0% | 0 |
| `preprocess_N2` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.9% | 0.0% | 97.2% | 0.0% | 0 |
| `assoc_needs_evidence+tier3_needs_text` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `tier3_scene_neutral` | 0.0% | 2.99 | 0.0% | 100.0% | 89.2% | 97.6% | 0.0% | 97.2% | 0.0% | 0 |
| `implied_relations` | 0.0% | 2.99 | 0.0% | 100.0% | 89.9% | 97.6% | 0.0% | 96.5% | 0.0% | 0 |

### Development, permissive settings, single items

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 0.0% | 2.39 | 16.0% | 82.9% | 72.1% | 80.5% | 0.5% | 83.8% | 64.2% | 0 |
| `engine_1_1_0` | 0.0% | 2.39 | 16.0% | 82.9% | 72.1% | 80.7% | 0.5% | 83.8% | 32.8% | 0 |
| `drop_T` | 0.0% | 2.39 | 16.0% | 82.9% | 61.7% | 64.3% | 0.5% | 0.0% | 47.8% | 0 |
| `assoc_needs_evidence` | 0.0% | 2.39 | 16.0% | 83.1% | 72.4% | 80.7% | 0.2% | 83.8% | 64.2% | 0 |
| `assoc_rho_0_5` | 0.0% | 2.39 | 16.0% | 83.1% | 72.4% | 80.7% | 0.2% | 83.8% | 64.2% | 0 |
| `meaning_weight_0` | 0.0% | 2.39 | 16.0% | 82.9% | 72.4% | 80.7% | 0.5% | 77.4% | 56.7% | 0 |
| `meaning_weight_0_5` | 0.0% | 2.39 | 16.0% | 82.9% | 72.1% | 80.2% | 0.5% | 83.8% | 64.2% | 0 |
| `tier3_needs_text` | 19.9% | 2.16 | 7.1% | 91.6% | 79.7% | 90.0% | 0.5% | 93.7% | 96.3% | 0 |
| `min_score_0_5` | 27.3% | 2.00 | 0.0% | 98.9% | 86.1% | 91.8% | 0.6% | 93.5% | 0.0% | 0 |
| `preprocess_N2` | 0.0% | 2.39 | 16.0% | 82.9% | 72.6% | 81.0% | 0.5% | 84.5% | 64.2% | 0 |
| `assoc_needs_evidence+tier3_needs_text` | 19.9% | 2.16 | 7.1% | 91.8% | 80.0% | 90.3% | 0.3% | 93.7% | 96.3% | 0 |
| `tier3_scene_neutral` | 0.0% | 2.39 | 16.0% | 82.9% | 72.1% | 80.7% | 0.5% | 83.8% | 32.8% | 0 |
| `implied_relations` | 0.0% | 2.52 | 14.4% | 84.7% | 74.7% | 81.0% | 0.4% | 81.0% | 62.5% | 0 |

### Development, no confirmed item

| option | abstention | items/profile | tier-3 share | literal share | literal span has query term | verse has query term | unevidenced assoc | T>0 | tier-3 fill depicts other scene | dup-poet lists |
|---|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `engine_1_1_0` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0 |
| `drop_T` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `assoc_needs_evidence` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `assoc_rho_0_5` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `meaning_weight_0` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `meaning_weight_0_5` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `tier3_needs_text` | 100.0% | 0.00 | — | — | — | — | — | — | — | 0 |
| `min_score_0_5` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `preprocess_N2` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |
| `assoc_needs_evidence+tier3_needs_text` | 100.0% | 0.00 | — | — | — | — | — | — | — | 0 |
| `tier3_scene_neutral` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0 |
| `implied_relations` | 0.0% | 1.00 | 100.0% | 0.0% | 0.0% | 0.0% | 0.0% | 0.0% | 50.0% | 0 |

## 7. Fifteen weak recommendations (v1.0.0), with their numbers

Verse text, spans, justifications, `meaning_ar` and the explanation sentences are copied from the record and from the engine output.

#### W1 — production · `tag.moon|lit_emotion.joy|default` · pv:verse:000028

- **Why weak:** literal label whose evidence span is a pronoun phrase; the moon is only in the previous verse (needs outside context).
- **Verse** (ابن المُعتَز): «وَاِنظُر إِلَيهِ كَزَورَقٍ مِن فِضَّةٍ    قَد أَثقَلَتهُ حُمولَةٌ مِن عَنبَرِ»
- **Scores (v1.0.0):** tier 1, E 1.0, V 1.0, T 0.0944, final 0.8189; relation `literal` to `tag.moon`.
- **Label:** span «وَاِنظُر إِلَيهِ» · justification «الضمير يعود على هلال الفطر في البيت السابق»
- **All visual labels of the record:** [('tag.moon', 'literal', 'وَاِنظُر إِلَيهِ'), ('tag.boat_ship', 'symbolic', None)]
- **Query tokens found:** verse [] · meaning ['قمر', 'هلال']
- **meaning_ar:** «انظر إلى هلال عيد الفطر كأنه زورق من فضة أثقلته حمولة من العنبر، يعني الجزء المظلم من القمر.»
- **Explanation shown to the user:** «تُظهر الصورة قمر (أكّدتَها)، والبيت يذكر «وَاِنظُر إِلَيهِ» وصفًا حرفيًا.» / «اخترتَ البهجة والسرور، وهو الإحساس الأساسي لهذا البيت، ودليله «وَاِنظُر إِلَيهِ كَزَورَقٍ مِن فِضَّةٍ».» / «المعنى: انظر إلى هلال عيد الفطر كأنه زورق من فضة أثقلته حمولة من العنبر، يعني الجزء المظلم من القمر.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000028'] → **1.1.0:** ['pv:verse:000028']

#### W2 — production · `tag.bird|lit_emotion.loneliness|default` · pv:verse:000012

- **Why weak:** scene_association that rests on the rest of the poem (the dove is never named in this verse).
- **Verse** (أبو فِراس الحَمَداني): «أَيا جارَتا ما أَنصَفَ الدَهرُ بَينَنا    تَعالَي أُقاسِمكِ الهُمومَ تَعالَي»
- **Scores (v1.0.0):** tier 1, E 1.0, V 0.7, T 0.0577, final 0.7065; relation `scene_association` to `tag.bird`.
- **Label:** span none · justification «الجارة المخاطبة هي الحمامة النائحة في القصيدة»
- **All visual labels of the record:** [('tag.bird', 'scene_association', None)]
- **Query tokens found:** verse [] · meaning ['حمامة']
- **meaning_ar:** «يخاطب الشاعر الحمامة جارته: لم يعدل الدهر بيننا، فأنتِ طليقة وأنا أسير، فتعالي أقاسمكِ همومي.»
- **Explanation shown to the user:** «البيت لا يسمّي طائر، لكن موقفه يقع فيها: الجارة المخاطبة هي الحمامة النائحة في القصيدة.» / «اخترتَ الوحدة والغربة، وهو الإحساس الأساسي لهذا البيت، ودليله «تَعالَي أُقاسِمكِ الهُمومَ تَعالَي».» / «المعنى: يخاطب الشاعر الحمامة جارته: لم يعدل الدهر بيننا، فأنتِ طليقة وأنا أسير، فتعالي أقاسمكِ همومي.» / «النسبة موثقة بأدلة من قاعدة المعرفة التاريخية.»
- **List v1.0.0:** ['pv:verse:000012'] → **1.1.0:** ['pv:verse:000012']

#### W3 — production · `scene_group.heritage|lit_emotion.awe|default` · pv:verse:000017

- **Why weak:** scene_association through a pronoun that refers to a building named elsewhere in the poem.
- **Verse** (البُحتُرِيّ): «لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ»
- **Scores (v1.0.0):** tier 1, E 1.0, V 0.7, T 0.0324, final 0.7015; relation `scene_association` to `scene_group.heritage`.
- **Label:** span none · justification «الضمير يعود على إيوان كسرى الأثري في القصيدة»
- **All visual labels of the record:** [('scene_group.heritage', 'scene_association', None)]
- **Query tokens found:** verse [] · meaning ['ايوان']
- **meaning_ar:** «يبلغ إيوان كسرى من عظمة البناء أن الناظر لا يدري: أبناه الإنس ليسكنه الجن، أم بناه الجن ليسكنه الإنس.»
- **Explanation shown to the user:** «البيت لا يسمّي الآثار والمدن القديمة، لكن موقفه يقع فيها: الضمير يعود على إيوان كسرى الأثري في القصيدة.» / «اخترتَ الجلال والدهشة، وهو الإحساس الأساسي لهذا البيت، ودليله «لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ».» / «المعنى: يبلغ إيوان كسرى من عظمة البناء أن الناظر لا يدري: أبناه الإنس ليسكنه الجن، أم بناه الجن ليسكنه الإنس.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000019', 'pv:verse:000017'] → **1.1.0:** ['pv:verse:000019', 'pv:verse:000017']

#### W4 — production · `scene_group.desert|lit_emotion.loneliness|permissive` · pv:verse:000011

- **Why weak:** emotion-only (tier 3) fill chosen by the verse_id tie-break; the same verse fills many unrelated cells.
- **Verse** (المُتَنَبّي): «بِمَ التَعَلُّلُ لا أَهلٌ وَلا وَطَنُ    وَلا نَديمٌ وَلا كَأسٌ وَلا سَكَنُ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.0, final 0.45; relation `none`.
- **All visual labels of the record:** []
- **Query tokens found:** verse [] · meaning []
- **meaning_ar:** «بأي شيء أتسلى وأصبّر نفسي، ولا أهل حولي ولا وطن، ولا صديق أنادمه ولا كأس ولا من أسكن إليه؟»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الوحدة والغربة، وهو الإحساس الأساسي لهذا البيت، ودليله «لا أَهلٌ وَلا وَطَنُ».» / «المعنى: بأي شيء أتسلى وأصبّر نفسي، ولا أهل حولي ولا وطن، ولا صديق أنادمه ولا كأس ولا من أسكن إليه؟.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000011'] → **1.1.0:** ['pv:verse:000011'] · this verse is the tier-3 fill in 33 production permissive cells

#### W5 — production · `scene_group.sea|lit_emotion.awe|permissive` · pv:verse:000016

- **Why weak:** emotion-only fill that literally depicts another scene (a mountain verse for a sea photo); 1.1.0 picks a scene-neutral verse instead, which avoids the contradiction but is still not a sea verse (none exists in production with this emotion).
- **Verse** (ابن خفاجة): «وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.0, final 0.45; relation `none`.
- **All visual labels of the record:** [('scene_group.mountains', 'literal', 'وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ'), ('scene_group.sky_night', 'literal', 'أَعنانَ السَماءِ')]
- **Query tokens found:** verse [] · meaning []
- **meaning_ar:** «ربّ جبل شامخ عالي القمة، يكاد من شدة ارتفاعه يطاول آفاق السماء بكاهله.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الجلال والدهشة، وهو الإحساس الأساسي لهذا البيت، ودليله «يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ».» / «المعنى: ربّ جبل شامخ عالي القمة، يكاد من شدة ارتفاعه يطاول آفاق السماء بكاهله.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000016'] → **1.1.0:** ['pv:verse:000017'] · this verse is the tier-3 fill in 29 production permissive cells

#### W6 — production · `tag.boat_ship|lit_emotion.longing|permissive` · pv:verse:000008

- **Why weak:** T > 0 from a polysemous query term: فلك (ship) matches فلك (celestial orbit).
- **Verse** (ابن زريق البغدادي): «اِستَودِعُ اللَهَ فِي بَغدادَ لِي قَمَراً    بِالكَرخِ مِن فَلَكِ الأَزرارَ مَطلَعُهُ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.2849, final 0.507; relation `none`.
- **All visual labels of the record:** [('tag.moon', 'symbolic', None)]
- **Query tokens found:** verse ['فلك'] · meaning ['فلك']
- **meaning_ar:** «يودّع الشاعر حبيبًا تركه في بغداد ويستودعه الله، ويشبّهه بقمر يطلع في حي الكرخ، مطلعه من فلك الأزرار، أي إن وجهه يطل من طوق ثوبه.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الحنين والشوق، وهو الإحساس الأساسي لهذا البيت، ودليله «اِستَودِعُ اللَهَ فِي بَغدادَ لِي قَمَراً».» / «المعنى: يودّع الشاعر حبيبًا تركه في بغداد ويستودعه الله، ويشبّهه بقمر يطلع في حي الكرخ، مطلعه من فلك الأزرار، أي إن وجهه يطل من طوق ثوبه.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000008'] → **1.1.0:** ['pv:verse:000008'] · this verse is the tier-3 fill in 4 production permissive cells

#### W7 — production · `scene_group.mountains|lit_emotion.pride|permissive` · pv:verse:000035

- **Why weak:** T > 0 from a polysemous query term: شعب (mountain pass) matches الشعب (the people).
- **Verse** (أبو القاسم الشابي): «إِذا الشَّعْبُ يوماً أرادَ الحياةَ    فلا بُدَّ أنْ يَسْتَجيبَ القدرْ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.2188, final 0.4938; relation `none`.
- **All visual labels of the record:** []
- **Query tokens found:** verse ['شعب'] · meaning ['شعب']
- **meaning_ar:** «إذا عزم الشعب على أن يحيا حرًّا كريمًا فلا بد أن يتحقق له ما أراد.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الفخر والحماسة، وهو الإحساس الأساسي لهذا البيت، ودليله «إِذا الشَّعْبُ يوماً أرادَ الحياةَ».» / «المعنى: إذا عزم الشعب على أن يحيا حرًّا كريمًا فلا بد أن يتحقق له ما أراد.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000035'] → **1.1.0:** ['pv:verse:000035'] · this verse is the tier-3 fill in 2 production permissive cells

#### W8 — production · `scene_group.mountains|lit_emotion.sadness|permissive` · pv:verse:000001

- **Why weak:** T > 0 from meaning_ar only: the proper name صخر (the poet's brother) matches the query term صخر (rock).
- **Verse** (الخَنساء): «يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.0293, final 0.4559; relation `none`.
- **All visual labels of the record:** [('scene_group.sky_night', 'literal', 'طُلوعُ الشَمسِ')]
- **Query tokens found:** verse [] · meaning ['صخر']
- **meaning_ar:** «تقول الخنساء إن طلوع الشمس كل صباح يذكّرها بأخيها صخر، وتعود فتذكره عند غروب كل شمس، فحزنها عليه متصل طوال النهار.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الحزن والأسى، وهو الإحساس الأساسي لهذا البيت، ودليله «يُذَكِّرُني طُلوعُ الشَمسِ صَخراً».» / «المعنى: تقول الخنساء إن طلوع الشمس كل صباح يذكّرها بأخيها صخر، وتعود فتذكره عند غروب كل شمس، فحزنها عليه متصل طوال النهار.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000001'] → **1.1.0:** ['pv:verse:000001'] · this verse is the tier-3 fill in 29 production permissive cells

#### W9 — production · `tag.sea|lit_emotion.loneliness|permissive` · pv:verse:000015

- **Why weak:** label gap: the verse names the sea but is labelled scene_group.sea only, so a tag.sea photo gets it as an emotion-only fill.
- **Verse** (خليل مطران): «شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.4238, final 0.5348; relation `none`.
- **All visual labels of the record:** [('scene_group.sea', 'literal', 'البَحْرِ')]
- **Query tokens found:** verse ['بحر'] · meaning ['بحر']
- **meaning_ar:** «يشكو الشاعر إلى البحر قلق أفكاره واضطرابها، فيرد عليه البحر برياحه العاصفة كأنه يشاركه اضطرابه.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الوحدة والغربة، وهو الإحساس الأساسي لهذا البيت، ودليله «شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي».» / «المعنى: يشكو الشاعر إلى البحر قلق أفكاره واضطرابها، فيرد عليه البحر برياحه العاصفة كأنه يشاركه اضطرابه.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000015'] → **1.1.0:** ['pv:verse:000015'] · this verse is the tier-3 fill in 1 production permissive cells

#### W10 — production · `scene_group.heritage|lit_emotion.longing|permissive` · pv:verse:000010

- **Why weak:** label gap: highest T of the grid (منازل is a heritage query term) but labelled only desert/scene_association.
- **Verse** (المُتَنَبّي): «لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.4822, final 0.5464; relation `none`.
- **All visual labels of the record:** [('scene_group.desert', 'scene_association', None)]
- **Query tokens found:** verse ['منازل'] · meaning ['ديار', 'منازل']
- **meaning_ar:** «يخاطب الشاعر ديار الأحبة: لكِ في القلوب منازل أخرى، فإن كنتِ قد خلوتِ من أهلكِ فإن منازلكِ في القلوب ما زالت عامرة بهم.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الحنين والشوق، وهو الإحساس الأساسي لهذا البيت، ودليله «لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ».» / «المعنى: يخاطب الشاعر ديار الأحبة: لكِ في القلوب منازل أخرى، فإن كنتِ قد خلوتِ من أهلكِ فإن منازلكِ في القلوب ما زالت عامرة بهم.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000010'] → **1.1.0:** ['pv:verse:000010'] · this verse is the tier-3 fill in 2 production permissive cells

#### W11 — development · `scene_group.desert|lit_emotion.pride|default` · pv:verse:000407

- **Why weak:** incidental literal mention: the camels are a figure in a boast about poems, not a desert scene.
- **Verse** (ابن الخياط ): «غَرائِبٌ ما حَدا الرَّكْبُ الرِّكابَ بِها    إِلاّ تَرَنَّحْنّ مِنْ تَرْجِيعهِا طَرَبا»
- **Scores (v1.0.0):** tier 1, E 1.0, V 1.0, T 0.0818, final 0.8164; relation `literal` to `scene_group.desert`.
- **Label:** span «الرِّكابَ» · justification none
- **All visual labels of the record:** [('scene_group.desert', 'literal', 'الرِّكابَ')]
- **Query tokens found:** verse ['ركب'] · meaning ['ابل', 'ركب']
- **meaning_ar:** «يفخر بقصائده النادرة، فما حدا بها ركب الإبل إلا تمايلت الإبل طربًا لترجيعها.»
- **Explanation shown to the user:** «تُظهر الصورة الصحراء والبادية (أكّدتَها)، والبيت يذكر «الرِّكابَ» وصفًا حرفيًا.» / «اخترتَ الفخر والحماسة، وهو الإحساس الأساسي لهذا البيت: يفخر بقصائده التي تطرب الإبل حين يحدو بها الركب.» / «المعنى: يفخر بقصائده النادرة، فما حدا بها ركب الإبل إلا تمايلت الإبل طربًا لترجيعها.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.» / «تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير).»
- **List v1.0.0:** ['pv:verse:000382', 'pv:verse:000373', 'pv:verse:000407'] → **1.1.0:** ['pv:verse:000382', 'pv:verse:000373', 'pv:verse:000407']

#### W12 — development · `scene_group.city|lit_emotion.sadness|default` · pv:verse:000192

- **Why weak:** a place name labelled literal for a visual scene; T = 0 (no query term), tie broken by verse_id.
- **Verse** (جميل صدقي الزهاوي): «بغداد أمست وقد أزرى بها النوب    تبكي على عزها الماضي وتنتحبُ»
- **Scores (v1.0.0):** tier 1, E 1.0, V 1.0, T 0.0, final 0.8; relation `literal` to `scene_group.city`.
- **Label:** span «بغداد» · justification none
- **All visual labels of the record:** [('scene_group.city', 'literal', 'بغداد')]
- **Query tokens found:** verse [] · meaning []
- **meaning_ar:** «يصور الشاعر بغداد وقد أذلّتها المصائب فصارت تبكي عزّها الماضي وتنتحب عليه.»
- **Explanation shown to the user:** «تُظهر الصورة المدينة الحديثة (أكّدتَها)، والبيت يذكر «بغداد» وصفًا حرفيًا.» / «اخترتَ الحزن والأسى، وهو الإحساس الأساسي لهذا البيت، ودليله «تبكي».» / «المعنى: يصور الشاعر بغداد وقد أذلّتها المصائب فصارت تبكي عزّها الماضي وتنتحب عليه.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.» / «تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير).»
- **List v1.0.0:** ['pv:verse:000192', 'pv:verse:000200', 'pv:verse:000358'] → **1.1.0:** ['pv:verse:000192', 'pv:verse:000200', 'pv:verse:000358']

#### W13 — development · `tag.road|lit_emotion.longing|permissive` · pv:verse:000267

- **Why weak:** no road verse exists; the tier-3 fill wins on T from سبيل used abstractly ('is there a way').
- **Verse** (سِبطِ اِبنِ التَعاويذي): «وَهَل مِن سَبيلٍ وَالأَماني تَعِلَّةٌ    إِلى مَعهَدٍ بِالرَملِ طالَ بِهِ عَهدي»
- **Scores (v1.0.0):** tier 3, E 1.0, V 0.0, T 0.2458, final 0.4992; relation `none`.
- **All visual labels of the record:** [('scene_group.desert', 'literal', 'بِالرَملِ')]
- **Query tokens found:** verse ['سبيل'] · meaning ['سبيل']
- **meaning_ar:** «يتساءل هل من سبيل، والأماني مجرد تعلة، إلى العودة إلى منزل قديم بالرمل طال عهده به.»
- **Explanation shown to the user:** «اقتراح بالإحساس وحده دون مطابقة بصرية.» / «اخترتَ الحنين والشوق، وهو الإحساس الأساسي لهذا البيت: يتمنى العودة إلى معهد قديم بالرمل.» / «المعنى: يتساءل هل من سبيل، والأماني مجرد تعلة، إلى العودة إلى منزل قديم بالرمل طال عهده به.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.» / «تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير).»
- **List v1.0.0:** ['pv:verse:000267'] → **1.1.0:** ['pv:verse:000267']

#### W14 — development · `tag.falcon|lit_emotion.sadness|default` · pv:verse:000221

- **Why weak:** the only falcon verse, admitted with the selected emotion as a secondary emotion (E = 0.6).
- **Verse** (ابن حريق البلنسي): «أخَاف حِمَى بَلَنسِيَةٍ وَكَانَت    تَطِيرُ بِهَا البُزاة عَلَى الحَمَامِ»
- **Scores (v1.0.0):** tier 1, E 0.6, V 1.0, T 0.0, final 0.62; relation `literal` to `tag.falcon`.
- **Label:** span «البُزاة» · justification none
- **All visual labels of the record:** [('scene_group.heritage', 'literal', 'بَلَنسِيَةٍ'), ('tag.falcon', 'literal', 'البُزاة'), ('tag.bird', 'literal', 'الحَمَامِ')]
- **Query tokens found:** verse [] · meaning []
- **meaning_ar:** «يخاف الشاعر على حمى بلنسية بعد فقد حاميها، وقد كانت في عهده منيعة تطير فيها البزاة فوق الحمام.»
- **Explanation shown to the user:** «تُظهر الصورة صقر (أكّدتَها)، والبيت يذكر «البُزاة» وصفًا حرفيًا.» / «اخترتَ الحزن والأسى، وهو إحساس ثانوي في هذا البيت.» / «المعنى: يخاف الشاعر على حمى بلنسية بعد فقد حاميها، وقد كانت في عهده منيعة تطير فيها البزاة فوق الحمام.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.» / «تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير).»
- **List v1.0.0:** ['pv:verse:000221'] → **1.1.0:** ['pv:verse:000221']

#### W15 — production · `scene_group.greenery|lit_emotion.serenity|default` · pv:verse:000021

- **Why weak:** duplicate poet: the one-per-poet rule is relaxed because fewer than k candidates exist.
- **Verse** (ابن خفاجة): «وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ»
- **Scores (v1.0.0):** tier 1, E 1.0, V 1.0, T 0.0371, final 0.8074; relation `literal` to `scene_group.greenery`.
- **Label:** span «بِالغُصونِ» · justification none
- **All visual labels of the record:** [('scene_group.greenery', 'literal', 'بِالغُصونِ'), ('scene_group.water', 'literal', 'الماءِ'), ('scene_group.sky_night', 'scene_association', None)]
- **Query tokens found:** verse [] · meaning ['اغصان']
- **meaning_ar:** «يصف الشاعر النهر عند الأصيل: الريح تلاعب الأغصان، وضوء الشمس الذهبي يسيل على صفحة الماء الفضية.»
- **Explanation shown to the user:** «تُظهر الصورة الخضرة والحدائق (أكّدتَها)، والبيت يذكر «بِالغُصونِ» وصفًا حرفيًا.» / «اخترتَ السكينة والطمأنينة، وهو الإحساس الأساسي لهذا البيت، ودليله «ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ».» / «المعنى: يصف الشاعر النهر عند الأصيل: الريح تلاعب الأغصان، وضوء الشمس الذهبي يسيل على صفحة الماء الفضية.» / «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.»
- **List v1.0.0:** ['pv:verse:000022', 'pv:verse:000021'] → **1.1.0:** ['pv:verse:000022', 'pv:verse:000021']


## 8. Side-by-side lists for human judgment

**production · `scene_group.sea|lit_emotion.awe|permissive`**

| option | rank | verse | tier | E | V | T | final | relation | text |
|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 1 | 000016 | 3 | 1.0 | 0.0 | 0.0 | 0.45 | none | وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ |
| `engine_1_1_0` | 1 | 000017 | 3 | 1.0 | 0.0 | 0.0 | 0.45 | none | لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ |
| `drop_T` | 1 | 000016 | 3 | 1.0 | 0.0 | — | 0.5625 | none | وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ |
| `meaning_weight_0` | 1 | 000016 | 3 | 1.0 | 0.0 | 0 | 0.45 | none | وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ |
| `assoc_needs_evidence` | 1 | 000016 | 3 | 1.0 | 0.0 | 0.0 | 0.45 | none | وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ |
| `implied_relations` | 1 | 000016 | 3 | 1.0 | 0.0 | 0.0 | 0.45 | none | وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ |

**production · `scene_group.greenery|lit_emotion.joy|default`**

| option | rank | verse | tier | E | V | T | final | relation | text |
|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 1 | 000029 | 1 | 1.0 | 1.0 | 0.041 | 0.8082 | literal | يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ |
| `v1_0_0` | 2 | 000026 | 1 | 1.0 | 0.7 | 0.218 | 0.7386 | scene_association | أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما |
| `v1_0_0` | 3 | 000027 | 1 | 1.0 | 0.7 | 0.037 | 0.7025 | scene_association | رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ |
| `engine_1_1_0` | 1 | 000029 | 1 | 1.0 | 1.0 | 0.041 | 0.8082 | literal | يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ |
| `engine_1_1_0` | 2 | 000026 | 1 | 1.0 | 0.7 | 0.218 | 0.7386 | scene_association | أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما |
| `engine_1_1_0` | 3 | 000027 | 1 | 1.0 | 0.7 | 0.037 | 0.7025 | scene_association | رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ |
| `drop_T` | 1 | 000029 | 1 | 1.0 | 1.0 | — | 1.0 | literal | يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ |
| `drop_T` | 2 | 000026 | 1 | 1.0 | 0.7 | — | 0.8687 | scene_association | أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما |
| `drop_T` | 3 | 000027 | 1 | 1.0 | 0.7 | — | 0.8687 | scene_association | رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ |
| `meaning_weight_0` | 1 | 000029 | 1 | 1.0 | 1.0 | 0 | 0.8 | literal | يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ |
| `meaning_weight_0` | 2 | 000026 | 1 | 1.0 | 0.7 | 0.25 | 0.745 | scene_association | أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما |
| `meaning_weight_0` | 3 | 000027 | 1 | 1.0 | 0.7 | 0 | 0.695 | scene_association | رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ |
| `assoc_needs_evidence` | 1 | 000029 | 1 | 1.0 | 1.0 | 0.041 | 0.8082 | literal | يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ |
| `assoc_needs_evidence` | 2 | 000022 | 1 | 0.6 | 1.0 | 0.203 | 0.6606 | literal | خَلَعَت عَلَيَّ بِهِ الأَراكَةُ ظِلَّها    وَالغُصنُ يُصغي وَالحَمامُ يُحَدِّثُ |
| `assoc_needs_evidence` | 3 | 000021 | 1 | 0.6 | 1.0 | 0.037 | 0.6274 | literal | وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ |
| `implied_relations` | 1 | 000029 | 1 | 1.0 | 1.0 | 0.041 | 0.8082 | literal | يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ |
| `implied_relations` | 2 | 000026 | 1 | 1.0 | 0.7 | 0.218 | 0.7386 | scene_association | أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما |
| `implied_relations` | 3 | 000027 | 1 | 1.0 | 0.7 | 0.037 | 0.7025 | scene_association | رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ |

**development · `scene_group.desert|lit_emotion.pride|default`**

| option | rank | verse | tier | E | V | T | final | relation | text |
|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 1 | 000382 | 1 | 1.0 | 1.0 | 0.093 | 0.8186 | literal | وَتَنوفَةٍ يَجري السَرابُ بِها    شارَفتَها وَالظِلُّ قَد مَصَحا |
| `v1_0_0` | 2 | 000373 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | تَعَمَّمُوا بإِياةِ الشمسِ واشتملوا    رقراقَ نَهْيِ سرابِ البيدِ والْتَثمُوا |
| `v1_0_0` | 3 | 000407 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | غَرائِبٌ ما حَدا الرَّكْبُ الرِّكابَ بِها    إِلاّ تَرَنَّحْنّ مِنْ تَرْجِيعهِا طَرَبا |
| `engine_1_1_0` | 1 | 000382 | 1 | 1.0 | 1.0 | 0.093 | 0.8186 | literal | وَتَنوفَةٍ يَجري السَرابُ بِها    شارَفتَها وَالظِلُّ قَد مَصَحا |
| `engine_1_1_0` | 2 | 000373 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | تَعَمَّمُوا بإِياةِ الشمسِ واشتملوا    رقراقَ نَهْيِ سرابِ البيدِ والْتَثمُوا |
| `engine_1_1_0` | 3 | 000407 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | غَرائِبٌ ما حَدا الرَّكْبُ الرِّكابَ بِها    إِلاّ تَرَنَّحْنّ مِنْ تَرْجِيعهِا طَرَبا |
| `drop_T` | 1 | 000031 | 1 | 1.0 | 1.0 | — | 1.0 | literal | فَالخَيلُ وَاللَيلُ وَالبَيداءُ تَعرِفُني    وَالسَيفُ وَالرُمحُ وَالقِرطاسُ وَالقَلَمُ |
| `drop_T` | 2 | 000187 | 1 | 1.0 | 1.0 | — | 1.0 | literal | قَليلُ الكَرى ماضٍ عَلى الهَولِ مُقدِمٌ    عَلى اللَّيلِ وَالبَيداءِ وَالحَرِّ وَالبَردِ |
| `drop_T` | 3 | 000251 | 1 | 1.0 | 1.0 | — | 1.0 | literal | وليلة أعملت السرى في مهامه    يطير بها القلب الجبان من الفزع |
| `meaning_weight_0` | 1 | 000382 | 1 | 1.0 | 1.0 | 0.094 | 0.8188 | literal | وَتَنوفَةٍ يَجري السَرابُ بِها    شارَفتَها وَالظِلُّ قَد مَصَحا |
| `meaning_weight_0` | 2 | 000373 | 1 | 1.0 | 1.0 | 0.08 | 0.8161 | literal | تَعَمَّمُوا بإِياةِ الشمسِ واشتملوا    رقراقَ نَهْيِ سرابِ البيدِ والْتَثمُوا |
| `meaning_weight_0` | 3 | 000031 | 1 | 1.0 | 1.0 | 0.07 | 0.8139 | literal | فَالخَيلُ وَاللَيلُ وَالبَيداءُ تَعرِفُني    وَالسَيفُ وَالرُمحُ وَالقِرطاسُ وَالقَلَمُ |
| `assoc_needs_evidence` | 1 | 000382 | 1 | 1.0 | 1.0 | 0.093 | 0.8186 | literal | وَتَنوفَةٍ يَجري السَرابُ بِها    شارَفتَها وَالظِلُّ قَد مَصَحا |
| `assoc_needs_evidence` | 2 | 000373 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | تَعَمَّمُوا بإِياةِ الشمسِ واشتملوا    رقراقَ نَهْيِ سرابِ البيدِ والْتَثمُوا |
| `assoc_needs_evidence` | 3 | 000407 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | غَرائِبٌ ما حَدا الرَّكْبُ الرِّكابَ بِها    إِلاّ تَرَنَّحْنّ مِنْ تَرْجِيعهِا طَرَبا |
| `implied_relations` | 1 | 000382 | 1 | 1.0 | 1.0 | 0.093 | 0.8186 | literal | وَتَنوفَةٍ يَجري السَرابُ بِها    شارَفتَها وَالظِلُّ قَد مَصَحا |
| `implied_relations` | 2 | 000373 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | تَعَمَّمُوا بإِياةِ الشمسِ واشتملوا    رقراقَ نَهْيِ سرابِ البيدِ والْتَثمُوا |
| `implied_relations` | 3 | 000407 | 1 | 1.0 | 1.0 | 0.082 | 0.8164 | literal | غَرائِبٌ ما حَدا الرَّكْبُ الرِّكابَ بِها    إِلاّ تَرَنَّحْنّ مِنْ تَرْجِيعهِا طَرَبا |

**development · `tag.sea|lit_emotion.loneliness|default`**

| option | rank | verse | tier | E | V | T | final | relation | text |
|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 1 | 000460 | 1 | 1.0 | 1.0 | 0.036 | 0.8072 | literal | إن أُمسِ منفرداً فالبحر منفردٌ    والبدرُ مُنفردٌ والسيف منفردُ |
| `v1_0_0` | 2 | 000452 | 1 | 0.6 | 1.0 | 0.183 | 0.6566 | literal | فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ |
| `v1_0_0` | 3 | 000464 | 1 | 0.6 | 1.0 | 0.107 | 0.6414 | literal | ستحملني فوق البحار بواخر    وأَحمل لي فوق البواخر أحزانا |
| `engine_1_1_0` | 1 | 000460 | 1 | 1.0 | 1.0 | 0.036 | 0.8072 | literal | إن أُمسِ منفرداً فالبحر منفردٌ    والبدرُ مُنفردٌ والسيف منفردُ |
| `engine_1_1_0` | 2 | 000452 | 1 | 0.6 | 1.0 | 0.183 | 0.6566 | literal | فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ |
| `engine_1_1_0` | 3 | 000464 | 1 | 0.6 | 1.0 | 0.107 | 0.6414 | literal | ستحملني فوق البحار بواخر    وأَحمل لي فوق البواخر أحزانا |
| `drop_T` | 1 | 000460 | 1 | 1.0 | 1.0 | — | 1.0 | literal | إن أُمسِ منفرداً فالبحر منفردٌ    والبدرُ مُنفردٌ والسيف منفردُ |
| `drop_T` | 2 | 000044 | 1 | 0.6 | 1.0 | — | 0.775 | literal | تائِهاً في الليلِ ما بينَ الصّخور    عندَ شاطي البَحرِ في ضَوءِ القمر |
| `drop_T` | 3 | 000112 | 1 | 0.6 | 1.0 | — | 0.775 | literal | غريب بشط البحر يبكي لشجوه    ولا سكنٌ يشكو إليه ولا أهل |
| `meaning_weight_0` | 1 | 000460 | 1 | 1.0 | 1.0 | 0.037 | 0.8074 | literal | إن أُمسِ منفرداً فالبحر منفردٌ    والبدرُ مُنفردٌ والسيف منفردُ |
| `meaning_weight_0` | 2 | 000452 | 1 | 0.6 | 1.0 | 0.244 | 0.6687 | literal | فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ |
| `meaning_weight_0` | 3 | 000464 | 1 | 0.6 | 1.0 | 0.105 | 0.641 | literal | ستحملني فوق البحار بواخر    وأَحمل لي فوق البواخر أحزانا |
| `assoc_needs_evidence` | 1 | 000460 | 1 | 1.0 | 1.0 | 0.036 | 0.8072 | literal | إن أُمسِ منفرداً فالبحر منفردٌ    والبدرُ مُنفردٌ والسيف منفردُ |
| `assoc_needs_evidence` | 2 | 000452 | 1 | 0.6 | 1.0 | 0.183 | 0.6566 | literal | فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ |
| `assoc_needs_evidence` | 3 | 000464 | 1 | 0.6 | 1.0 | 0.107 | 0.6414 | literal | ستحملني فوق البحار بواخر    وأَحمل لي فوق البواخر أحزانا |
| `implied_relations` | 1 | 000458 | 1 | 1.0 | 1.0 | 0.128 | 0.8256 | literal | عَلى مَ تَجشَّمُ الأَهوالَ فَرداً    بُغبِرِ البِيدِ أَو لُجَجِ البِحارِ |
| `implied_relations` | 2 | 000015 | 1 | 1.0 | 1.0 | 0.06 | 0.812 | literal | شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ |
| `implied_relations` | 3 | 000460 | 1 | 1.0 | 1.0 | 0.036 | 0.8072 | literal | إن أُمسِ منفرداً فالبحر منفردٌ    والبدرُ مُنفردٌ والسيف منفردُ |

**development · `none|lit_emotion.serenity|default`**

| option | rank | verse | tier | E | V | T | final | relation | text |
|---|---|---|---|---|---|---|---|---|---|
| `v1_0_0` | 1 | 000021 | 3 | 1.0 | — | — | 1.0 | none | وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ |
| `engine_1_1_0` | 1 | 000725 | 3 | 1.0 | — | — | 1.0 | none | ترى رهبانَهم راضين طوعاً    بذُلِّ الفقر والفقرُ اختيار |
| `drop_T` | 1 | 000021 | 3 | 1.0 | — | — | 1.0 | none | وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ |
| `meaning_weight_0` | 1 | 000021 | 3 | 1.0 | — | 0 | 0.6923 | none | وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ |
| `assoc_needs_evidence` | 1 | 000021 | 3 | 1.0 | — | — | 1.0 | none | وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ |
| `implied_relations` | 1 | 000021 | 3 | 1.0 | — | — | 1.0 | none | وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ |


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
