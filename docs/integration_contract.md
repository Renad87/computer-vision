# Integration Contract — DRAFT v0

> **Status:** proposal for INT-01. Not binding until all four members approve their own section in the INT-01 issue.
> Change a function signature or a shared name only through a PR reviewed by the affected owners.

## 1. Shared rules

- Every module is a plain importable Python function that returns JSON-serialisable dicts. No module depends on the backend or frontend.
- Arabic display text in `*_ar` fields; stable machine keys in English (`label`, `poem_id`, ...).
- Never return invented values. If something is unknown, return `null` / an empty list plus a reason, not a guess.
- Every model output carries `model_version`; every historical claim carries `source_ids`.
- Errors: raise `ValueError` for bad input inside modules; the backend converts to
  `{"error": {"code": "<snake_case>", "message_ar": "..."}}` with an HTTP 4xx/5xx status.

## 2. Module functions

### 2.1 `analyze_visual(image_bytes) -> dict` — owner: Shaden (`ml/visual/`)

```json
{
  "scenes":        [{"label": "sea", "label_ar": "بحر", "score": 0.81, "source": "trained"}],
  "objects":       [{"label": "bird", "label_ar": "طائر", "score": 0.44, "source": "zero_shot"}],
  "attributes":    {"time_of_day": "sunset", "lighting": "dim"},
  "focus_candidates": [{"id": "f1", "label_ar": "البحر", "kind": "scene"},
                       {"id": "f2", "label_ar": "الوحدة", "kind": "concept"}],
  "interpretations": [{"label_ar": "الوحدة", "score": 0.32, "source": "zero_shot", "is_interpretation": true}],
  "image_embedding": [/* optional CLIP embedding, shareable with analyze_emotions */],
  "embedding_model": "openai/clip-vit-base-patch32",
  "model_version": "..."
}
```
Visible content (`scenes`, `objects`) and interpretations are kept separate.

### 2.2 `analyze_emotions(image_bytes, clip_embedding=None, embedding_model_name=None) -> dict` — owner: Renad (`ml/emotion/`)

```json
{
  "emotion_suggestions": [
    {"label": "contentment", "label_ar": "السكينة والرضا", "project_emotion": "السكينة",
     "score": 0.52, "source": "trained"},
    {"label": "nostalgia", "label_ar": "الحنين", "project_emotion": "الحنين",
     "score": 0.18, "source": "zero_shot_unvalidated"}
  ],
  "visual_affective_attributes": {"brightness": 0.41, "warmth": 0.12, "descriptors_ar": {"tone": "دافئة"}},
  "uncertainty": {"top1_prob": 0.52, "margin_top1_top2": 0.21, "is_ambiguous": false},
  "model_version": "...",
  "all_trained_scores": {"amusement": 0.03, "...": 0.0},
  "disclaimer": "..."
}
```
`source: "trained"` = class learned from labelled data (EmoSet). `zero_shot_unvalidated` = semantic suggestion that was never trained or evaluated (الحنين، الشوق، التأمل).

### 2.3 `recommend_poems(visual, emotion, focus, top_k=3) -> list` — owner: Mohammed (`nlp/`)

Input: the `analyze_visual` dict, the emotion chosen by the user (`project_emotion` string), the chosen focus (`focus_candidates[].id` or free text).

```json
[{
  "poem_id": "P000123",
  "opening": "مطلع القصيدة",
  "poet": {"poet_id": "POET0042", "name_ar": "..."},
  "verses": ["بيت مختار 1", "بيت مختار 2"],
  "match_types": ["visual", "semantic", "emotional"],
  "explanation_ar": "سبب الترشيح",
  "score": 0.74,
  "has_story": true
}]
```
Returns **fewer than `top_k`** results when no suitable poem exists; never pads.

### 2.4 `get_historical_story(poem_id) -> dict` — owner: Omar (`history/`)

```json
{
  "poem_id": "P000123",
  "status": "documented | disputed | unknown_occasion",
  "stations": [
    {"id": "poet",  "title_ar": "الشاعر",  "text_ar": "...", "source_ids": ["S001"]},
    {"id": "story", "title_ar": "الحكاية", "text_ar": "...", "source_ids": ["S002", "S003"]},
    {"id": "poem",  "title_ar": "القصيدة", "text_ar": "...", "source_ids": ["S001"]}
  ],
  "variants_note_ar": "وجود اختلاف في الروايات إن وجد",
  "sources": [{"source_id": "S001", "title": "كتاب الأغاني", "author": "أبو الفرج الأصفهاني",
               "volume_page": "ج 1 ص 1", "url": null}]
}
```
`unknown_occasion`: the `story` station is a sourced biography note and must say the occasion is unknown.

## 3. Shared vocabularies

- **Emotion labels** (owner: Renad, consumed by Mohammed): trained classes from EmoSet — amusement, awe, contentment, excitement, anger, disgust, fear, sadness — mapped to the project list: الفرح (amusement, excitement)، السكينة (contentment)، الرهبة (awe)، الحزن (sadness). Derived only: الحنين، الشوق، التأمل. Poetry taxonomy emotion tags must use the same Arabic project names.
- **Visual tags** (owner: Shaden, consumed by Mohammed): one list in `data/visual_tags.json` with `label`, `label_ar`, synonyms.
- **IDs** (owners: Mohammed + Omar): `poem_id` and `poet_id` are created once in `data/poems.json` and reused unchanged in `data/stories.json` and `data/poem_id_mapping.json`.

## 4. Backend API (FastAPI, shared)

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/api/analyze` | multipart image | `{"visual": ..., "emotions": ...}` |
| POST | `/api/poems` | `{"visual": ..., "emotion": "السكينة", "focus": "f1"}` | list from `recommend_poems` |
| GET | `/api/stories/{poem_id}` | — | dict from `get_historical_story` |
| GET | `/api/health` | — | module versions |
