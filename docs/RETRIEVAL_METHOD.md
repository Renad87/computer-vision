# Poetry Vision retrieval method v1 (provisional)

Status: part of the approved architecture (2026-11-25).

- The weights, the relevance weights ρ and every threshold below are **provisional hypotheses**. They must be evaluated, and may only be tuned on development data (PV-Dev and the development corpus), never on PV-Test.
- Contracts: `contracts/CONTRACTS.md`. The `recommendations` validator recomputes the score formula and checks the ordering, status and disclosure rules below.

## 0. Inputs and mode

- `image_profile` (what the user confirmed), `retrieval_query` (method, weights, k, tiers, diversity), and the corpus as a list of `poetry_record` dicts.
- **Active mode:** `query.corpus_mode`. Candidates are the records with `display_allowed(record, query["corpus_mode"])` (`contracts/validate.py`):

  | Mode | Candidates | Purpose |
  |---|---|---|
  | `production` | human-reviewed records only | the real application |
  | `development` | also AI drafts pending review | explicit opt-in for engine development; every item must carry `T_DRAFT_DISCLOSURE` |
  | `fixture` | also synthetic fixture records | tests |

- No runtime LLM, no RAG, no vector database. Python standard library only.

## 1. Arabic preprocessing (retrieval representation only)

`text_original` is never modified. Build a separate representation:

- **N0:**
  - Unicode NFC.
  - Remove diacritics U+064B–U+0652 and U+0670, and tatweel U+0640.
  - Fold أ إ آ ٱ → ا. Keep ى and ة: folding them merges «ليلى» with «ليلي», and «حياة» with «حياه».
  - Remove punctuation. The hemistich gap (4 spaces in APCD) becomes one space.
- **N1** = N0 plus stripping the definite article and the article with an attached particle: ال، وال، بال، كال، فال، لل. Strip only when at least 3 letters remain.
- **N2** = N1 plus stripping the single-letter proclitics و ف ب ك ل, also only when at least 3 letters remain. A protected list is required:
  - taxonomy query terms;
  - «فراق»، «وداع»، «وادي»، «بكاء» (otherwise «راق»، «داع»، «ادي»، «كاء»).
- **Stop words:** a small list of particles. Negations لا، ما، لم، لن، ليس are always kept.
- **Not used:** root stemming (ISRI conflates «مكتبة/كاتب/كتب») and lemmatization.
- **Default:** N1. Compare N0, N1 and N2 on development examples and document the evidence.

## 2. Text similarity T (TF-IDF, cosine)

- **Spaces:** two vector spaces over the candidate records, verse (`text_original` after preprocessing) and meaning (`meaning_ar` after preprocessing).
- **Production weighting:** `tf = raw count`, `idf(t) = ln((1 + N) / (1 + df(t))) + 1`, L2 normalization. The cosine lies in [0, 1].
- **Lecture baseline (B1-lecture, educational):** `TF = count / total terms`, `IDF = log(N / (1 + df))`, exactly as in Unit8_Part2.
  - Report the terms with IDF ≤ 0; this happens when df ≥ N − 1.
  - Dividing TF by the document length does not change the cosine. Only IDF differs from production.
- **Query:**
  - `query_terms_ar` of the confirmed items from the taxonomy, weighted focus 2, primary 1, secondary 0.5;
  - `concept_id` terms weighted 0.5;
  - the same preprocessing as documents;
  - no emotion terms, because emotion is handled by E.
- **Combination:** `T = 0.7 · cos(q, verse) + 0.3 · cos(q, meaning)`. Without a meaning, `T = cos(q, verse)`. With an empty query, `T = null`.
- **No query-level min-max normalization.** T keeps the cosine scale.

## 3. Label matching (E and V)

- **E (emotion compatibility):**
  - E = 1.0 if `selected_lit_emotion` is a primary emotion of the record, 0.6 if it is a secondary one.
  - Otherwise the record is **not eligible**.
  - `emotion_status` neutral, ambiguous or not_annotated means not eligible. That is missing evidence, not a conflict.
- **Second emotion:** `secondary_lit_emotion` is a ranking preference only (section 5). It never replaces the selected emotion.
- **ρ(v, x)**, the relation weight between record v and confirmed item x, from `taxonomy.relation_weights`:

  | Relation | ρ |
  |---|---|
  | literal | 1.0 |
  | scene_association | 0.7 |
  | symbolic | 0.4 if `symbolic_allowed`, else 0 |
  | negated, hypothetical, ambiguous, no association | 0 |

- **V (visual compatibility):** `V = Σ_x w_x · ρ(v, x) / Σ_x w_x` over the confirmed items, with w = 2 (focus), 1 (primary), 0.5 (secondary). No confirmed items gives `V = null`.

## 4. Eligibility tiers

- **Anchors:** `{focus}` if a focus is set, otherwise every confirmed item.

| Tier | Condition |
|---|---|
| 1 | E-eligible and a literal or scene_association relation with an anchor; requires 1 ∈ `tiers_enabled` |
| 2 | E-eligible, `symbolic_allowed`, a symbolic relation with an anchor, not tier 1; requires 2 ∈ `tiers_enabled` |
| 3 | E-eligible, `emotion_only_allowed` and 3 ∈ `tiers_enabled`, not tier 1 or 2. **At most one** tier-3 item is returned |

Text similarity alone never establishes a visual relation.

## 5. Score and order

```
Score = 0.45·E + 0.35·V + 0.20·T          (weights come from query.weights; semantic S has weight 0 unless Word2Vec is enabled)
final = Σ w_i · s_i / Σ w_i over the non-null components   (null components are dropped, weights renormalized)
```

