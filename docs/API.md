# Poetry Vision final app: HTTP API (backend/ ↔ frontend/)

Backend: FastAPI in `backend/app.py`, default `http://127.0.0.1:8010` (port 8000 belongs to the frozen old product).
The built frontend (`frontend/dist`) is served by the backend at `/`. In development, Vite on `:5174` proxies `/api` to `:8010`.

All JSON. Errors use HTTP 4xx/5xx with `{"error": {"code": "...", "message_ar": "..."}}`.

## GET /api/health
`{"status": "ok", "app_version": "1.0.0"}`

## GET /api/ready
```
{
  "ready": bool,                     // model and corpus loaded
  "model":  {"loaded": bool, "model_id", "model_version", "device", "error": str|null,
             "fingerprints": {"clip_weights_sha256", "emotion_head_sha256", "scene_head_sha256", "tag_head_sha256", "scene_calibration_sha256"}},
  "corpus": {"loaded": bool, "version", "sha256", "count", "displayable": {"production": int, "development": int}, "error": str|null},
  "engine_version": "1.0.0",
  "modes": ["production", "development"],
  "default_mode": "production"
}
```

## GET /api/taxonomy
Labels for the UI (Arabic names): `scene_groups`, `scenes`, `img_emotions`, `lit_emotions`, `exposed_tags`, `pilot`, `suggestion_map`, `user_only_lit_emotions`.
Each label: `{"id", "name_ar", "name_en"}`.

## POST /api/analyze  (multipart, field `image`)
Runs the single CLIP model once. Returns
```
{
  "analysis_id": "uuid4",
  "inference": <inference_output contract document>,
  "suggestion": {                     // deterministic defaults for the confirmation step, never a user choice
     "visual_items": [{"id": "scene_group.*|tag.*", "name_ar", "score": float|null, "source": "scene_group|tag"}],
     "lit_emotions": [{"id", "name_ar", "from_img_emotion"}]
  },
  "timings_ms": {"inference": ..., "total": ...}
}
```
Errors: 400 `invalid_image | unsupported_format | too_small | empty_file`, 413 `too_large`, 503 `model_not_ready`.
`inference.scene.status` may be `unsupported` (low confidence) and `inference.emotion.status` may be `ambiguous`.

## POST /api/recommend  (JSON)
```
{
  "analysis_id": "uuid4",                 // reuses the cached inference; the model is not run again
  "selected_lit_emotion": "lit_emotion.*",
  "secondary_lit_emotion": "lit_emotion.*" | null,
  "confirmed_visual_items": [{"id": "...", "user_selection": "focus|primary|secondary"}],   // at most one focus
  "symbolic_allowed": bool,
  "emotion_only_allowed": bool,
  "mode": "production" | "development"
}
```
Returns
```
{
  "mode": "...",
  "disclosure_ar": str|null,          // set in development mode
  "profile": <image_profile>,
  "query": <retrieval_query>,
  "recommendations": <recommendations contract document>,
  "display": [{"verse_id", "hemistichs": {...}, "meaning_ar", "source": {...}, "poet_name_apcd", "era_apcd",
               "review_status", "annotation_method"}],     // display-only fields read from the corpus record, same order as items
  "timings_ms": {"retrieval": ..., "total": ...},
  "inference_reused": true
}
```
Errors: 404 `analysis_not_found` (expired: re-upload), 422 `invalid_profile` (with `issues`), 503 `corpus_not_ready`.
`recommendations.status` is `ok | partial | abstained`; when abstained, `recommendations.abstention` carries `reason` and `message_ar`.
