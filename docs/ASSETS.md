# حالة الأصول

آخر تحديث: 2026-11-26. الرموز: **موجود** (تحقق محلي)، **مطلوب** (عند صاحبه)، **ينتظر موافقة** (تنزيل)، **لم يبدأ**.

## أصول ناقصة

| البند | الحائز | الملف أو المسار | المحتوى المتوقع | الحالة | إن غاب |
|---|---|---|---|---|---|
| R1 | رناد | `emoset.zip` | `emoset/{train,val,test}/<emotion>/<image_id>.jpg`؛ 600/150/400 لكل إحساس | **موجود** (انظر أدناه) | — |
| S1 | شادن | `ml/visual/data/places_manifest.csv` | `path,label,places_class,io,split`؛ 5,980 صفًا متوقعًا؛ مسارات Windows | **موجود** (2026-11-26، `external/shaden_visual/data/`) | N2 |
| S2 | شادن | `ml/visual/data/places365/<category-folder>/Places365_val_*.jpg` | 5,980 صورة بدقة 256 | **موجود** (2026-11-26، `external/shaden_visual/data/`) | N2 |
| S3 | شادن | `ml/visual/data/features/places_clip.npz` | `feats` (5,980×512، float32، L2) و`paths` | **موجود** (2026-11-26، `external/shaden_visual/data/`) | تُحسب من S2 |
| S4 | شادن | `pip freeze` لبيئة التدريب + نظام التشغيل والجهاز | إصدارات python وtorch وopen_clip_torch وnumpy وscikit-learn | مطلوب | توثيق أضعف |
| S5 | شادن (اختياري) | `openimages_manifest.csv` و`data/openimages/*.jpg` و`openimages_clip.npz` | لإعادة تقييم الوسوم فقط | مطلوب | النتائج المنشورة |
| S6 | شادن (عند إعادة التشغيل) | `ml/visual/data/raw/places365/IO_places365.txt` | ملف IO لفئات Places365 | **موجود** (2026-11-26، `external/shaden_visual/data/`) | يُجلب مع N2 |
| N1 | الشبكة | بيانات EmoSet الوصفية `image_id, emotion, scene` | من الإصدار الرسمي (Dropbox) بطلبات range دون أي صورة | **موجود** (2026-11-26، انظر أدناه) | — |
| N2 | الشبكة | إعادة تشغيل `prepare_data.py places` | — | لم يعد لازمًا (S1–S3 موجودة) | — |
| N3 | الشبكة | إعادة عيّنة رناد | — | لم يعد لازمًا (R1 موجود) | — |
| N4 | الشبكة (اختياري) | gensim في بيئة منفصلة | لتجربة Word2Vec | ينتظر موافقة | يُلغى Word2Vec |
| T1 | الفريق | صور PV-Test | 30–40 صورة يملكها ملتقطوها، 5 مجموعات تجريبية + 5 غير مدعومة، بلا وجوه، مع موافقة | لم يبدأ | تقييم أصغر بحد معلن |

## أصول موجودة (تحقق محلي في 2026-11-25)

