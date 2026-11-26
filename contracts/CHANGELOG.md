# Contracts changelog

## 1.0.0 — 2026-11-25 (draft, pending sign-off)

- **Taxonomy v1** (`contracts/taxonomy/taxonomy_v1.json`) has 102 labels in 8 layers:

  | Layer | Labels |
  |---|---|
  | scenes | 17 |
  | scene groups | 9 |
  | tags | 34 (13 exposed) |
  | image emotions | 8 |
  | literary emotions | 8 |
  | relations | 6 |
  | concepts | 11 |
  | genres | 9 |

  - The pilot covers 5 scene groups × 5 literary emotions.
  - The image-to-literary suggestion map is `mapping_v1`.
  - Scene and tag ids, Places365 lists and Arabic scene and tag names are imported unchanged from the visual module.
  - Class orders are verified against `scene_head_clip.npz`, `tag_heads.npz` and Renad's `model_config.json`.
- **Contracts and tooling:**
  - nine contracts with standard-library validators, 16 error codes and a generated field reference (`CONTRACT_FIELDS.md`);
  - 20 poetry fixtures built from verbatim APCD rows;
  - 27 invalid fixtures, covering every error code and every contract;
  - a deterministic fixture builder.
- **Deliberate differences from the planning handoff:**
  1. `display_allowed` is derived by `display_allowed(record, mode)` and is not stored in records, which removes a source of contradiction.
  2. Four error codes were added: `E_FORMAT`, `E_RANGE`, `E_UNKNOWN_FIELD` and `E_FIXTURE_IN_PRODUCTION`.
  3. PV-Test emotion labels use `emotion_label_status = labeled_set` with acceptable sets instead of one label.
  4. Relations, concepts and genres are referenced by full taxonomy ids (`relation.literal`, ...).
  5. "evoked ⇒ uncertainty ≥ medium" is not enforced, because an evoked emotion can be certain. The annotation guide gives advice instead.
  6. `poem_id` (history link) is allowed only for `source_verified` records. `poet_id` stays null for `apcd_only` fixtures.
  7. Records may carry `"fixture": true`, and the validator rejects fixture data in production mode.
  8. Image profiles carry no model scores, only user selections and a reference to the inference output.

### Draft amendment — 2026-11-25 (owner request: Mohammed's development package)

Field names, class ids and schema versions are unchanged.

- **Development mode:** a third mode, `development`, for building the retrieval engine on AI drafts before human review.
  - `display_allowed(record, "development")` also admits unreviewed, non-disputed records whose text is verified.
  - Production is unchanged.
  - Synthetic fixtures stay limited to fixture mode.
- **Corpus mode:** `corpus_mode` in `retrieval_query` and `recommendations` accepts `development`. Production mode rejects development and fixture corpora with `E_FIXTURE_IN_PRODUCTION`.
- **Disclosure:** recommendations over a development corpus must include the template id `T_DRAFT_DISCLOSURE` in every item.
- **Portability:** no machine-specific absolute paths remain in `contracts/`.
  - The APCD zip is found through `PV_APCD_ZIP`, `external/apcd/` or `external/poetry_vision_old/`.
  - The model-card fixture names reused head files relative to the visual module.
- **New invalid fixtures:**
  - `recommendations/E_STATUS_CONFLICT__development_without_draft_disclosure.json`
  - `retrieval_query/E_FIXTURE_IN_PRODUCTION__production_with_development_corpus.json`

### Sign-off (required before 1.0.0 is frozen)

- [ ] Shaden: `image_manifest`
- [ ] Mohammed: `retrieval_query`, `recommendations`, and the consumer view of `image_profile` and `poetry_record`
- [ ] Omar: the remaining contracts (owner)
