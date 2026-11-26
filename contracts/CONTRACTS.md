# Poetry Vision data contracts v1.0.0

عقود البيانات التسعة المشتركة بين أعضاء الفريق. الـvalidator في `contracts/validate.py` هو المرجع القابل للتنفيذ. جدول الحقول الكامل مولَّد آليًا في [CONTRACT_FIELDS.md](CONTRACT_FIELDS.md)، والأمثلة هي ملفات الـfixtures نفسها.

- Status: drafted 2026-11-25 (M1). Frozen as 1.0.0 once the consumers sign off in `CHANGELOG.md`.
- Python standard library only. Validate with:

```bash
python3 -m contracts.validate <contract> <file> [--mode production|fixture] [--apcd-zip PATH] [--corpus PATH]
```

Output: one line per issue, `CODE<TAB>path<TAB>message`; JSONL paths start with the line number (`L3:`). Exit code 0 = valid, 1 = invalid, 2 = usage or IO error. Python API: `validate_file`, `validate_document`, `validate_records`, `display_allowed`.

## Ownership

| Contract | Format | Owner | Producer | Consumers |
|---|---|---|---|---|
| `taxonomy` | JSON (`contracts/taxonomy/taxonomy_v1.json`) | Omar | contracts | everyone |
| `image_manifest` | JSONL | Shaden | data_preparation | vision_model, evaluation |
| `model_card` | JSON | Omar | vision_model | backend, evaluation |
| `inference_output` | JSON | Omar | vision_model / backend | frontend, profile builder |
| `image_profile` | JSON | Omar | backend (user choices) | retrieval |
| `poetry_record` | JSONL | Omar | poetry_corpus | retrieval, evaluation |
| `retrieval_query` | JSON | Mohammed | backend / retrieval | retrieval |
| `recommendations` | JSON | Mohammed | retrieval | backend, frontend, evaluation |
| `evaluation_record` | JSONL | Omar (vision, annotation, e2e), Mohammed (retrieval) | evaluation | reports |

## Shared conventions

- **Versions:** every document or record carries `schema_version` and `taxonomy_version` (semver).
  - Only schema major 1 is supported.
  - The taxonomy major must match the loaded taxonomy (`E_VERSION`).
- **Strict schemas:** unknown fields → `E_UNKNOWN_FIELD`. Missing required fields or empty strings → `E_REQUIRED`.
- **Taxonomy ids:** always `<layer>.<name>` (for example `relation.literal`, `scene_group.desert`).
  - Unknown ids and ids from the wrong layer → `E_UNKNOWN_ID`.
  - Where a field accepts exposed tags only, the 21 unexposed tags are rejected.
- **Stable identifiers:**
  - `image_sha256` is the full 64-hex digest. `image_id` is `img:<source_dataset>:<source_image_id>`.
  - `verse_id` is `pv:verse:NNNNNN` and is never reused. `profile_id`, `query_id` and `eval_id` are UUID4.
- **APCD rows:** `apcd_row` is the 0-based data-row index of the APCD CSV, header excluded (same convention as `scripts/locate_verses.py` in the original project).
  - `contracts/apcd.py` reads rows verbatim.
  - `text_original` is the `البيت` column exactly, diacritics included. It is never retyped or corrected; use `text_note`.
- **Evidence spans:** `{start, end, text}` with 0-based Unicode code-point offsets on `text_original`; `end` is exclusive.
  - Rule: `text_original[start:end] == text`, otherwise `E_SPAN`.
  - Diacritics are separate code points and count.
- **Missing vs negative:** `unavailable`, `unmapped`, `excluded_ood`, `not_annotated`, `neutral` and `ambiguous` are distinct statuses. A missing annotation is never read as "absent".
- **Provenance types never mix:**
  - model scores (`score`, `decision_score`, with a `calibrated` flag);
  - user selections (`user_selection`: `focus | primary | secondary`, no number);
  - review status (`review.status` + reviewer ids);
  - annotator uncertainty (`low | medium | high`).

  A user-confirmed scene is a selection, not a probability of 1.0.
