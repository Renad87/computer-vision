# حزمة مراجعة ذات أولوية لعمر: الخلايا التجريبية

56 بيتًا تغطي الخلايا التجريبية الخمس والعشرين (5 مجموعات مشهد × 5 أحاسيس أدبية في `taxonomy.pilot`)، مأخوذة من `poetry_corpus/exports/corpus_all_v2.jsonl`.

| الملف | المحتوى |
|---|---|
| `Poetry_Review_Priority_v1_56.xlsx` | ملف العمل: التعليمات، والأحاسيس الثمانية، وورقة «المراجعة» |
| `review_sheet_priority_v1.csv` | نسخة CSV (UTF-8 مع BOM) للاستعمال البرمجي |
| `priority_v1_manifest.json` | المعرّفات والأولويات والتغطية ونتيجة التحقق |

## ما في الحزمة

- **V، الوسم البصري فقط (12 صفًا):** أبيات قبلت المراجِعة `human:renad` إحساسها في P0، ولم يراجع إنسان وسومها البصرية بعد. أعمدة الإحساس تبقى فارغة.
- **A/B/C، الإحساس والوسم البصري (44 صفًا):** مسودات آلية لم تُراجع، مختارة بالتغطية الجشعة نفسها في `poetry_corpus/tools/build_review_package.py` (حتى ثلاث قصائد مختلفة لكل خلية بعد احتساب صفوف V): A 14، B 15، C 15.
- **مستبعد:** الأبيات الخمسة المعلقة من ورقة رناد (`pv:verse:000005`، `pv:verse:000007`، `pv:verse:000018`، `pv:verse:000024`، `pv:verse:000031`)؛ تحتاج توضيحًا منها، لا مراجعة جديدة.
- خلايا القرار كلها فارغة، ولا يُسجَّل أي قرار آليًا.

## الإرجاع والاستيراد

احفظ الملف باسم `review_priority_v1_v1.xlsx`، ثم:

```bash
python3 -m poetry_corpus.review.import_review review_priority_v1_v1.xlsx --reviewer human:omar \
    --base poetry_corpus/exports/corpus_all_v2.jsonl --out-version v3 \
    --sent poetry_corpus/review_packages/priority_v1/Poetry_Review_Priority_v1_56.xlsx
```

يستورد البرنامج ACCEPT الواضح وحده، ويترك ما سواه معلقًا مع السبب في `poetry_corpus/reports/review_import_v3.json`.