- **Order:** tier ascending, then `final` descending, then whether the secondary emotion matches (descending), then `verse_id` ascending. The result must be deterministic.
- **Tier-3 tie-break (engine 1.1.0, 2026-11-26):** within tier 3 only, after secondary-emotion match and before `verse_id`, a verse that does not literally depict an unconfirmed scene group ranks first (`retrieval.labels.scene_conflict`). Scores, tiers, eligibility and explanations are unchanged. Evidence: `evaluation/retrieval/quality_diagnosis/REPORT.md`. Rollback: `backups/retrieval_v1_0_0/`.
- **Minimum score:** `min_score` (θ) is 0 (disabled) in v1. Tune it only on development data.

## 6. Diversity and duplicate removal

1. Unique `verse_id`. Records with the same `text_sha256` are duplicates.
2. One verse per poem. The poem key is `poem_id` when set, otherwise (`poet.name_apcd`, `source.meter_apcd`, `source.rhyme_apcd`) as an approximation.
3. One verse per poet, unless fewer than k results would remain; then relax this rule only.
4. Skip a verse whose TF-IDF cosine to an already selected verse exceeds `diversity.near_dup_cosine` (0.8).

## 7. Abstention

`status = abstained`, `items = []`, with the first matching reason:

| Reason | When |
|---|---|
| `empty_corpus` | no displayable record in the active mode (`coverage_gap` null) |
| `no_emotion_match` | no displayable record carries the selected emotion |
| `cell_not_covered` | no displayable record has a qualifying relation (literal or scene_association, or symbolic when allowed) with any anchor |
| `no_visual_match_emotion_only_off` | the anchors are covered, but not together with the selected emotion, and emotion-only is off |
| `diversity_exhausted` | candidates existed, but all were removed by section 6 |

- `coverage_gap = {visual_targets: anchors, lit_emotion: selected}`; log it so the corpus can be expanded.
- Status values: `ok` (exactly k items), `partial` (1 to k−1), `abstained` (0).
- Never fall back to unreviewed records outside the active mode, to APCD, or to generated text.

## 8. Deterministic explanations

Explanations are built from template ids and Arabic sentences filled only from record fields (spans, justifications, `meaning_ar`, attribution). The evidence spans are copied from the record.

| Template id | Suggested sentence |
|---|---|
| T_SCENE_LITERAL | «تُظهر الصورة {group} (أكّدتَها)، والبيت يذكر «{span}» وصفًا حرفيًا.» |
| T_SCENE_ASSOC | «البيت لا يسمّي {group}، لكن موقفه يقع فيها: {justification}.» |
| T_SYMBOLIC | «يرد {target} في البيت رمزًا أو تشبيهًا: {justification}.» |
| T_EMOTION_PRIMARY | «اخترتَ {emotion}، وهو الإحساس الأساسي لهذا البيت، ودليله «{span}».» |
| T_EMOTION_SECONDARY | «اخترتَ {emotion}، وهو إحساس ثانوي في هذا البيت.» |
| T_MEANING | «المعنى: {meaning}» |
| T_TIER_DISCLOSURE | tier 2: «اقتراح رمزي لا يطابق مشهد الصورة حرفيًا.» — tier 3: «اقتراح بالإحساس وحده دون مطابقة بصرية.» |
| T_ATTRIBUTION | «النسبة موثقة بأدلة من قاعدة المعرفة التاريخية.» أو «النسبة كما في APCD، ولم يُتحقق منها بمصدر مستقل.» |
| T_DRAFT_DISCLOSURE | required in development mode: «تنبيه: تسميات هذا البيت مسودة آلية لم يراجعها إنسان بعد (وضع التطوير).» |

## 9. Baselines

**Experiment A** uses the same corpus and the same profiles for every method:

| Code | `method` | Description |
|---|---|---|
| B1-lecture | `tfidf_lecture` | TF-IDF with the lecture formula |
| B1 | `tfidf` | production TF-IDF |
| B3 | `labels_exact` | exact label match |
| B4 | `labels_weighted` | E and V with tiers, no T |
| B5 | `hybrid` | the method above |
| B5-noTier | `hybrid_no_tier` | the same Score with no eligibility tiers |
| B2 (optional) | `w2v` | Word2Vec |
| B7 (optional, Omar's machine) | `bge_m3_baseline` | BGE-M3 |

**Experiment B** compares the legacy engine on its own corpus with the new system. It is a system-level comparison, not a method baseline.

## 10. Evaluation

- **Metrics:**
  - P@3 (denominator 3) and precision among returned;
  - nDCG@3 with pooled blind judgments (document the incomplete-judgment limits);
  - emotion relevance and visual relevance;
  - coverage, abstention rate and abstention correctness;
  - explanation correctness;
  - latency p50/p95 (target p95 < 100 ms for ≤ 1,000 records).
- **Statistics:** paired bootstrap over queries, 1,000 resamples with a fixed seed. Say "better" only when the confidence interval excludes zero.
- Jaccard between emotions is a diagnostic only.
- No metric is reported before the human rating sheets are complete. Never tune on PV-Test.

## 11. Word2Vec (optional)

- **Setup:** skip-gram on the full APCD through a streaming reader with N1, dim 100, window 5, min_count 5, 5 epochs. Measure time and memory.
- **Restrictions:**
  - never trained on the curated corpus;
  - never used for emotion polarity;
  - dropped if it does not improve development relevance.
- **Approval:** `gensim` needs the owner's approval before installation.
