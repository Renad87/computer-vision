# Visual Emotion Recognition — ml/emotion

**Owner:** Renad · **Epic:** #2 · **Methodology:** [`docs/emotion_methodology.md`](../../docs/emotion_methodology.md)

## ملخص الجزء

يقترح هذا المكون **الجو العاطفي الذي توحي به الصورة** (وليس مشاعر المستخدم الحقيقية) ليستخدمه محرك الشعر في المطابقة العاطفية.

- **البيانات:** EmoSet-118K، فيها 8 فئات موسومة: amusement, awe, contentment, excitement, anger, disgust, fear, sadness. نأخذ عينة متوازنة من كل تقسيم رسمي (train / val / test) دون خلط بينها.
- **النموذج:** CLIP ViT-B/32، وهو نفس الـ backbone عند شادن ليُحمَّل نموذج واحد فقط في التطبيق.
- **التدريب (Transfer Learning من الجزء 3 في الوحدة):**
  0. Zero-shot: النموذج قبل أي تدريب، كخط أساس.
  1. Feature Extraction: CLIP مجمد + رأس تصنيف (Logistic Regression أو MLP)، ومعه ResNet50 مجمد للمقارنة بشبكة CNN كلاسيكية.
  2. Fine-tuning: فك تجميد آخر طبقتين بمعدل تعلم منخفض، والرأس يبدأ من نتيجة المرحلة الأولى.
- **التقييم:** على Test مستقل: Accuracy، Macro F1 مع فترة ثقة، أداء كل فئة، Confusion Matrix، معايرة الاحتمالات، تحليل الصور الغامضة، ودراسة أثر الألوان والإضاءة.
- **الصدق في الادعاء:** الحنين والشوق والتأمل غير موجودة في EmoSet، فتُعرض كـ "اقتراحات دلالية غير مدربة" (`zero_shot_unvalidated`)، ولا يُدّعى أن النموذج تدرب عليها.

## التشغيل (Google Colab مع GPU)

```bash
pip install -q -r ml/emotion/requirements.txt
python ml/emotion/prepare_features.py      # 1) sample EmoSet + cache images + extract features
python ml/emotion/train.py --finetune      # 2) zero-shot, feature extraction, fine-tuning
python ml/emotion/evaluate.py              # 3) independent test evaluation -> results/RESULTS.md
python ml/emotion/inference.py photo.jpg   # 4) try the integration function
```

Faster run if time is short: `prepare_features.py --per_class_train 600 --skip_resnet`, then `train.py` without `--finetune`.
The notebook keeps outputs inside the Colab session by default (no Google Drive access) and downloads a zip at the end; set `USE_DRIVE = True` only if you want them to survive disconnects.

## الملفات

| File | Purpose |
|---|---|
| `config.py` | labels, Arabic names, mapping to project emotions, defaults |
| `data.py` | streams a class-balanced sample of each official EmoSet split |
| `prepare_features.py` | caches images, extracts CLIP / ResNet50 features and colour-light attributes |
| `train.py` | zero-shot baseline, feature-extraction heads, temperature calibration, export |
| `finetune.py` | partial unfreezing of the last CLIP blocks |
| `evaluate.py` | test-set metrics, charts, auto-generated `results/RESULTS.md` |
| `inference.py` | `analyze_emotions(image_bytes)` — the integration contract |
| `attributes.py`, `policy.py`, `head.py`, `metrics.py`, `encoders.py` | shared helpers |
| `tests/test_offline.py` | offline tests on synthetic data (no GPU, no internet) |

## عقد التكامل

```python
from ml.emotion.inference import analyze_emotions
result = analyze_emotions(image_bytes)                      # loads CLIP once
result = analyze_emotions(image_bytes, clip_embedding=emb,  # reuse Shaden's embedding
                          embedding_model_name="openai/clip-vit-base-patch32")
# -> emotion_suggestions, visual_affective_attributes, uncertainty, model_version
```

## Outputs (not committed if large)

- `artifacts/emotion_head.npz` — deployed head (small, can be committed)
- `artifacts/finetuned/` — unfrozen-layer weights (~60 MB, git-ignored: share via Google Drive or Hugging Face Hub) + meta
- `results/` — metrics.json, RESULTS.md and all charts

**Status:** code tested offline on synthetic data only. Real results appear in `results/RESULTS.md` after running the pipeline on Colab.