- **Modes:** `production` (default), `development` and `fixture`.
  - `production`: only human-reviewed records are displayable. Fixture data, and queries or results over a `fixture` or `development` corpus, are rejected (`E_FIXTURE_IN_PRODUCTION`).
  - `development`: an explicit opt-in for building the engine before reviews exist. Unreviewed records (AI drafts pending review) also become displayable. Every recommended item must disclose this with the template id `T_DRAFT_DISCLOSURE`. Never shown to users as approved results.
  - `fixture`: synthetic test data. Records may carry `"fixture": true`. Fixture verses use verbatim APCD text, but their labels, scores and ratings are synthetic.

## Contract rules (cross-field)

### taxonomy
- **Labels and layers:**
  - Every label has `id, layer, name_ar, name_en, definition_ar, include_ar, exclude_ar, examples, provenance`.
  - The id prefix equals the layer. Ids are unique.
  - The 8 layers are exactly `scene, scene_group, tag, img_emotion, lit_emotion, relation, concept, genre`.
- **Query terms:** scene groups and exposed tags need `query_terms_ar`.
- **Examples:** descriptions or verified `apcd_row` references, never typed verses.
- **Model outputs:** `model_outputs.{scene,img_emotion,tag}.class_order` has 17/8/34 ids, covers its layer exactly, and aligns with `external_names` (the class names inside the reused heads). `tag.exposed` ⊂ tag class order.
- **Scene groups:** `scene_groups` defines every group. A scene belongs to at most one group, and `scene.other` to none.
- **Suggestions:** `suggestion_map` maps image emotions to literary emotions once per source and never to `user_only_lit_emotions`. These are suggestions, not predictions.
- **Relation weights:** `relation_weights` defines every relation.
- **Places365 mapping:** `places365_mapping` has one list per scene (except `scene.other`) plus `background_for_scene_other` and `ood_excluded`, and no category appears twice.
  - Name normalization: lower-case, strip a leading `/x/`, `-` → `/`, space → `_`.

### image_manifest
- **Scene label:** `scene_label` set ⇔ `scene_label_status = labeled` ⇔ `scene_label_source` set.
  - When `scene_source_raw` is present and the source is not `human_annotation`, (label, status) must equal the taxonomy mapping of the raw name:
    - scene list → `scene.*`;
    - background → `scene.other`;
    - OOD list → `excluded_ood`;
    - anything else → `unmapped`.
  - `split = ood_test` ⇒ `excluded_ood`.
- **Emotion label:**
  - `labeled` needs a label and a source.
  - `labeled_set` (PV-Test) needs `acceptable_img_emotions`, source `human_annotation` and no single label.
  - `unavailable` carries nothing.
- **PV-Test:** `pv_test` ⇒ split `test` and `split_origin = independent_test`. `acceptable_*` and `scene_ambiguous` exist only on `pv_test`.
- **Training rows:** at least one labeled task per training row.
- **Collection:**
  - unique `image_id`;
  - identical content twice → `E_DUP_ID` in the same split, `E_SPLIT_LEAK` across splits;
  - a `near_dup_group` spanning two splits → `E_SPLIT_LEAK`.
  - Quarantined images are listed in `datasets/reports/quarantine.jsonl`, not in the manifest.

### model_card
- **Heads:** names are unique; scene/emotion/tags output `scene`/`img_emotion`/`tag` with softmax/softmax/linear_threshold.
  - `output_ids` equal the taxonomy class order.
  - `out_dim = len(output_ids)`; `params = in_dim·out_dim + out_dim`.
  - `in_dim` equals `backbone.embedding_dim` (input `embedding`) or `adapter.out_dim` (input `adapter`).
  - `calibrated` ⇔ temperature set.
- **Tag head:** lists `exposed_ids` equal to the taxonomy exposed tags. Every exposed tag has a threshold.
- **Scene threshold:** `scene_supported` uses the rule "max in-taxonomy probability of the 17-way softmax (other excluded, not renormalized)". `after_temperature` requires a calibrated scene head.
- **Released cards:**
  - trained heads have `trained_on`;
  - softmax heads are calibrated;
  - the threshold is set (and re-derived after temperature when the scene head is calibrated);
  - `metrics` is non-empty, each with `run_id`.

