# Visual Understanding module — نظام الفهم البصري

Takes a user photo and returns **what is in it** (scene, objects, culturally relevant elements, colours, light)
and **which poetic themes it may suggest**, with facts kept separate from interpretations.
Image emotion/mood is **not** done here — that is the emotion module.

```
photo ─► CLIP ViT-B/32 ─► 512-d vector ─┬─► scene head (16 scenes + "other")   ─► scene_labels, supported
                                        ├─► 34 tag heads (camel, moon, mosque…) ─► visual_tags
                                        └─► zero-shot prompts                   ─► indoor/outdoor, time of day
      ─► YOLOv8n ──────────────────────────────────────────────────────────────► objects + boxes, focus_options
      ─► pixels ───────────────────────────────────────────────────────────────► brightness, colours
facts ─► rules in taxonomy.json ───────────────────────────────────────────────► possible_meanings
```

## Quick start (from this folder)

```powershell
pip install -r requirements.txt          # first run also downloads CLIP weights (~600 MB) automatically
python test_image.py photo.jpg           # readable summary in the terminal   (add --show to see YOLO boxes)
python inference.py photo.jpg            # full JSON output
```

From Python (backend / demo):

```python
from inference import analyze_visual     # import this BEFORE pandas (see "Known issues")
result = analyze_visual(open("photo.jpg", "rb").read())
```

Load once at startup: the first call takes 5–13 s (model loading), then ~0.7 s per image on CPU.

## Files

| File | What it is |
|---|---|
| **`visual_model_simple.ipynb`** | **Start here.** The whole project in one course-style notebook: data → features → zero-shot (before) → trained head (after) → evaluation → tags → YOLO → `analyze_visual` |
| `eda_preprocessing.ipynb` | Data exploration + every preprocessing step, with figures |
| `test_image.py` | Test any image from the terminal (uses the model saved by the simple notebook) |
| `inference.py` | **Official** `analyze_visual(image_bytes)` used by the app |
| `train.py` | Trains the scene head and tag heads, calibrates all thresholds |
| `evaluate.py` | Evaluates everything on held-out test data, writes `results/` |
| `prepare_data.py` | Downloads the data sample (Places365 + Open Images, ~600 MB) |
| `common.py` | Shared helpers: CLIP, YOLO, feature cache. `embed_image()` = shared backbone for teammates |
| `taxonomy.json` | Scenes, tags, Arabic names, **meaning rules** (the poetry lead edits this, no code changes needed) |
| `weights/` | Trained model (~7 MB incl. `yolov8n.pt`) |
| `results/` | Real evaluation results: `summary.md`, `metrics.json`, confusion matrices, error galleries, `eda/` figures |
| `../../docs/visual_methodology.md` | Full write-up (Arabic): data, method, results, error analysis, limits |

`data/` is not shared (in `.gitignore`); rebuild it with `python prepare_data.py` only if you want to retrain.

## Output of `analyze_visual`

| Field | Kind | Content |
|---|---|---|
| `scene_labels` | fact | up to 3 of 16 scenes with confidence, or `[]` if the scene is outside what was tested |
| `objects` | fact | YOLO objects (80 COCO classes) with Arabic name, confidence, box (0–1) |
| `visual_tags` | fact | validated tags only (13 of 34), e.g. مسجد، قمر، حصان، صقر، بحر |
| `visual_attributes` | fact | indoor/outdoor, time of day (`evaluated: false`), brightness, colourfulness, dominant colours, people count |
| `possible_meanings` | **interpretation** | poetic themes from rules, each with its `evidence` |
| `focus_options` | choice | whole image / object groups / objects (with boxes) / concepts |
| `supported` | decision | `false` only if no scene, object or tag was recognised |
| `model_version`, `notes` | info | version string; why something was not supported |

Example (beach photo): scene `بحر وشاطئ` 0.54 + `سماء` 0.30 · tag `بحر` · meanings `ركوب البحر والمجهول`, `الكرم (البحر في العطاء)`.

## Results (held-out test data)

| | Before training | After training |
|---|---|---|
| Scene accuracy (16 classes, 860 images) | 76.6 % (zero-shot) · MobileNetV2 head 67.8 % | **80.5 %** (top-3 97.6 %) |
| Unfamiliar scenes rejected (600 images, 20 unseen categories) | 37 % | **80 %** (AUROC 0.94) |
| Tags, mean AP (Open Images, human-verified) | 0.767 | **0.863** |
| Indoor / outdoor | 93.9 % | — |
| YOLO objects | F1 0.80–0.93 (person, car, bird, horse, dog, boat, cat), book 0.54 | — |

Details: `results/summary.md`.

## How it connects to the other modules

* **Emotion module:** same input photo, separate model. They give the *mood*, we give the *content and themes*.
  `common.embed_image(img)` returns our CLIP vector if they want to reuse the backbone.
* **Poetry module:** uses `possible_meanings` (themes) and `scene_labels` / `visual_tags` (concrete elements)
  together with the emotion output. The theme names in `taxonomy.json → meanings.rules` must match the labels used on the poems.

## Known issues / limits

* **Windows import order:** if `pandas` is imported before `torch`, torch fails with `WinError 1114`
  (pyarrow DLL clash). Import `inference` (or `torch`) **before** pandas.
* Tested on photographs only — not on paintings, calligraphy, screenshots or generated images.
* 21 of 34 tags are not validated (palm tree, tent, sword, camel is close) and are hidden by default;
  `analyze_visual(b, include_unvalidated_tags=True)` shows them marked `validated: false`.
* `time_of_day` is not evaluated and never feeds the meanings.
* Very small images (< ~300 px) or backlit silhouettes: objects are often missed.
* HEIC (iPhone) files are not supported — convert to JPEG/PNG.
* The meaning rules are a draft until reviewed by the poetry lead.

## Reproduce from scratch

```powershell
python prepare_data.py     # ~30 min download
python train.py            # ~25 min the first time (feature extraction), ~3 min after
python evaluate.py         # writes results/
```