| الأصل | المسار | التحقق |
|---|---|---|
| أوزان CLIP | `$PV_HF_CACHE/models--timm--vit_base_patch32_clip_224.openai/snapshots/a6f597a30f7b82c51704746581f9a4e41421e878/open_clip_model.safetensors` | sha256 `e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31`، 605,143,284 بايت؛ تُحمَّل offline في `.venv` خلال 1.36 ثانية؛ البرج البصري 87,849,216 معاملًا؛ المخرج 512 |
| رؤوس شادن | `product/vendor/visual_module/ml/visual/weights/{scene_head_clip.npz, tag_heads.npz, calibration.json}` | ترتيب الفئات (17) والوسوم (34) مطابق لـ`taxonomy_v1.json` (اختبار `tests/contracts/test_external_alignment.py`) |
| نتائج شادن | `.../results/{metrics.json, tag_metrics.json}` | 13 وسمًا `validated=true` |
| نموذج رناد | `team_modules/emotion_keras_results/emotion_keras/{emotion_resnet50.keras, model_config.json}` | ترتيب الفئات الثماني مطابق |
| APCD | `Arabic Poem Comprehensive Dataset (APCD).csv.zip` (87.6 MB) | الترويسة الثمانية مطابقة لـ`contracts/apcd.py` |
| قاعدة المعرفة | `data/poems_reference.json` | 15 قصيدة بصفوف موثّقة (مصدر نصوص الـfixtures) |
| تلميحات V3 | `work/apcd-semantic-v3/parquet/` (74 ملفًا) | للتلميح فقط، غير مراجَعة |
| التطبيق القديم | `product/poetry_vision/`، `product/frontend/`، `product/run.sh` | للنقل في M7، دون تعديل الأصل |
| البيئة | `Poetry-Vision-Final/.venv` (Python 3.12.15) | بُنيت offline من ذاكرة uv دون تنزيل، وفق `requirements.txt` |
| EmoSet (رناد، R1) | `external/renad/emoset.zip` (نسخة من `~/Downloads/emoset (1).zip`) | 160,925,142 بايت، sha256 `df604d10fd825dd0d9761e8ccda26c3e7859a2c517f64eae06900f359eb13693`؛ تحقق مستقل في 2026-11-26: 9,200 صورة JPEG بنمط RGB تُفك كلها؛ train/val/test = 4,800/1,200/3,200؛ 600/150/400 لكل إحساس من الثمانية؛ 0 تالف، 0 اسم مكرر، 0 تكرار بايتي، 0 مسار غير آمن؛ أطول ضلع 256 (عدا 3 صور: 240، 240، 239)؛ أقصر ضلع ≥ 64 |
| بيانات EmoSet الوصفية (N1) | `external/emoset_metadata/` | 118,102 سجلًا `image_id, emotion, scene, official_split` من الإصدار الرسمي؛ 49,613,395 بايت منقولة دون أي صورة؛ تطابق كامل مع الـ9,200 (0 غير مطابق، 0 اختلاف إحساس، التقسيمات مطابقة)؛ المشهد متاح لـ2,105 صورة منها؛ التفاصيل في `evaluation/annotation/emoset_n1/N1_REPORT.md` |
| ذاكرة الـembeddings | `artifacts/features/emoset_clip_vitb32.npz` | 9,200×512 float32 مطبّعة L2، مفتاحها sha256 الصورة؛ بُنيت على MPS في 45.9 ثانية |
| تسليم شادن M2 | `external/deliveries/For_Omar_2026-11-26.zip` (sha256 `4fac224b…8bb92`) | `Shaden_M2_Dataset_v1.zip` و`shaden_visual_places365.zip` و`emoset.zip` (مطابق لـR1)، وكل بصمة مطابقة لملفها؛ المحتوى مثبّت في `datasets/` و`data_preparation/` و`tests/data_preparation/` و`evaluation/pv_test/` |
| manifest البيانات | `datasets/manifests/manifest_v0.9_emotion.jsonl` (9,200، sha256 `7df0416f…`) و`manifest_v1.jsonl` (15,180، sha256 `efdf33b1…`) | التحقق في وضع الإنتاج: 0 مشكلة لكل منهما؛ v0.9 مطابق للذاكرة (sha256 الصور والتقسيمات) وللتسميات الرسمية (N1) |
| ذاكرة Places365 | `artifacts/features/places_clip_vitb32.npz` | 5,980×512؛ مطابقة لـ`places_clip.npz` من شادن (أدنى cosine 0.9999998) |
| رؤوس مدرَّبة ومعايرة | `artifacts/heads/emotion_head_v1.npz` و`artifacts/heads/scene_calibration_v1.json` و`artifacts/model_card_v1.json` | بطاقة النموذج تجتاز العقد (مسودة؛ تجتاز أيضًا قواعد الإصدار) |