### inference_output
- **Status:** `status = error` ⇔ `error` set and all prediction blocks null.
- **Scene:**
  - predictions cover the 17 classes once and sum to 1 (±1e-3);
  - `top1_score` is the best in-taxonomy score and `margin` = top1 − second;
  - `supported` = `top1_score ≥ supported_threshold`;
  - `status = unsupported` ⇔ not supported.
- **Scene groups:** all 9 groups; each score is the sum of its member scene scores (tags are reported separately).
- **Emotion:**
  - 8 classes summing to 1;
  - `margin` = top1 − top2;
  - `ambiguous` ⇔ margin < `ambiguity_margin`;
  - `entropy` in nats.
- **Tags:** every exposed tag exactly once; `present = decision_score ≥ threshold`.
- **Suggestions:** `suggested_lit_emotions` pairs must exist in `suggestion_map`, with `basis = mapping_v1`, and carry no score.

### image_profile
- **Items:**
  - confirmed items are `scene_group.*` or exposed tags, each once;
  - at most one `focus`;
  - no items ⇒ `emotion_only_allowed = true`.
- **Emotions:** `selected_lit_emotion` is required and `secondary_lit_emotion` differs from it.
- **Origin:** `origin = synthetic_query` ⇔ `source_inference = null`.

### poetry_record
- **Display rule:** `display_allowed` is derived by `contracts.validate.display_allowed(record, mode)` and must not be stored (`E_DISPLAY_RULE`). A record is displayable only if all of the following hold:
  - method `human` or `ai_draft_human_reviewed`;
  - review `reviewed | double_reviewed | adjudicated`;
  - attribution not `disputed`;
  - `text_verification.method = apcd_row_exact`;
  - intact `text_sha256`.

  In development mode, unreviewed records (for example `ai_draft` + `not_reviewed`) also qualify. In fixture mode, synthetic fixtures also qualify. Disputed attribution or unverified text never qualifies.
- **Text:**
  - `apcd_row ≥ 0` (`E_APCD_ROW`);
  - `text_sha256 = sha256(text_original)` (`E_APCD_TEXT`).
  - With `--apcd-zip`, the row must exist, and the text, hemistichs, poet, era, diwan, meter and rhyme must equal APCD.
- **Visual associations:**
  - targets are unique;
  - `literal`, `negated` and `hypothetical` need an evidence span;
  - `scene_association`, `symbolic` and `ambiguous` need `justification_ar` (≤ 15 words).
- **Emotions:**
  - `expressed` needs an evidence span; `evoked` needs `justification_ar` (≤ 15 words);
  - at most 2 primary and 2 secondary;
  - no id twice.
- **Emotion status:**
  - `has_emotion` ⇒ 1–2 primary;
  - `neutral | ambiguous | not_annotated` ⇒ no emotions;
  - `not_annotated` ⇔ `dimension_status.emotion = not_annotated`;
  - a `not_annotated` dimension has an empty field.
- **Attribution:** `source_verified` ⇒ `evidence_ids`. `poem_id` (history link) only for `source_verified`.
- **Annotation and review:**
  - AI drafts name `model_id`;
  - a reviewed AI draft is `ai_draft_human_reviewed`;
  - `synthetic_fixture` method ⇔ review status `synthetic_fixture` ⇔ `fixture: true`;
  - `reviewed` needs a reviewer other than the annotator; `double_reviewed` two; `adjudicated` an `adjudicate` decision.
- **Collection:** unique `verse_id` and `apcd_row`.

### retrieval_query
- **Weights:** non-negative and sum to 1.
- **Tiers:** unique.
- **Corpus mode:** `corpus_mode` is `production`, `development` or `fixture`. Production mode cannot use a `fixture` or `development` corpus.
- **`method` values and baselines:**
  - `tfidf_lecture` = B1-lecture, `tfidf` = B1, `w2v` = B2;
  - `labels_exact` = B3, `labels_weighted` = B4;
  - `hybrid` = B5, `hybrid_no_tier` = B5-noTier;
  - `bge_m3_baseline` = B7.
  - The legacy engine (S0) is a system-level comparison, not a method here.

### recommendations
- **Status:**
  - `abstained` ⇔ no items ⇔ `abstention` set;
  - `ok` returns exactly `k` items; `partial` returns 1 to k−1.
- **Ordering:**
  - ranks 1..n;
  - unique verses;
  - order by tier, then `final` descending;
  - at most one tier-3 (emotion-only) item.
- **Scores:**
  - `final` = Σ wᵢ·sᵢ / Σ wᵢ over the non-null components (null components are dropped and the weights renormalized; no min-max);
  - emotion score 1.0 for a primary match, 0.6 for a secondary match.
- **Explanation:** one sentence per template id; spans valid on the item text.
- **Development corpus:** when `corpus_mode = development`, every item's `template_ids` include `T_DRAFT_DISCLOSURE`, a sentence saying the labels are unreviewed drafts. Production mode rejects development and fixture corpora.
- **With `--corpus`:**
  - every verse exists;
  - text, row, poet, era, attribution and review status match the corpus record;
  - the verse is displayable in the declared `corpus_mode` (`E_DISPLAY_RULE`).
- **Fixture note:** the recommendation fixtures leave `text` and `semantic` null. The real engine fills `text` with the smoothed TF-IDF cosine.

### evaluation_record
- **Retrieval and e2e judgments:**
  - blind;
  - need `visual_fit`, `emotion_fit` and `overall` (0–3);
  - e2e also needs `explanation_correct` and `text_authentic`.
- **Vision and annotation judgments:** need `judgment`.
- **Collection:** unique `eval_id`, and one judgment per (layer, rater, item, method).
- **Honesty:** metrics are computed only from completed sheets; synthetic fixtures never enter reports.

## Error codes

| Code | Meaning |
|---|---|
| `E_REQUIRED` | required field missing or empty |
| `E_TYPE` | wrong JSON type, null not allowed, or unreadable JSON |
| `E_ENUM` | value outside the allowed set |
| `E_FORMAT` | sha256, uuid4, id, path or date format wrong |
| `E_RANGE` | number, length, word count, item count or weight sum out of range |
| `E_UNKNOWN_FIELD` | field not defined by the contract |
| `E_UNKNOWN_ID` | taxonomy id unknown, wrong layer or unexposed tag; verse not in corpus |
| `E_VERSION` | version invalid or unsupported |
| `E_SPAN` | evidence span does not match the text |
| `E_APCD_ROW` | row number negative or absent from APCD |
| `E_APCD_TEXT` | text or metadata differs from APCD/corpus, or text hash mismatch |
| `E_DISPLAY_RULE` | derived display flag stored, or a non-displayable verse returned |
| `E_STATUS_CONFLICT` | fields contradict each other |
| `E_DUP_ID` | duplicate identifier |
| `E_SPLIT_LEAK` | same or near-duplicate image in two splits |
| `E_FIXTURE_IN_PRODUCTION` | fixture data, or a fixture/development corpus, in production mode |

## Fixtures

- **Location:** `contracts/fixtures/valid/<contract>/` pass in fixture mode. Each file in `contracts/fixtures/invalid/<contract>/<CODE>__<case>.*` fails with `<CODE>`.
  - Files whose name contains `__production` are checked in production mode.
- **Rebuilding:** all fixtures are generated by `python3 -m contracts.tools.build_fixtures`, which reads the 20 verses from APCD rows located in the original project's `data/poems_reference.json` plus two rows found by an APCD search.
  - A test fails if a fixture file differs from a fresh build.
- **Poetry fixtures:** `poetry_fixtures_v1.jsonl` covers:
  - all six relations;
  - expressed and evoked emotions;
  - the statuses `has_emotion`, `neutral`, `ambiguous` and `not_annotated`;
  - `source_verified` and `apcd_only` attribution;
  - two `text_note` cases (APCD quirks kept verbatim);
  - repeated poems and poets for diversity tests.
- **Profiles:** literal desert, association greenery, symbolic allowed and denied (sea), emotion-only, focus, and tag-only (stars, which only appear negated, so retrieval must abstain).

## Change control

1. The contract owner proposes the change.
2. The consumers approve it.
3. The version is bumped (semver):
   - patch: wording;
   - minor: new optional field or label;
   - major: anything that breaks existing files.
4. Regenerate fixtures and `CONTRACT_FIELDS.md`, run the tests, and record the change in `CHANGELOG.md`.
