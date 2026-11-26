# Quality benchmark: before vs after

- Before: model 1.0.0, engine 1.0.0, corpus corpus_all_v2 (2026-11-26T06:47:42)
- After: model 1.0.0, engine 1.1.0, corpus corpus_all_v2 (2026-11-26T07:07:31)
- Same 16 real Places365 test photos (`benchmark_set.json`), same queries: app-suggested visual items x 5 pilot literary emotions x 2 modes.
- Behaviour counts only. No human relevance judgments exist; nothing here is an accuracy or quality score.

| Count | Before | After |
|---|---|---|
| auto_suggested_lit | 16 | 12 |
| awe_top1 | 10 | 10 |
| development:T>0 | 210 | 210 |
| development:abstained | 3 | 3 |
| development:items | 219 | 219 |
| development:literal | 214 | 214 |
| development:ok | 71 | 71 |
| development:partial | 6 | 6 |
| development:tier1 | 214 | 214 |
| development:tier3 | 5 | 5 |
| emotion_ambiguous | 4 | 4 |
| images | 16 | 16 |
| production:T>0 | 23 | 23 |
| production:abstained | 53 | 53 |
| production:items | 40 | 40 |
| production:literal | 23 | 23 |
| production:ok | 3 | 3 |
| production:partial | 24 | 24 |
| production:tier1 | 35 | 35 |
| production:tier3 | 5 | 5 |
| top1_ge_0.95 | 3 | 3 |

## mountains · img:places365_sample:Places365_val_00000041 (mountain)

- Scene: before snow_ice 0.85 (confident); after snow_ice 0.85 (confident)
- Image emotion top-3: before awe 0.996, contentment 0.002, excitement 0.001 (clear); after awe 0.996, contentment 0.002, excitement 0.001 (clear)
- Suggested literary emotion: before ['awe']; after ['awe']
- Confirmed visual items (app suggestion): before ['scene_group.mountains']; after ['scene_group.mountains']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.165 → 0.833 · literal · أَبو تَمّام: سَقى اللَهُ البِقاعَ فَحَيثُ راقَت    جِبالُ الثَلجِ رَحباً وَالرَحيبُ
- before · tier 1 · E 1.00 V 1.0 T 0.147 → 0.829 · literal · شهاب الدين الخلوف: يا حبذا زمن في الشعب مر وقد    هبت علينا من الوادي نسيمات
- before · tier 1 · E 1.00 V 1.0 T 0.12 → 0.824 · literal · الباخرزي صاحب الدمية: حنَّتْ هوىً لجبالِ الثّلجِ راحِلتي    وما لهَا بِبراقِ الشِّيحِ من عَطَنِ
- after · tier 1 · E 1.00 V 1.0 T 0.165 → 0.833 · literal · أَبو تَمّام: سَقى اللَهُ البِقاعَ فَحَيثُ راقَت    جِبالُ الثَلجِ رَحباً وَالرَحيبُ
- after · tier 1 · E 1.00 V 1.0 T 0.147 → 0.829 · literal · شهاب الدين الخلوف: يا حبذا زمن في الشعب مر وقد    هبت علينا من الوادي نسيمات
- after · tier 1 · E 1.00 V 1.0 T 0.12 → 0.824 · literal · الباخرزي صاحب الدمية: حنَّتْ هوىً لجبالِ الثّلجِ راحِلتي    وما لهَا بِبراقِ الشِّيحِ من عَطَنِ

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.172 → 0.834 · literal · ابنة حذاق الحنفي: أَعينيَّ جودا بِالدموعِ عَلى الصدرِ    عَلى الفارسِ المَقتولِ في الجبل الوعرِ
- before · tier 1 · E 1.00 V 1.0 T 0.167 → 0.833 · literal · ابن حمديس: ويسومُ ضيماً كلَّ أعصمَ شاهقٍ    ريبُ المنون وكلَّ حيَّةِ وادِ
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · ابن نباتة السعدي: تَطاوَلَ لَيْلي بالجبال تَزورُني    جِبال هُمومٍ تَرتَمي وتُماصِعُ
- after · tier 1 · E 1.00 V 1.0 T 0.172 → 0.834 · literal · ابنة حذاق الحنفي: أَعينيَّ جودا بِالدموعِ عَلى الصدرِ    عَلى الفارسِ المَقتولِ في الجبل الوعرِ
- after · tier 1 · E 1.00 V 1.0 T 0.167 → 0.833 · literal · ابن حمديس: ويسومُ ضيماً كلَّ أعصمَ شاهقٍ    ريبُ المنون وكلَّ حيَّةِ وادِ
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · ابن نباتة السعدي: تَطاوَلَ لَيْلي بالجبال تَزورُني    جِبال هُمومٍ تَرتَمي وتُماصِعُ

**awe · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.079 → 0.816 · literal · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ
- after · tier 1 · E 1.00 V 1.0 T 0.079 → 0.816 · literal · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.201 → 0.840 · literal · بشر بن المعتمر: والصدع الأعصمُ في شاهقٍ    وجأبةٌ مسكنها الوعرُ
- before · tier 1 · E 1.00 V 1.0 T 0.178 → 0.836 · literal · عدي بن زيد: وأَرَى الشَّاهِقَ المُدِلَّ بهِ الأَر    وَى دُوَينَ السَّحابِ وَعرَ الَمراقي
- before · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal · أمية بن أبي الصلت: قِيلَ فَاِهبِط فَقَد تَناهَت بِكَ الفُلكَ عَلى    رَأَسِ شاهِقٍ مرساها
- after · tier 1 · E 1.00 V 1.0 T 0.201 → 0.840 · literal · بشر بن المعتمر: والصدع الأعصمُ في شاهقٍ    وجأبةٌ مسكنها الوعرُ
- after · tier 1 · E 1.00 V 1.0 T 0.178 → 0.836 · literal · عدي بن زيد: وأَرَى الشَّاهِقَ المُدِلَّ بهِ الأَر    وَى دُوَينَ السَّحابِ وَعرَ الَمراقي
- after · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal · أمية بن أبي الصلت: قِيلَ فَاِهبِط فَقَد تَناهَت بِكَ الفُلكَ عَلى    رَأَسِ شاهِقٍ مرساها

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.119 → 0.824 · literal · عبد العزيز الفِشتالي: وَما ضَمَّخَت صُلعَ الرُبى راحَةُ الصَبا    فَصَيَّرَها أَو نَمَّقَتها ثُلوجُ
- before · tier 1 · E 1.00 V 1.0 T 0.09 → 0.818 · literal · ابن الراعي: وادي منين انضر الوديان    أطياره تشدو على العيدان
- before · tier 1 · E 1.00 V 1.0 T 0.076 → 0.815 · literal · أبو القاسم الشابي: لِتَنامَ أورادُ الجبالِ الشُمِّ    في مهدٍ عَجيبْ
- after · tier 1 · E 1.00 V 1.0 T 0.119 → 0.824 · literal · عبد العزيز الفِشتالي: وَما ضَمَّخَت صُلعَ الرُبى راحَةُ الصَبا    فَصَيَّرَها أَو نَمَّقَتها ثُلوجُ
- after · tier 1 · E 1.00 V 1.0 T 0.09 → 0.818 · literal · ابن الراعي: وادي منين انضر الوديان    أطياره تشدو على العيدان
- after · tier 1 · E 1.00 V 1.0 T 0.076 → 0.815 · literal · أبو القاسم الشابي: لِتَنامَ أورادُ الجبالِ الشُمِّ    في مهدٍ عَجيبْ

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.19 → 0.838 · literal · ابن الراعي: أولهم يا صاح وادي بردا    واد ترى للأنس فيه مددا
- before · tier 1 · E 1.00 V 1.0 T 0.071 → 0.814 · literal · شرف الدين البوصيري: واهْتَزَّ مِنْ فَرَحٍ ثَبِيرٌ تَحْتَهُ    وَمِنَ الجِبَالِ مُسَبِّحٌ ومُؤَوِّبُ
- before · tier 1 · E 1.00 V 1.0 T 0.063 → 0.813 · literal · أبو نُوّاس: لَمّا بَدا الثَعلَبُ في سَفحِ الجَبَل    صِحتُ بِكَلبي ها فَهاجَ كَالبَطَل
- after · tier 1 · E 1.00 V 1.0 T 0.19 → 0.838 · literal · ابن الراعي: أولهم يا صاح وادي بردا    واد ترى للأنس فيه مددا
- after · tier 1 · E 1.00 V 1.0 T 0.071 → 0.814 · literal · شرف الدين البوصيري: واهْتَزَّ مِنْ فَرَحٍ ثَبِيرٌ تَحْتَهُ    وَمِنَ الجِبَالِ مُسَبِّحٌ ومُؤَوِّبُ
- after · tier 1 · E 1.00 V 1.0 T 0.063 → 0.813 · literal · أبو نُوّاس: لَمّا بَدا الثَعلَبُ في سَفحِ الجَبَل    صِحتُ بِكَلبي ها فَهاجَ كَالبَطَل

## mountains · img:places365_sample:Places365_val_00001780 (mountain)

- Scene: before mountains_valleys 0.89 (confident); after mountains_valleys 0.89 (confident)
- Image emotion top-3: before awe 0.432, anger 0.374, fear 0.089 (ambiguous); after awe 0.432, anger 0.374, fear 0.089 (ambiguous)
- Suggested literary emotion: before ['awe']; after []
- Confirmed visual items (app suggestion): before ['scene_group.mountains']; after ['scene_group.mountains']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.165 → 0.833 · literal · أَبو تَمّام: سَقى اللَهُ البِقاعَ فَحَيثُ راقَت    جِبالُ الثَلجِ رَحباً وَالرَحيبُ
- before · tier 1 · E 1.00 V 1.0 T 0.147 → 0.829 · literal · شهاب الدين الخلوف: يا حبذا زمن في الشعب مر وقد    هبت علينا من الوادي نسيمات
- before · tier 1 · E 1.00 V 1.0 T 0.12 → 0.824 · literal · الباخرزي صاحب الدمية: حنَّتْ هوىً لجبالِ الثّلجِ راحِلتي    وما لهَا بِبراقِ الشِّيحِ من عَطَنِ
- after · tier 1 · E 1.00 V 1.0 T 0.165 → 0.833 · literal · أَبو تَمّام: سَقى اللَهُ البِقاعَ فَحَيثُ راقَت    جِبالُ الثَلجِ رَحباً وَالرَحيبُ
- after · tier 1 · E 1.00 V 1.0 T 0.147 → 0.829 · literal · شهاب الدين الخلوف: يا حبذا زمن في الشعب مر وقد    هبت علينا من الوادي نسيمات
- after · tier 1 · E 1.00 V 1.0 T 0.12 → 0.824 · literal · الباخرزي صاحب الدمية: حنَّتْ هوىً لجبالِ الثّلجِ راحِلتي    وما لهَا بِبراقِ الشِّيحِ من عَطَنِ

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.172 → 0.834 · literal · ابنة حذاق الحنفي: أَعينيَّ جودا بِالدموعِ عَلى الصدرِ    عَلى الفارسِ المَقتولِ في الجبل الوعرِ
- before · tier 1 · E 1.00 V 1.0 T 0.167 → 0.833 · literal · ابن حمديس: ويسومُ ضيماً كلَّ أعصمَ شاهقٍ    ريبُ المنون وكلَّ حيَّةِ وادِ
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · ابن نباتة السعدي: تَطاوَلَ لَيْلي بالجبال تَزورُني    جِبال هُمومٍ تَرتَمي وتُماصِعُ
- after · tier 1 · E 1.00 V 1.0 T 0.172 → 0.834 · literal · ابنة حذاق الحنفي: أَعينيَّ جودا بِالدموعِ عَلى الصدرِ    عَلى الفارسِ المَقتولِ في الجبل الوعرِ
- after · tier 1 · E 1.00 V 1.0 T 0.167 → 0.833 · literal · ابن حمديس: ويسومُ ضيماً كلَّ أعصمَ شاهقٍ    ريبُ المنون وكلَّ حيَّةِ وادِ
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · ابن نباتة السعدي: تَطاوَلَ لَيْلي بالجبال تَزورُني    جِبال هُمومٍ تَرتَمي وتُماصِعُ

**awe · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.079 → 0.816 · literal · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ
- after · tier 1 · E 1.00 V 1.0 T 0.079 → 0.816 · literal · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.201 → 0.840 · literal · بشر بن المعتمر: والصدع الأعصمُ في شاهقٍ    وجأبةٌ مسكنها الوعرُ
- before · tier 1 · E 1.00 V 1.0 T 0.178 → 0.836 · literal · عدي بن زيد: وأَرَى الشَّاهِقَ المُدِلَّ بهِ الأَر    وَى دُوَينَ السَّحابِ وَعرَ الَمراقي
- before · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal · أمية بن أبي الصلت: قِيلَ فَاِهبِط فَقَد تَناهَت بِكَ الفُلكَ عَلى    رَأَسِ شاهِقٍ مرساها
- after · tier 1 · E 1.00 V 1.0 T 0.201 → 0.840 · literal · بشر بن المعتمر: والصدع الأعصمُ في شاهقٍ    وجأبةٌ مسكنها الوعرُ
- after · tier 1 · E 1.00 V 1.0 T 0.178 → 0.836 · literal · عدي بن زيد: وأَرَى الشَّاهِقَ المُدِلَّ بهِ الأَر    وَى دُوَينَ السَّحابِ وَعرَ الَمراقي
- after · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal · أمية بن أبي الصلت: قِيلَ فَاِهبِط فَقَد تَناهَت بِكَ الفُلكَ عَلى    رَأَسِ شاهِقٍ مرساها

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.119 → 0.824 · literal · عبد العزيز الفِشتالي: وَما ضَمَّخَت صُلعَ الرُبى راحَةُ الصَبا    فَصَيَّرَها أَو نَمَّقَتها ثُلوجُ
- before · tier 1 · E 1.00 V 1.0 T 0.09 → 0.818 · literal · ابن الراعي: وادي منين انضر الوديان    أطياره تشدو على العيدان
- before · tier 1 · E 1.00 V 1.0 T 0.076 → 0.815 · literal · أبو القاسم الشابي: لِتَنامَ أورادُ الجبالِ الشُمِّ    في مهدٍ عَجيبْ
- after · tier 1 · E 1.00 V 1.0 T 0.119 → 0.824 · literal · عبد العزيز الفِشتالي: وَما ضَمَّخَت صُلعَ الرُبى راحَةُ الصَبا    فَصَيَّرَها أَو نَمَّقَتها ثُلوجُ
- after · tier 1 · E 1.00 V 1.0 T 0.09 → 0.818 · literal · ابن الراعي: وادي منين انضر الوديان    أطياره تشدو على العيدان
- after · tier 1 · E 1.00 V 1.0 T 0.076 → 0.815 · literal · أبو القاسم الشابي: لِتَنامَ أورادُ الجبالِ الشُمِّ    في مهدٍ عَجيبْ

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.19 → 0.838 · literal · ابن الراعي: أولهم يا صاح وادي بردا    واد ترى للأنس فيه مددا
- before · tier 1 · E 1.00 V 1.0 T 0.071 → 0.814 · literal · شرف الدين البوصيري: واهْتَزَّ مِنْ فَرَحٍ ثَبِيرٌ تَحْتَهُ    وَمِنَ الجِبَالِ مُسَبِّحٌ ومُؤَوِّبُ
- before · tier 1 · E 1.00 V 1.0 T 0.063 → 0.813 · literal · أبو نُوّاس: لَمّا بَدا الثَعلَبُ في سَفحِ الجَبَل    صِحتُ بِكَلبي ها فَهاجَ كَالبَطَل
- after · tier 1 · E 1.00 V 1.0 T 0.19 → 0.838 · literal · ابن الراعي: أولهم يا صاح وادي بردا    واد ترى للأنس فيه مددا
- after · tier 1 · E 1.00 V 1.0 T 0.071 → 0.814 · literal · شرف الدين البوصيري: واهْتَزَّ مِنْ فَرَحٍ ثَبِيرٌ تَحْتَهُ    وَمِنَ الجِبَالِ مُسَبِّحٌ ومُؤَوِّبُ
- after · tier 1 · E 1.00 V 1.0 T 0.063 → 0.813 · literal · أبو نُوّاس: لَمّا بَدا الثَعلَبُ في سَفحِ الجَبَل    صِحتُ بِكَلبي ها فَهاجَ كَالبَطَل

## sea · img:places365_sample:Places365_val_00001214 (coast)

- Scene: before sea_coast 0.96 (confident); after sea_coast 0.96 (confident)
- Image emotion top-3: before awe 0.570, excitement 0.206, contentment 0.137 (clear); after awe 0.570, excitement 0.206, contentment 0.137 (clear)
- Suggested literary emotion: before ['awe', 'joy']; after ['awe', 'joy']
- Confirmed visual items (app suggestion): before ['scene_group.sea']; after ['scene_group.sea']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.177 → 0.835 · literal · ابن رشيق القيرواني: وَلَقَدْ ذَكَرْتُكِ في السَّفينَةِ والرَّدى    مُتَوَقَّعٌ بِتَلاطُمِ الأَمْواجِ
- before · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · ظافر الحداد: سلامٌ على القَصْرَين من مَنْشَأ الصَّبا    إلى ساحل الثَّغرِ المُطِلِّ على البحرِ
- before · tier 1 · E 1.00 V 1.0 T 0.109 → 0.822 · literal · وجيه الدولة الحمداني: وقفت والسفن تجري في الرحيل بهم    والدمع يجري على خدي بشاطيه
- after · tier 1 · E 1.00 V 1.0 T 0.177 → 0.835 · literal · ابن رشيق القيرواني: وَلَقَدْ ذَكَرْتُكِ في السَّفينَةِ والرَّدى    مُتَوَقَّعٌ بِتَلاطُمِ الأَمْواجِ
- after · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · ظافر الحداد: سلامٌ على القَصْرَين من مَنْشَأ الصَّبا    إلى ساحل الثَّغرِ المُطِلِّ على البحرِ
- after · tier 1 · E 1.00 V 1.0 T 0.109 → 0.822 · literal · وجيه الدولة الحمداني: وقفت والسفن تجري في الرحيل بهم    والدمع يجري على خدي بشاطيه

**sadness · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 1.0 T 0.3 → 0.680 · literal · خليل مطران: شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ
- after · tier 1 · E 0.60 V 1.0 T 0.3 → 0.680 · literal · خليل مطران: شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.136 → 0.827 · literal · جميل صدقي الزهاوي: لا ينبغي ان يكون البحر قاتله    ان كان للبحر ذي الامواج وجدان
- before · tier 1 · E 1.00 V 1.0 T 0.108 → 0.822 · literal · أبو القاسم الشابي: على ساحِلِ البَحْرِ أَنَّى يضجُّ    صُراخُ الصَّباحِ ونَوْحُ المَسَا
- before · tier 1 · E 1.00 V 1.0 T 0.083 → 0.817 · literal · المهلهل بن ربيعة: وَأَبكي وَالنُجومُ مُطَلِّعاتٌ    كَأَن لَم تَحوِها عَنّي البِحارُ
- after · tier 1 · E 1.00 V 1.0 T 0.136 → 0.827 · literal · جميل صدقي الزهاوي: لا ينبغي ان يكون البحر قاتله    ان كان للبحر ذي الامواج وجدان
- after · tier 1 · E 1.00 V 1.0 T 0.108 → 0.822 · literal · أبو القاسم الشابي: على ساحِلِ البَحْرِ أَنَّى يضجُّ    صُراخُ الصَّباحِ ونَوْحُ المَسَا
- after · tier 1 · E 1.00 V 1.0 T 0.083 → 0.817 · literal · المهلهل بن ربيعة: وَأَبكي وَالنُجومُ مُطَلِّعاتٌ    كَأَن لَم تَحوِها عَنّي البِحارُ

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.159 → 0.832 · literal · أمية بن أبي الصلت: تَجري سَفينَةُ نَوحٍ في جَوانِبِهِ    بِكلِّ مَوجٍ مَعَ الأَرواحِ تَقتَحِمُ
- before · tier 1 · E 1.00 V 1.0 T 0.149 → 0.830 · literal · أبو الحسن الكاتب: انظر إلى البحر وأمواجه    فقد علاها زبد متسق
- before · tier 1 · E 1.00 V 1.0 T 0.127 → 0.825 · literal · الغشري: سبحانه كلُّ له هاطع    سَبَّحَهُ البحرُ مع الساحلِ
- after · tier 1 · E 1.00 V 1.0 T 0.159 → 0.832 · literal · أمية بن أبي الصلت: تَجري سَفينَةُ نَوحٍ في جَوانِبِهِ    بِكلِّ مَوجٍ مَعَ الأَرواحِ تَقتَحِمُ
- after · tier 1 · E 1.00 V 1.0 T 0.149 → 0.830 · literal · أبو الحسن الكاتب: انظر إلى البحر وأمواجه    فقد علاها زبد متسق
- after · tier 1 · E 1.00 V 1.0 T 0.127 → 0.825 · literal · الغشري: سبحانه كلُّ له هاطع    سَبَّحَهُ البحرُ مع الساحلِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · ابن قلاقس: وسَمَالها ذُو رأسٍ فاسْتَذْرَتْ بِهِ    في ساكنِ الأَمواجِ دانِي الهَبَّةِ
- before · tier 1 · E 1.00 V 1.0 T 0.05 → 0.810 · literal · محمد عبد المطلب: سالمتها الرياح فالبحر ساجٍ    لا ترى فيه غير لَمع الحَباب
- before · tier 1 · E 1.00 V 1.0 T 0.043 → 0.809 · literal · الحبسي: تجرى به في البحر في أمانِ    تجرى بريح رحمةِ الرحمنِ
- after · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · ابن قلاقس: وسَمَالها ذُو رأسٍ فاسْتَذْرَتْ بِهِ    في ساكنِ الأَمواجِ دانِي الهَبَّةِ
- after · tier 1 · E 1.00 V 1.0 T 0.05 → 0.810 · literal · محمد عبد المطلب: سالمتها الرياح فالبحر ساجٍ    لا ترى فيه غير لَمع الحَباب
- after · tier 1 · E 1.00 V 1.0 T 0.043 → 0.809 · literal · الحبسي: تجرى به في البحر في أمانِ    تجرى بريح رحمةِ الرحمنِ

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal · الرقيق القيرواني: وفي سر دوس مستراد وملعب    إلى وير مرحنا إلى ساحل البحر
- before · tier 1 · E 1.00 V 1.0 T 0.087 → 0.817 · literal · لسان الدين بن الخطيب: أأبْصَرْتَنا كالشُّهْبِ والشّمْسِ فِتيةً    تَهَلَّلَ منّا البَرُّ والبَحْرُ ذو المَوْجِ
- before · tier 1 · E 1.00 V 1.0 T 0.075 → 0.815 · literal · علي محمود طه: فإذا البحر يرقصُ الموج فيه    وإذا الطير صُدَّحٌ في الروابي
- after · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal · الرقيق القيرواني: وفي سر دوس مستراد وملعب    إلى وير مرحنا إلى ساحل البحر
- after · tier 1 · E 1.00 V 1.0 T 0.087 → 0.817 · literal · لسان الدين بن الخطيب: أأبْصَرْتَنا كالشُّهْبِ والشّمْسِ فِتيةً    تَهَلَّلَ منّا البَرُّ والبَحْرُ ذو المَوْجِ
- after · tier 1 · E 1.00 V 1.0 T 0.075 → 0.815 · literal · علي محمود طه: فإذا البحر يرقصُ الموج فيه    وإذا الطير صُدَّحٌ في الروابي

## sea · img:places365_sample:Places365_val_00004355 (ocean)

- Scene: before sea_coast 0.91 (confident); after sea_coast 0.91 (confident)
- Image emotion top-3: before awe 0.775, contentment 0.150, excitement 0.043 (clear); after awe 0.775, contentment 0.150, excitement 0.043 (clear)
- Suggested literary emotion: before ['awe', 'serenity']; after ['awe', 'serenity']
- Confirmed visual items (app suggestion): before ['scene_group.sea', 'tag.sea']; after ['scene_group.sea', 'tag.sea']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.183 → 0.837 · literal,literal · ابن رشيق القيرواني: وَلَقَدْ ذَكَرْتُكِ في السَّفينَةِ والرَّدى    مُتَوَقَّعٌ بِتَلاطُمِ الأَمْواجِ
- before · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal,literal · ظافر الحداد: سلامٌ على القَصْرَين من مَنْشَأ الصَّبا    إلى ساحل الثَّغرِ المُطِلِّ على البحرِ
- before · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal,literal · محمود سامي البارودي: فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ
- after · tier 1 · E 1.00 V 1.0 T 0.183 → 0.837 · literal,literal · ابن رشيق القيرواني: وَلَقَدْ ذَكَرْتُكِ في السَّفينَةِ والرَّدى    مُتَوَقَّعٌ بِتَلاطُمِ الأَمْواجِ
- after · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal,literal · ظافر الحداد: سلامٌ على القَصْرَين من مَنْشَأ الصَّبا    إلى ساحل الثَّغرِ المُطِلِّ على البحرِ
- after · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal,literal · محمود سامي البارودي: فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ

**sadness · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 0.5 T 0.379 → 0.521 · literal · خليل مطران: شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ
- after · tier 1 · E 0.60 V 0.5 T 0.379 → 0.521 · literal · خليل مطران: شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.192 → 0.838 · literal,literal · جميل صدقي الزهاوي: لا ينبغي ان يكون البحر قاتله    ان كان للبحر ذي الامواج وجدان
- before · tier 1 · E 1.00 V 1.0 T 0.098 → 0.820 · literal,literal · ابن حمديس: عانَقَهَا الموجُ ثمّ فارقَها    عن ضَمّةٍ فاضَ روحها فيها
- before · tier 1 · E 1.00 V 1.0 T 0.097 → 0.819 · literal,literal · أبو القاسم الشابي: على ساحِلِ البَحْرِ أَنَّى يضجُّ    صُراخُ الصَّباحِ ونَوْحُ المَسَا
- after · tier 1 · E 1.00 V 1.0 T 0.192 → 0.838 · literal,literal · جميل صدقي الزهاوي: لا ينبغي ان يكون البحر قاتله    ان كان للبحر ذي الامواج وجدان
- after · tier 1 · E 1.00 V 1.0 T 0.098 → 0.820 · literal,literal · ابن حمديس: عانَقَهَا الموجُ ثمّ فارقَها    عن ضَمّةٍ فاضَ روحها فيها
- after · tier 1 · E 1.00 V 1.0 T 0.097 → 0.819 · literal,literal · أبو القاسم الشابي: على ساحِلِ البَحْرِ أَنَّى يضجُّ    صُراخُ الصَّباحِ ونَوْحُ المَسَا

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · أبو الحسن الكاتب: انظر إلى البحر وأمواجه    فقد علاها زبد متسق
- before · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · حافظ ابراهيم: كُلَّما أَوفَت عَلى أَمواجِهِ    سَجَدَ المَوجُ خُشوعاً وَاِحتِشاما
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal,literal · الغشري: سبحانه كلُّ له هاطع    سَبَّحَهُ البحرُ مع الساحلِ
- after · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · أبو الحسن الكاتب: انظر إلى البحر وأمواجه    فقد علاها زبد متسق
- after · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · حافظ ابراهيم: كُلَّما أَوفَت عَلى أَمواجِهِ    سَجَدَ المَوجُ خُشوعاً وَاِحتِشاما
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal,literal · الغشري: سبحانه كلُّ له هاطع    سَبَّحَهُ البحرُ مع الساحلِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.057 → 0.811 · literal,literal · محمد عبد المطلب: سالمتها الرياح فالبحر ساجٍ    لا ترى فيه غير لَمع الحَباب
- before · tier 1 · E 1.00 V 1.0 T 0.049 → 0.810 · literal,literal · الحبسي: تجرى به في البحر في أمانِ    تجرى بريح رحمةِ الرحمنِ
- before · tier 1 · E 1.00 V 1.0 T 0.044 → 0.809 · literal,literal · ابن فُركون: وقد أشْبَهَ البحْرُ مرآةَ هِندٍ    تُريكَ علَى البُعْدِ منْها مِثالا
- after · tier 1 · E 1.00 V 1.0 T 0.057 → 0.811 · literal,literal · محمد عبد المطلب: سالمتها الرياح فالبحر ساجٍ    لا ترى فيه غير لَمع الحَباب
- after · tier 1 · E 1.00 V 1.0 T 0.049 → 0.810 · literal,literal · الحبسي: تجرى به في البحر في أمانِ    تجرى بريح رحمةِ الرحمنِ
- after · tier 1 · E 1.00 V 1.0 T 0.044 → 0.809 · literal,literal · ابن فُركون: وقد أشْبَهَ البحْرُ مرآةَ هِندٍ    تُريكَ علَى البُعْدِ منْها مِثالا

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.123 → 0.825 · literal,literal · لسان الدين بن الخطيب: أأبْصَرْتَنا كالشُّهْبِ والشّمْسِ فِتيةً    تَهَلَّلَ منّا البَرُّ والبَحْرُ ذو المَوْجِ
- before · tier 1 · E 1.00 V 1.0 T 0.106 → 0.821 · literal,literal · علي محمود طه: فإذا البحر يرقصُ الموج فيه    وإذا الطير صُدَّحٌ في الروابي
- before · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal,literal · الرقيق القيرواني: وفي سر دوس مستراد وملعب    إلى وير مرحنا إلى ساحل البحر
- after · tier 1 · E 1.00 V 1.0 T 0.123 → 0.825 · literal,literal · لسان الدين بن الخطيب: أأبْصَرْتَنا كالشُّهْبِ والشّمْسِ فِتيةً    تَهَلَّلَ منّا البَرُّ والبَحْرُ ذو المَوْجِ
- after · tier 1 · E 1.00 V 1.0 T 0.106 → 0.821 · literal,literal · علي محمود طه: فإذا البحر يرقصُ الموج فيه    وإذا الطير صُدَّحٌ في الروابي
- after · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal,literal · الرقيق القيرواني: وفي سر دوس مستراد وملعب    إلى وير مرحنا إلى ساحل البحر

## desert · img:places365_sample:Places365_val_00000907 (desert/sand)

- Scene: before desert 0.98 (confident); after desert 0.98 (confident)
- Image emotion top-3: before awe 0.896, contentment 0.073, excitement 0.023 (clear); after awe 0.896, contentment 0.073, excitement 0.023 (clear)
- Suggested literary emotion: before ['awe']; after ['awe']
- Confirmed visual items (app suggestion): before ['scene_group.desert', 'tag.horse']; after ['scene_group.desert', 'tag.horse']

**longing · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 0.35 T 0.0 → 0.573 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ
- after · tier 1 · E 1.00 V 0.35 T 0.0 → 0.573 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal,literal · التهامي: بَكيتُ فَحَنَّت ناقَتي فَأَجابَها    صَهيل جوادي حينَ لاحَت دِيارُها
- before · tier 1 · E 1.00 V 0.5 T 0.079 → 0.641 · literal · امرؤ القَيس: لِمَن طَلَلٌ بَينَ الجُدَيَّةِ والجبَل    مَحَلٌ قَدِيمُ العَهدِ طَالَت بِهِ الطِّيَل
- before · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · عَبيد بن الأبرَص: أَمِن مَنزِلٍ عافٍ وَمِن رَسمِ أَطلالِ    بَكيتَ وَهَل يَبكي مِنَ الشَوقِ أَمثالي
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal,literal · التهامي: بَكيتُ فَحَنَّت ناقَتي فَأَجابَها    صَهيل جوادي حينَ لاحَت دِيارُها
- after · tier 1 · E 1.00 V 0.5 T 0.079 → 0.641 · literal · امرؤ القَيس: لِمَن طَلَلٌ بَينَ الجُدَيَّةِ والجبَل    مَحَلٌ قَدِيمُ العَهدِ طَالَت بِهِ الطِّيَل
- after · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · عَبيد بن الأبرَص: أَمِن مَنزِلٍ عافٍ وَمِن رَسمِ أَطلالِ    بَكيتَ وَهَل يَبكي مِنَ الشَوقِ أَمثالي

**sadness · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 0.35 T 0.0 → 0.393 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ
- after · tier 1 · E 0.60 V 0.35 T 0.0 → 0.393 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.18 → 0.661 · literal · الستالي: رحلت ظُعُنٌ ونأَت شجن    وخلت دِمنٌ وعَفا طلَلُ
- before · tier 1 · E 1.00 V 0.5 T 0.097 → 0.644 · literal · سلامة القس: يا صاحب القبر الغريب    بالشام في طرف الكثيب
- before · tier 1 · E 1.00 V 0.5 T 0.069 → 0.639 · literal · العكوك: خَلَّفتَني نِضوَ أَحزان أُعالِجُها    بِالجِزعِ أندُبُ في أَنضاءِ أَطلال
- after · tier 1 · E 1.00 V 0.5 T 0.18 → 0.661 · literal · الستالي: رحلت ظُعُنٌ ونأَت شجن    وخلت دِمنٌ وعَفا طلَلُ
- after · tier 1 · E 1.00 V 0.5 T 0.097 → 0.644 · literal · سلامة القس: يا صاحب القبر الغريب    بالشام في طرف الكثيب
- after · tier 1 · E 1.00 V 0.5 T 0.069 → 0.639 · literal · العكوك: خَلَّفتَني نِضوَ أَحزان أُعالِجُها    بِالجِزعِ أندُبُ في أَنضاءِ أَطلال

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.14 → 0.653 · literal · صيفي بن الأسلَت: وله الوحش بالفلاة تراها    في حقاف وفي ظلال الرمال
- before · tier 1 · E 0.60 V 1.0 T 0.099 → 0.640 · literal,literal · عبد الله الشقراطسي: والخيل تختال زهوا في أعِنّتها    والعيس تنثال زهواً من ثنى الوجل
- before · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · النابِغَة الذُبياني: تَرى كُلَّ ذَيّالٍ يُعارِضُ رَبرَباً    عَلى كُلِّ رَجّافٍ مِنَ الرَملِ هائِلِ
- after · tier 1 · E 1.00 V 0.5 T 0.14 → 0.653 · literal · صيفي بن الأسلَت: وله الوحش بالفلاة تراها    في حقاف وفي ظلال الرمال
- after · tier 1 · E 0.60 V 1.0 T 0.099 → 0.640 · literal,literal · عبد الله الشقراطسي: والخيل تختال زهوا في أعِنّتها    والعيس تنثال زهواً من ثنى الوجل
- after · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · النابِغَة الذُبياني: تَرى كُلَّ ذَيّالٍ يُعارِضُ رَبرَباً    عَلى كُلِّ رَجّافٍ مِنَ الرَملِ هائِلِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.079 → 0.641 · literal · امرؤ القَيس: فَجُزِيتِ خَيرَ جَزاءِ ناقَةِ واحِدٍ    وَرَجَعتِ سالِمَةَ القَرا بِسَلامِ
- before · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · علي محمود طه: ورمى البدرُ بالأشعةِ تبدو    فوق وجه الرمالِ منعكساتِ
- before · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · الغشري: وخفَّضَ المزنُ جناحيهْ ما    بين الكثيب والصفا والمراحْ
- after · tier 1 · E 1.00 V 0.5 T 0.079 → 0.641 · literal · امرؤ القَيس: فَجُزِيتِ خَيرَ جَزاءِ ناقَةِ واحِدٍ    وَرَجَعتِ سالِمَةَ القَرا بِسَلامِ
- after · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · علي محمود طه: ورمى البدرُ بالأشعةِ تبدو    فوق وجه الرمالِ منعكساتِ
- after · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · الغشري: وخفَّضَ المزنُ جناحيهْ ما    بين الكثيب والصفا والمراحْ

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal,literal · عبد الله الشقراطسي: والخيل تختال زهوا في أعِنّتها    والعيس تنثال زهواً من ثنى الوجل
- before · tier 1 · E 1.00 V 0.5 T 0.13 → 0.651 · literal · ناصح الدين الأرجاني: وغَنّى وراء الرّكبِ حادٍ مُطَرّبٌ    يُزعزِعُ من أعطافِ نُوقٍ مَطارب
- before · tier 1 · E 1.00 V 0.5 T 0.064 → 0.638 · literal · الصنوبري: نَشْرُ الربيعِ على الصحراءِ مَنْثُورُ    ومسكُ آذارَ فوقَ الأرض مَذْرُورُ
- after · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal,literal · عبد الله الشقراطسي: والخيل تختال زهوا في أعِنّتها    والعيس تنثال زهواً من ثنى الوجل
- after · tier 1 · E 1.00 V 0.5 T 0.13 → 0.651 · literal · ناصح الدين الأرجاني: وغَنّى وراء الرّكبِ حادٍ مُطَرّبٌ    يُزعزِعُ من أعطافِ نُوقٍ مَطارب
- after · tier 1 · E 1.00 V 0.5 T 0.064 → 0.638 · literal · الصنوبري: نَشْرُ الربيعِ على الصحراءِ مَنْثُورُ    ومسكُ آذارَ فوقَ الأرض مَذْرُورُ

## desert · img:places365_sample:Places365_val_00001064 (desert/sand)

- Scene: before desert 0.73 (confident); after desert 0.73 (confident)
- Image emotion top-3: before sadness 0.718, anger 0.087, amusement 0.053 (clear); after sadness 0.718, anger 0.087, amusement 0.053 (clear)
- Suggested literary emotion: before ['sadness']; after ['sadness']
- Confirmed visual items (app suggestion): before ['scene_group.desert', 'tag.road']; after ['scene_group.desert', 'tag.road']

**longing · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 0.35 T 0.0 → 0.573 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ
- after · tier 1 · E 1.00 V 0.35 T 0.0 → 0.573 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.148 → 0.655 · literal · سِبطِ اِبنِ التَعاويذي: وَهَل مِن سَبيلٍ وَالأَماني تَعِلَّةٌ    إِلى مَعهَدٍ بِالرَملِ طالَ بِهِ عَهدي
- before · tier 1 · E 1.00 V 0.5 T 0.077 → 0.640 · literal · امرؤ القَيس: لِمَن طَلَلٌ بَينَ الجُدَيَّةِ والجبَل    مَحَلٌ قَدِيمُ العَهدِ طَالَت بِهِ الطِّيَل
- before · tier 1 · E 1.00 V 0.5 T 0.066 → 0.638 · literal · عَبيد بن الأبرَص: أَمِن مَنزِلٍ عافٍ وَمِن رَسمِ أَطلالِ    بَكيتَ وَهَل يَبكي مِنَ الشَوقِ أَمثالي
- after · tier 1 · E 1.00 V 0.5 T 0.148 → 0.655 · literal · سِبطِ اِبنِ التَعاويذي: وَهَل مِن سَبيلٍ وَالأَماني تَعِلَّةٌ    إِلى مَعهَدٍ بِالرَملِ طالَ بِهِ عَهدي
- after · tier 1 · E 1.00 V 0.5 T 0.077 → 0.640 · literal · امرؤ القَيس: لِمَن طَلَلٌ بَينَ الجُدَيَّةِ والجبَل    مَحَلٌ قَدِيمُ العَهدِ طَالَت بِهِ الطِّيَل
- after · tier 1 · E 1.00 V 0.5 T 0.066 → 0.638 · literal · عَبيد بن الأبرَص: أَمِن مَنزِلٍ عافٍ وَمِن رَسمِ أَطلالِ    بَكيتَ وَهَل يَبكي مِنَ الشَوقِ أَمثالي

**sadness · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 0.35 T 0.0 → 0.393 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ
- after · tier 1 · E 0.60 V 0.35 T 0.0 → 0.393 · scene_association · المُتَنَبّي: لَكِ يا مَنازِلُ في القُلوبِ مَنازِلُ    أَقفَرتِ أَنتِ وَهُنَّ مِنكِ أَواهِلُ

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.179 → 0.661 · literal · الستالي: رحلت ظُعُنٌ ونأَت شجن    وخلت دِمنٌ وعَفا طلَلُ
- before · tier 1 · E 1.00 V 0.5 T 0.095 → 0.644 · literal · سلامة القس: يا صاحب القبر الغريب    بالشام في طرف الكثيب
- before · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · العكوك: خَلَّفتَني نِضوَ أَحزان أُعالِجُها    بِالجِزعِ أندُبُ في أَنضاءِ أَطلال
- after · tier 1 · E 1.00 V 0.5 T 0.179 → 0.661 · literal · الستالي: رحلت ظُعُنٌ ونأَت شجن    وخلت دِمنٌ وعَفا طلَلُ
- after · tier 1 · E 1.00 V 0.5 T 0.095 → 0.644 · literal · سلامة القس: يا صاحب القبر الغريب    بالشام في طرف الكثيب
- after · tier 1 · E 1.00 V 0.5 T 0.068 → 0.639 · literal · العكوك: خَلَّفتَني نِضوَ أَحزان أُعالِجُها    بِالجِزعِ أندُبُ في أَنضاءِ أَطلال

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.137 → 0.652 · literal · صيفي بن الأسلَت: وله الوحش بالفلاة تراها    في حقاف وفي ظلال الرمال
- before · tier 1 · E 1.00 V 0.5 T 0.071 → 0.639 · literal · عَبدَةِ بنِ الطَبيب: مِن دونِها لِعِتاقِ العيسِ إِن طَلَبَت    خَبتٌ بَعيدٌ نِياطُ الماءِ مَجهولُ
- before · tier 1 · E 1.00 V 0.5 T 0.066 → 0.638 · literal · الصاحب بن عباد: وَاِجنَب إِلى الصَحراءِ بِالبَقيعِ    فَثَمَّ أَرضُ الشرفِ الرَفيعِ
- after · tier 1 · E 1.00 V 0.5 T 0.137 → 0.652 · literal · صيفي بن الأسلَت: وله الوحش بالفلاة تراها    في حقاف وفي ظلال الرمال
- after · tier 1 · E 1.00 V 0.5 T 0.071 → 0.639 · literal · عَبدَةِ بنِ الطَبيب: مِن دونِها لِعِتاقِ العيسِ إِن طَلَبَت    خَبتٌ بَعيدٌ نِياطُ الماءِ مَجهولُ
- after · tier 1 · E 1.00 V 0.5 T 0.066 → 0.638 · literal · الصاحب بن عباد: وَاِجنَب إِلى الصَحراءِ بِالبَقيعِ    فَثَمَّ أَرضُ الشرفِ الرَفيعِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · امرؤ القَيس: فَجُزِيتِ خَيرَ جَزاءِ ناقَةِ واحِدٍ    وَرَجَعتِ سالِمَةَ القَرا بِسَلامِ
- before · tier 1 · E 1.00 V 0.5 T 0.076 → 0.640 · literal · علي محمود طه: ورمى البدرُ بالأشعةِ تبدو    فوق وجه الرمالِ منعكساتِ
- before · tier 1 · E 1.00 V 0.5 T 0.067 → 0.638 · literal · الغشري: وخفَّضَ المزنُ جناحيهْ ما    بين الكثيب والصفا والمراحْ
- after · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · امرؤ القَيس: فَجُزِيتِ خَيرَ جَزاءِ ناقَةِ واحِدٍ    وَرَجَعتِ سالِمَةَ القَرا بِسَلامِ
- after · tier 1 · E 1.00 V 0.5 T 0.076 → 0.640 · literal · علي محمود طه: ورمى البدرُ بالأشعةِ تبدو    فوق وجه الرمالِ منعكساتِ
- after · tier 1 · E 1.00 V 0.5 T 0.067 → 0.638 · literal · الغشري: وخفَّضَ المزنُ جناحيهْ ما    بين الكثيب والصفا والمراحْ

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.128 → 0.651 · literal · ناصح الدين الأرجاني: وغَنّى وراء الرّكبِ حادٍ مُطَرّبٌ    يُزعزِعُ من أعطافِ نُوقٍ مَطارب
- before · tier 1 · E 1.00 V 0.5 T 0.063 → 0.638 · literal · الصنوبري: نَشْرُ الربيعِ على الصحراءِ مَنْثُورُ    ومسكُ آذارَ فوقَ الأرض مَذْرُورُ
- before · tier 1 · E 1.00 V 0.5 T 0.057 → 0.636 · literal · صردر بن صربعر: وقفةٌ بالركابِ تُجمعُ فيها    فرحةٌ لي وراحةٌ للرَّكْبِ
- after · tier 1 · E 1.00 V 0.5 T 0.128 → 0.651 · literal · ناصح الدين الأرجاني: وغَنّى وراء الرّكبِ حادٍ مُطَرّبٌ    يُزعزِعُ من أعطافِ نُوقٍ مَطارب
- after · tier 1 · E 1.00 V 0.5 T 0.063 → 0.638 · literal · الصنوبري: نَشْرُ الربيعِ على الصحراءِ مَنْثُورُ    ومسكُ آذارَ فوقَ الأرض مَذْرُورُ
- after · tier 1 · E 1.00 V 0.5 T 0.057 → 0.636 · literal · صردر بن صربعر: وقفةٌ بالركابِ تُجمعُ فيها    فرحةٌ لي وراحةٌ للرَّكْبِ

## sky_sunset_stars · img:places365_sample:Places365_val_00000942 (sky)

- Scene: before sea_coast 0.84 (confident); after sea_coast 0.84 (confident)
- Image emotion top-3: before awe 0.979, sadness 0.011, contentment 0.007 (clear); after awe 0.979, sadness 0.011, contentment 0.007 (clear)
- Suggested literary emotion: before ['awe']; after ['awe']
- Confirmed visual items (app suggestion): before ['scene_group.sea', 'tag.sea']; after ['scene_group.sea', 'tag.sea']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.183 → 0.837 · literal,literal · ابن رشيق القيرواني: وَلَقَدْ ذَكَرْتُكِ في السَّفينَةِ والرَّدى    مُتَوَقَّعٌ بِتَلاطُمِ الأَمْواجِ
- before · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal,literal · ظافر الحداد: سلامٌ على القَصْرَين من مَنْشَأ الصَّبا    إلى ساحل الثَّغرِ المُطِلِّ على البحرِ
- before · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal,literal · محمود سامي البارودي: فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ
- after · tier 1 · E 1.00 V 1.0 T 0.183 → 0.837 · literal,literal · ابن رشيق القيرواني: وَلَقَدْ ذَكَرْتُكِ في السَّفينَةِ والرَّدى    مُتَوَقَّعٌ بِتَلاطُمِ الأَمْواجِ
- after · tier 1 · E 1.00 V 1.0 T 0.11 → 0.822 · literal,literal · ظافر الحداد: سلامٌ على القَصْرَين من مَنْشَأ الصَّبا    إلى ساحل الثَّغرِ المُطِلِّ على البحرِ
- after · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal,literal · محمود سامي البارودي: فَيَا لَكَ مِنْ طَيْفٍ أَلَمَّ وَدُونَهُ    مُحِيطٌ مِنَ الْبَحْرِ الْجَنُوبِيِّ زَاخِرُ

**sadness · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 0.5 T 0.379 → 0.521 · literal · خليل مطران: شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ
- after · tier 1 · E 0.60 V 0.5 T 0.379 → 0.521 · literal · خليل مطران: شاكٍ إِلى البَحْرِ اضْطَرابَ خَوَاطِرِي    فَيُجِيبُنِي بِرِيَاحِهِ الهَوْجَاءِ

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.192 → 0.838 · literal,literal · جميل صدقي الزهاوي: لا ينبغي ان يكون البحر قاتله    ان كان للبحر ذي الامواج وجدان
- before · tier 1 · E 1.00 V 1.0 T 0.098 → 0.820 · literal,literal · ابن حمديس: عانَقَهَا الموجُ ثمّ فارقَها    عن ضَمّةٍ فاضَ روحها فيها
- before · tier 1 · E 1.00 V 1.0 T 0.097 → 0.819 · literal,literal · أبو القاسم الشابي: على ساحِلِ البَحْرِ أَنَّى يضجُّ    صُراخُ الصَّباحِ ونَوْحُ المَسَا
- after · tier 1 · E 1.00 V 1.0 T 0.192 → 0.838 · literal,literal · جميل صدقي الزهاوي: لا ينبغي ان يكون البحر قاتله    ان كان للبحر ذي الامواج وجدان
- after · tier 1 · E 1.00 V 1.0 T 0.098 → 0.820 · literal,literal · ابن حمديس: عانَقَهَا الموجُ ثمّ فارقَها    عن ضَمّةٍ فاضَ روحها فيها
- after · tier 1 · E 1.00 V 1.0 T 0.097 → 0.819 · literal,literal · أبو القاسم الشابي: على ساحِلِ البَحْرِ أَنَّى يضجُّ    صُراخُ الصَّباحِ ونَوْحُ المَسَا

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · أبو الحسن الكاتب: انظر إلى البحر وأمواجه    فقد علاها زبد متسق
- before · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · حافظ ابراهيم: كُلَّما أَوفَت عَلى أَمواجِهِ    سَجَدَ المَوجُ خُشوعاً وَاِحتِشاما
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal,literal · الغشري: سبحانه كلُّ له هاطع    سَبَّحَهُ البحرُ مع الساحلِ
- after · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · أبو الحسن الكاتب: انظر إلى البحر وأمواجه    فقد علاها زبد متسق
- after · tier 1 · E 1.00 V 1.0 T 0.129 → 0.826 · literal,literal · حافظ ابراهيم: كُلَّما أَوفَت عَلى أَمواجِهِ    سَجَدَ المَوجُ خُشوعاً وَاِحتِشاما
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal,literal · الغشري: سبحانه كلُّ له هاطع    سَبَّحَهُ البحرُ مع الساحلِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.057 → 0.811 · literal,literal · محمد عبد المطلب: سالمتها الرياح فالبحر ساجٍ    لا ترى فيه غير لَمع الحَباب
- before · tier 1 · E 1.00 V 1.0 T 0.049 → 0.810 · literal,literal · الحبسي: تجرى به في البحر في أمانِ    تجرى بريح رحمةِ الرحمنِ
- before · tier 1 · E 1.00 V 1.0 T 0.044 → 0.809 · literal,literal · ابن فُركون: وقد أشْبَهَ البحْرُ مرآةَ هِندٍ    تُريكَ علَى البُعْدِ منْها مِثالا
- after · tier 1 · E 1.00 V 1.0 T 0.057 → 0.811 · literal,literal · محمد عبد المطلب: سالمتها الرياح فالبحر ساجٍ    لا ترى فيه غير لَمع الحَباب
- after · tier 1 · E 1.00 V 1.0 T 0.049 → 0.810 · literal,literal · الحبسي: تجرى به في البحر في أمانِ    تجرى بريح رحمةِ الرحمنِ
- after · tier 1 · E 1.00 V 1.0 T 0.044 → 0.809 · literal,literal · ابن فُركون: وقد أشْبَهَ البحْرُ مرآةَ هِندٍ    تُريكَ علَى البُعْدِ منْها مِثالا

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.123 → 0.825 · literal,literal · لسان الدين بن الخطيب: أأبْصَرْتَنا كالشُّهْبِ والشّمْسِ فِتيةً    تَهَلَّلَ منّا البَرُّ والبَحْرُ ذو المَوْجِ
- before · tier 1 · E 1.00 V 1.0 T 0.106 → 0.821 · literal,literal · علي محمود طه: فإذا البحر يرقصُ الموج فيه    وإذا الطير صُدَّحٌ في الروابي
- before · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal,literal · الرقيق القيرواني: وفي سر دوس مستراد وملعب    إلى وير مرحنا إلى ساحل البحر
- after · tier 1 · E 1.00 V 1.0 T 0.123 → 0.825 · literal,literal · لسان الدين بن الخطيب: أأبْصَرْتَنا كالشُّهْبِ والشّمْسِ فِتيةً    تَهَلَّلَ منّا البَرُّ والبَحْرُ ذو المَوْجِ
- after · tier 1 · E 1.00 V 1.0 T 0.106 → 0.821 · literal,literal · علي محمود طه: فإذا البحر يرقصُ الموج فيه    وإذا الطير صُدَّحٌ في الروابي
- after · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal,literal · الرقيق القيرواني: وفي سر دوس مستراد وملعب    إلى وير مرحنا إلى ساحل البحر

## sky_sunset_stars · img:places365_sample:Places365_val_00001270 (sky)

- Scene: before sky 0.99 (confident); after sky 0.99 (confident)
- Image emotion top-3: before awe 0.986, contentment 0.007, sadness 0.003 (clear); after awe 0.986, contentment 0.007, sadness 0.003 (clear)
- Suggested literary emotion: before ['awe']; after ['awe']
- Confirmed visual items (app suggestion): before ['scene_group.sky_night']; after ['scene_group.sky_night']

**longing · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 1.0 T 0.0 → 0.620 · literal · الخَنساء: يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ
- after · tier 1 · E 0.60 V 1.0 T 0.0 → 0.620 · literal · الخَنساء: يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.144 → 0.829 · literal · القاضي الفاضل: ذَكَرتُ وُجوهَكُم وَالبَدرُ يَسري    كِلا البَدرَينِ مَسكَنُهُ السَحابُ
- before · tier 1 · E 1.00 V 1.0 T 0.088 → 0.818 · literal · ابن نباتة السعدي: كأَنَّ نجومَ الليلِ بعدَ فراقهم    أَقامتْ على آثارهم تَتَردَّدُ
- before · tier 1 · E 1.00 V 1.0 T 0.078 → 0.816 · literal · ابن زيدون: إِنّي ذَكَرتُكِ بِازَهراءَ مُشتاقاً    وَالأُفقُ طَلقٌ وَمَرأى الأَرضِ قَد راقا
- after · tier 1 · E 1.00 V 1.0 T 0.144 → 0.829 · literal · القاضي الفاضل: ذَكَرتُ وُجوهَكُم وَالبَدرُ يَسري    كِلا البَدرَينِ مَسكَنُهُ السَحابُ
- after · tier 1 · E 1.00 V 1.0 T 0.088 → 0.818 · literal · ابن نباتة السعدي: كأَنَّ نجومَ الليلِ بعدَ فراقهم    أَقامتْ على آثارهم تَتَردَّدُ
- after · tier 1 · E 1.00 V 1.0 T 0.078 → 0.816 · literal · ابن زيدون: إِنّي ذَكَرتُكِ بِازَهراءَ مُشتاقاً    وَالأُفقُ طَلقٌ وَمَرأى الأَرضِ قَد راقا

**sadness · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · الخَنساء: يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ
- before · tier 1 · E 0.60 V 1.0 T 0.139 → 0.648 · literal · ابن الرومي: إذا رنَّقت شمسُ الأصيل ونفَّضت    على الأفق الغربيِّ ورساً مذعذعا
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · الخَنساء: يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ
- after · tier 1 · E 0.60 V 1.0 T 0.139 → 0.648 · literal · ابن الرومي: إذا رنَّقت شمسُ الأصيل ونفَّضت    على الأفق الغربيِّ ورساً مذعذعا

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · رشيد أيوب: تائِهاً في الليلِ ما بينَ الصّخور    عندَ شاطي البَحرِ في ضَوءِ القمر
- before · tier 1 · E 1.00 V 1.0 T 0.108 → 0.822 · literal · عبيدة اليشكري: إِذا ذَكَرَت نَفسي مَعَ اللَيلِ مُحرِزاً    تَأَوَّهتُ مِن حُزنٍ عَلَيهِ إِلى الفَجرِ
- before · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal · جَرير: فَالشَمسُ كاسِفَةٌ لَيسَت بِطالِعَةٍ    تَبكي عَلَيكَ نُجومَ اللَيلِ وَالقَمَرا
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · رشيد أيوب: تائِهاً في الليلِ ما بينَ الصّخور    عندَ شاطي البَحرِ في ضَوءِ القمر
- after · tier 1 · E 1.00 V 1.0 T 0.108 → 0.822 · literal · عبيدة اليشكري: إِذا ذَكَرَت نَفسي مَعَ اللَيلِ مُحرِزاً    تَأَوَّهتُ مِن حُزنٍ عَلَيهِ إِلى الفَجرِ
- after · tier 1 · E 1.00 V 1.0 T 0.099 → 0.820 · literal · جَرير: فَالشَمسُ كاسِفَةٌ لَيسَت بِطالِعَةٍ    تَبكي عَلَيكَ نُجومَ اللَيلِ وَالقَمَرا

**awe · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.142 → 0.828 · literal · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ
- after · tier 1 · E 1.00 V 1.0 T 0.142 → 0.828 · literal · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.141 → 0.828 · literal · حازم القرطاجني: سبحانَ من سبَّحت شمسُ النهار له    والبدرُ بدرُ الدُّجى والشهبُ في الظلم
- before · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · الأمير الصنعاني: تبين ثغر الفجر لما تبسما    فسبحان من في الذكر بالفجر أقسما
- before · tier 1 · E 1.00 V 1.0 T 0.1 → 0.820 · literal · أَبو العَلاء المَعَرِي: فَيا عَجَبا لِلشَمسِ تُنشَرُ بِالضُحى    وَتُطوى الدُجى وَالبَدرُ يَنمو وَيُهزَلُ
- after · tier 1 · E 1.00 V 1.0 T 0.141 → 0.828 · literal · حازم القرطاجني: سبحانَ من سبَّحت شمسُ النهار له    والبدرُ بدرُ الدُّجى والشهبُ في الظلم
- after · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · الأمير الصنعاني: تبين ثغر الفجر لما تبسما    فسبحان من في الذكر بالفجر أقسما
- after · tier 1 · E 1.00 V 1.0 T 0.1 → 0.820 · literal · أَبو العَلاء المَعَرِي: فَيا عَجَبا لِلشَمسِ تُنشَرُ بِالضُحى    وَتُطوى الدُجى وَالبَدرُ يَنمو وَيُهزَلُ

**serenity · production** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.139 → 0.828 · literal · ابن الرومي: إذا رنَّقت شمسُ الأصيل ونفَّضت    على الأفق الغربيِّ ورساً مذعذعا
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · أَبو تَمّام: مَطَرٌ يَذوبُ الصَحوُ مِنهُ وَبَعدَهُ    صَحوٌ يَكادُ مِنَ الغَضارَةِ يُمطِرُ
- before · tier 1 · E 1.00 V 0.7 T 0.0 → 0.695 · scene_association · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 1 · E 1.00 V 1.0 T 0.139 → 0.828 · literal · ابن الرومي: إذا رنَّقت شمسُ الأصيل ونفَّضت    على الأفق الغربيِّ ورساً مذعذعا
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · أَبو تَمّام: مَطَرٌ يَذوبُ الصَحوُ مِنهُ وَبَعدَهُ    صَحوٌ يَكادُ مِنَ الغَضارَةِ يُمطِرُ
- after · tier 1 · E 1.00 V 0.7 T 0.0 → 0.695 · scene_association · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.157 → 0.831 · literal · ابن الأبار: والثرَيا بجانِب البَدْرِ تحْكي    راحَةً أوْمَأَتْ لِتَلْطِمَ خَدا
- before · tier 1 · E 1.00 V 1.0 T 0.137 → 0.827 · literal · ابن زَمرَك: وكأنما خمسُ الثريا راحَةٌ    ذرعَتْ مسير الليل بالأَشبارِ
- before · tier 1 · E 1.00 V 1.0 T 0.081 → 0.816 · literal · إبراهيم ناجي: عرفتكِ هادئاً والفجر غافٍ    كأَنَّ البحر وَسَّدَه فناما
- after · tier 1 · E 1.00 V 1.0 T 0.157 → 0.831 · literal · ابن الأبار: والثرَيا بجانِب البَدْرِ تحْكي    راحَةً أوْمَأَتْ لِتَلْطِمَ خَدا
- after · tier 1 · E 1.00 V 1.0 T 0.137 → 0.827 · literal · ابن زَمرَك: وكأنما خمسُ الثريا راحَةٌ    ذرعَتْ مسير الليل بالأَشبارِ
- after · tier 1 · E 1.00 V 1.0 T 0.081 → 0.816 · literal · إبراهيم ناجي: عرفتكِ هادئاً والفجر غافٍ    كأَنَّ البحر وَسَّدَه فناما

**joy · production** — before `partial`, after `partial`
- before · tier 1 · E 0.60 V 1.0 T 0.0 → 0.620 · literal · أَبو تَمّام: مَطَرٌ يَذوبُ الصَحوُ مِنهُ وَبَعدَهُ    صَحوٌ يَكادُ مِنَ الغَضارَةِ يُمطِرُ
- before · tier 1 · E 0.60 V 0.7 T 0.0 → 0.515 · scene_association · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 1 · E 0.60 V 1.0 T 0.0 → 0.620 · literal · أَبو تَمّام: مَطَرٌ يَذوبُ الصَحوُ مِنهُ وَبَعدَهُ    صَحوٌ يَكادُ مِنَ الغَضارَةِ يُمطِرُ
- after · tier 1 · E 0.60 V 0.7 T 0.0 → 0.515 · scene_association · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.183 → 0.837 · literal · أبو القاسم الشابي: في فتنة الشَّفقِ البَديعِ    وفي النُّجُومِ البَاسمهْ
- before · tier 1 · E 1.00 V 1.0 T 0.177 → 0.835 · literal · أبو هلال العسكري: وَاِنشَقَّ ثَوبُ الظَلامِ عَن قَمَرٍ    يَضحَكُ في أَوجُهِ الدُجُنّاتِ
- before · tier 1 · E 1.00 V 1.0 T 0.135 → 0.827 · literal · ابن معتوق الموسوي: فلَقَ الدُجى بعَمودِه الفجرُ    وبكى النّدى وتبسّمَ الزّهرُ
- after · tier 1 · E 1.00 V 1.0 T 0.183 → 0.837 · literal · أبو القاسم الشابي: في فتنة الشَّفقِ البَديعِ    وفي النُّجُومِ البَاسمهْ
- after · tier 1 · E 1.00 V 1.0 T 0.177 → 0.835 · literal · أبو هلال العسكري: وَاِنشَقَّ ثَوبُ الظَلامِ عَن قَمَرٍ    يَضحَكُ في أَوجُهِ الدُجُنّاتِ
- after · tier 1 · E 1.00 V 1.0 T 0.135 → 0.827 · literal · ابن معتوق الموسوي: فلَقَ الدُجى بعَمودِه الفجرُ    وبكى النّدى وتبسّمَ الزّهرُ

## greenery · img:places365_sample:Places365_val_00000549 (formal_garden)

- Scene: before garden 0.94 (confident); after garden 0.94 (confident)
- Image emotion top-3: before awe 0.578, contentment 0.259, amusement 0.117 (clear); after awe 0.578, contentment 0.259, amusement 0.117 (clear)
- Suggested literary emotion: before ['awe', 'serenity']; after ['awe', 'serenity']
- Confirmed visual items (app suggestion): before ['scene_group.greenery']; after ['scene_group.greenery']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · ابن لؤلؤ: أحن إلى الأزهار ما هبت الصبا    وما ناحَ في الأيكِ الحمامُ المطوقُ
- before · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · الشاب الظريف: ما نَاحَ حَمامُ الأَيْكِ فِي الأَغْصانِ    إِلَّا وَتَزايَدتْ بِكُمْ أَشْجاني
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · عمرو بن شأس الأسدي: تَذَكَّرتُها وَهناً وَقَد حالَ دونَها    رِعانٌ وَقيعانٌ بِها الزَهرُ وَالشَجَر
- after · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · ابن لؤلؤ: أحن إلى الأزهار ما هبت الصبا    وما ناحَ في الأيكِ الحمامُ المطوقُ
- after · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · الشاب الظريف: ما نَاحَ حَمامُ الأَيْكِ فِي الأَغْصانِ    إِلَّا وَتَزايَدتْ بِكُمْ أَشْجاني
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · عمرو بن شأس الأسدي: تَذَكَّرتُها وَهناً وَقَد حالَ دونَها    رِعانٌ وَقيعانٌ بِها الزَهرُ وَالشَجَر

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · اللواح: أنوح في نخل نوح الحمائم في    فن من الأيك أو رأسي من النخل
- before · tier 1 · E 1.00 V 1.0 T 0.18 → 0.836 · literal · المعتمد بن عباد: يَبكي لَها القَصرُ المُنيفُ تلالأت    شُرَفاتُهُ في خُضرَةِ الأَشجارِ
- before · tier 1 · E 1.00 V 1.0 T 0.127 → 0.825 · literal · الخَنساء: تَذَكَّرتُ صَخراً إِذ تَغَنَّت حَمامَةٌ    هَتوفٌ عَلى غُصنٍ مِنَ الأَيكِ تَسجَعُ
- after · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · اللواح: أنوح في نخل نوح الحمائم في    فن من الأيك أو رأسي من النخل
- after · tier 1 · E 1.00 V 1.0 T 0.18 → 0.836 · literal · المعتمد بن عباد: يَبكي لَها القَصرُ المُنيفُ تلالأت    شُرَفاتُهُ في خُضرَةِ الأَشجارِ
- after · tier 1 · E 1.00 V 1.0 T 0.127 → 0.825 · literal · الخَنساء: تَذَكَّرتُ صَخراً إِذ تَغَنَّت حَمامَةٌ    هَتوفٌ عَلى غُصنٍ مِنَ الأَيكِ تَسجَعُ

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · البرعي: وَضاحك البرق أَزهار الرياض فمن    فضى مذهبها نور وَأَنوار
- before · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · ابن عنين: في رَوضَةٍ عُنِيَ الرَبيعُ بِها    فَأَبانَ صنعَةَ عِلَّةِ العِلَلِ
- before · tier 1 · E 1.00 V 1.0 T 0.104 → 0.821 · literal · سيف الدين المشد: روضة كالسماء أشرق فيها    ضاحك الزهر إذ بكته الغيوم
- after · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · البرعي: وَضاحك البرق أَزهار الرياض فمن    فضى مذهبها نور وَأَنوار
- after · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · ابن عنين: في رَوضَةٍ عُنِيَ الرَبيعُ بِها    فَأَبانَ صنعَةَ عِلَّةِ العِلَلِ
- after · tier 1 · E 1.00 V 1.0 T 0.104 → 0.821 · literal · سيف الدين المشد: روضة كالسماء أشرق فيها    ضاحك الزهر إذ بكته الغيوم

**serenity · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · ابن خفاجة: خَلَعَت عَلَيَّ بِهِ الأَراكَةُ ظِلَّها    وَالغُصنُ يُصغي وَالحَمامُ يُحَدِّثُ
- before · tier 1 · E 1.00 V 1.0 T 0.037 → 0.807 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · ابن خفاجة: خَلَعَت عَلَيَّ بِهِ الأَراكَةُ ظِلَّها    وَالغُصنُ يُصغي وَالحَمامُ يُحَدِّثُ
- after · tier 1 · E 1.00 V 1.0 T 0.037 → 0.807 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.163 → 0.833 · literal · فوزي المعلوف: في الروض زنبقة يحيط بها    ورق الربيع وباسم الزهر
- before · tier 1 · E 1.00 V 1.0 T 0.116 → 0.823 · literal · الملك الأمجد: والدوحُ مُخْضَلٌّ بقَطْرِ النَّدى    في روضةٍ غَنّاءَ مِعطارِ
- before · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · وجيه الدولة الحمداني: بحيث نسيم الغوطتين معطّر    بأنفاس زهر في الرّياض مبدّد
- after · tier 1 · E 1.00 V 1.0 T 0.163 → 0.833 · literal · فوزي المعلوف: في الروض زنبقة يحيط بها    ورق الربيع وباسم الزهر
- after · tier 1 · E 1.00 V 1.0 T 0.116 → 0.823 · literal · الملك الأمجد: والدوحُ مُخْضَلٌّ بقَطْرِ النَّدى    في روضةٍ غَنّاءَ مِعطارِ
- after · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · وجيه الدولة الحمداني: بحيث نسيم الغوطتين معطّر    بأنفاس زهر في الرّياض مبدّد

**joy · production** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.041 → 0.808 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- before · tier 1 · E 1.00 V 0.7 T 0.218 → 0.739 · scene_association · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما
- before · tier 1 · E 1.00 V 0.7 T 0.037 → 0.702 · scene_association · أَبو تَمّام: رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ
- after · tier 1 · E 1.00 V 1.0 T 0.041 → 0.808 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- after · tier 1 · E 1.00 V 0.7 T 0.218 → 0.739 · scene_association · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما
- after · tier 1 · E 1.00 V 0.7 T 0.037 → 0.702 · scene_association · أَبو تَمّام: رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.159 → 0.832 · literal · ابن عبد ربه الأندلسي : باكرِ الروضَ في رياضِ السُّرورِ    بينَ نظمِ الربيعِ والمنثورِ
- before · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · أبو فِراس الحَمَداني: أُنظُر إِلى زَهرِ الرَبيعِ    وَالماءِ في بِرَكِ البَديعِ
- before · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · فتيان الشاغوري: يا طيبَ أَزهار أَنفاسِ الرَبيعِ بِها    وَالطَيرُ تُطرِبُنا أَصواتُ شاديها
- after · tier 1 · E 1.00 V 1.0 T 0.159 → 0.832 · literal · ابن عبد ربه الأندلسي : باكرِ الروضَ في رياضِ السُّرورِ    بينَ نظمِ الربيعِ والمنثورِ
- after · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · أبو فِراس الحَمَداني: أُنظُر إِلى زَهرِ الرَبيعِ    وَالماءِ في بِرَكِ البَديعِ
- after · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · فتيان الشاغوري: يا طيبَ أَزهار أَنفاسِ الرَبيعِ بِها    وَالطَيرُ تُطرِبُنا أَصواتُ شاديها

## greenery · img:places365_sample:Places365_val_00000552 (formal_garden)

- Scene: before garden 0.99 (confident); after garden 0.99 (confident)
- Image emotion top-3: before contentment 0.632, amusement 0.256, awe 0.106 (clear); after contentment 0.632, amusement 0.256, awe 0.106 (clear)
- Suggested literary emotion: before ['serenity', 'joy']; after ['serenity', 'joy']
- Confirmed visual items (app suggestion): before ['scene_group.greenery']; after ['scene_group.greenery']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · ابن لؤلؤ: أحن إلى الأزهار ما هبت الصبا    وما ناحَ في الأيكِ الحمامُ المطوقُ
- before · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · الشاب الظريف: ما نَاحَ حَمامُ الأَيْكِ فِي الأَغْصانِ    إِلَّا وَتَزايَدتْ بِكُمْ أَشْجاني
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · عمرو بن شأس الأسدي: تَذَكَّرتُها وَهناً وَقَد حالَ دونَها    رِعانٌ وَقيعانٌ بِها الزَهرُ وَالشَجَر
- after · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · ابن لؤلؤ: أحن إلى الأزهار ما هبت الصبا    وما ناحَ في الأيكِ الحمامُ المطوقُ
- after · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · الشاب الظريف: ما نَاحَ حَمامُ الأَيْكِ فِي الأَغْصانِ    إِلَّا وَتَزايَدتْ بِكُمْ أَشْجاني
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · عمرو بن شأس الأسدي: تَذَكَّرتُها وَهناً وَقَد حالَ دونَها    رِعانٌ وَقيعانٌ بِها الزَهرُ وَالشَجَر

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · اللواح: أنوح في نخل نوح الحمائم في    فن من الأيك أو رأسي من النخل
- before · tier 1 · E 1.00 V 1.0 T 0.18 → 0.836 · literal · المعتمد بن عباد: يَبكي لَها القَصرُ المُنيفُ تلالأت    شُرَفاتُهُ في خُضرَةِ الأَشجارِ
- before · tier 1 · E 1.00 V 1.0 T 0.127 → 0.825 · literal · الخَنساء: تَذَكَّرتُ صَخراً إِذ تَغَنَّت حَمامَةٌ    هَتوفٌ عَلى غُصنٍ مِنَ الأَيكِ تَسجَعُ
- after · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · اللواح: أنوح في نخل نوح الحمائم في    فن من الأيك أو رأسي من النخل
- after · tier 1 · E 1.00 V 1.0 T 0.18 → 0.836 · literal · المعتمد بن عباد: يَبكي لَها القَصرُ المُنيفُ تلالأت    شُرَفاتُهُ في خُضرَةِ الأَشجارِ
- after · tier 1 · E 1.00 V 1.0 T 0.127 → 0.825 · literal · الخَنساء: تَذَكَّرتُ صَخراً إِذ تَغَنَّت حَمامَةٌ    هَتوفٌ عَلى غُصنٍ مِنَ الأَيكِ تَسجَعُ

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · البرعي: وَضاحك البرق أَزهار الرياض فمن    فضى مذهبها نور وَأَنوار
- before · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · ابن عنين: في رَوضَةٍ عُنِيَ الرَبيعُ بِها    فَأَبانَ صنعَةَ عِلَّةِ العِلَلِ
- before · tier 1 · E 1.00 V 1.0 T 0.104 → 0.821 · literal · سيف الدين المشد: روضة كالسماء أشرق فيها    ضاحك الزهر إذ بكته الغيوم
- after · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · البرعي: وَضاحك البرق أَزهار الرياض فمن    فضى مذهبها نور وَأَنوار
- after · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · ابن عنين: في رَوضَةٍ عُنِيَ الرَبيعُ بِها    فَأَبانَ صنعَةَ عِلَّةِ العِلَلِ
- after · tier 1 · E 1.00 V 1.0 T 0.104 → 0.821 · literal · سيف الدين المشد: روضة كالسماء أشرق فيها    ضاحك الزهر إذ بكته الغيوم

**serenity · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · ابن خفاجة: خَلَعَت عَلَيَّ بِهِ الأَراكَةُ ظِلَّها    وَالغُصنُ يُصغي وَالحَمامُ يُحَدِّثُ
- before · tier 1 · E 1.00 V 1.0 T 0.037 → 0.807 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 1 · E 1.00 V 1.0 T 0.203 → 0.841 · literal · ابن خفاجة: خَلَعَت عَلَيَّ بِهِ الأَراكَةُ ظِلَّها    وَالغُصنُ يُصغي وَالحَمامُ يُحَدِّثُ
- after · tier 1 · E 1.00 V 1.0 T 0.037 → 0.807 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.163 → 0.833 · literal · فوزي المعلوف: في الروض زنبقة يحيط بها    ورق الربيع وباسم الزهر
- before · tier 1 · E 1.00 V 1.0 T 0.116 → 0.823 · literal · الملك الأمجد: والدوحُ مُخْضَلٌّ بقَطْرِ النَّدى    في روضةٍ غَنّاءَ مِعطارِ
- before · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · وجيه الدولة الحمداني: بحيث نسيم الغوطتين معطّر    بأنفاس زهر في الرّياض مبدّد
- after · tier 1 · E 1.00 V 1.0 T 0.163 → 0.833 · literal · فوزي المعلوف: في الروض زنبقة يحيط بها    ورق الربيع وباسم الزهر
- after · tier 1 · E 1.00 V 1.0 T 0.116 → 0.823 · literal · الملك الأمجد: والدوحُ مُخْضَلٌّ بقَطْرِ النَّدى    في روضةٍ غَنّاءَ مِعطارِ
- after · tier 1 · E 1.00 V 1.0 T 0.107 → 0.821 · literal · وجيه الدولة الحمداني: بحيث نسيم الغوطتين معطّر    بأنفاس زهر في الرّياض مبدّد

**joy · production** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.041 → 0.808 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- before · tier 1 · E 1.00 V 0.7 T 0.218 → 0.739 · scene_association · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما
- before · tier 1 · E 1.00 V 0.7 T 0.037 → 0.702 · scene_association · أَبو تَمّام: رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ
- after · tier 1 · E 1.00 V 1.0 T 0.041 → 0.808 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- after · tier 1 · E 1.00 V 0.7 T 0.218 → 0.739 · scene_association · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما
- after · tier 1 · E 1.00 V 0.7 T 0.037 → 0.702 · scene_association · أَبو تَمّام: رَقَّت حَواشي الدَهرُ فَهيَ تَمَرمَرُ    وَغَدا الثَرى في حَليِهِ يَتَكَسَّرُ

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.159 → 0.832 · literal · ابن عبد ربه الأندلسي : باكرِ الروضَ في رياضِ السُّرورِ    بينَ نظمِ الربيعِ والمنثورِ
- before · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · أبو فِراس الحَمَداني: أُنظُر إِلى زَهرِ الرَبيعِ    وَالماءِ في بِرَكِ البَديعِ
- before · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · فتيان الشاغوري: يا طيبَ أَزهار أَنفاسِ الرَبيعِ بِها    وَالطَيرُ تُطرِبُنا أَصواتُ شاديها
- after · tier 1 · E 1.00 V 1.0 T 0.159 → 0.832 · literal · ابن عبد ربه الأندلسي : باكرِ الروضَ في رياضِ السُّرورِ    بينَ نظمِ الربيعِ والمنثورِ
- after · tier 1 · E 1.00 V 1.0 T 0.13 → 0.826 · literal · أبو فِراس الحَمَداني: أُنظُر إِلى زَهرِ الرَبيعِ    وَالماءِ في بِرَكِ البَديعِ
- after · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · فتيان الشاغوري: يا طيبَ أَزهار أَنفاسِ الرَبيعِ بِها    وَالطَيرُ تُطرِبُنا أَصواتُ شاديها

## heritage · img:places365_sample:Places365_val_00000111 (palace)

- Scene: before historic_monument 0.80 (confident); after historic_monument 0.80 (confident)
- Image emotion top-3: before amusement 0.543, awe 0.426, excitement 0.011 (ambiguous); after amusement 0.543, awe 0.426, excitement 0.011 (ambiguous)
- Suggested literary emotion: before ['joy', 'awe']; after []
- Confirmed visual items (app suggestion): before ['scene_group.heritage']; after ['scene_group.heritage']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.095 → 0.819 · literal · البُحتُرِيّ: يَطَّبي أَبيَضُ المَدائِنِ شَوقي    أَفَلا المَذحِجِيُّ أَو غِمدانُه
- before · tier 1 · E 1.00 V 1.0 T 0.068 → 0.814 · literal · المعتمد بن عباد: وَسَلِّم عَلى قَصر الشَراجيب عَن فَتىً    لَهُ أَبَداً شَوقٌ إِلى ذَلِكَ القَصرِ
- before · tier 1 · E 1.00 V 1.0 T 0.064 → 0.813 · literal · ولي الدين يكن: همت شوقاً ببعلبك وماسا    ءلت أطلال بعلبك زماني
- after · tier 1 · E 1.00 V 1.0 T 0.095 → 0.819 · literal · البُحتُرِيّ: يَطَّبي أَبيَضُ المَدائِنِ شَوقي    أَفَلا المَذحِجِيُّ أَو غِمدانُه
- after · tier 1 · E 1.00 V 1.0 T 0.068 → 0.814 · literal · المعتمد بن عباد: وَسَلِّم عَلى قَصر الشَراجيب عَن فَتىً    لَهُ أَبَداً شَوقٌ إِلى ذَلِكَ القَصرِ
- after · tier 1 · E 1.00 V 1.0 T 0.064 → 0.813 · literal · ولي الدين يكن: همت شوقاً ببعلبك وماسا    ءلت أطلال بعلبك زماني

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.155 → 0.831 · literal · أبو العَتاهِيَة: سَتَدرُسُ آثارٌ وَتَعقِبُ حَسرَةٌ    سَتَخلو قُصورٌ شُيِّدَت وَحُصونُ
- before · tier 1 · E 1.00 V 1.0 T 0.121 → 0.824 · literal · أبو البقاء الرندي: دارَ الزَمانُ عَلى دارا وَقاتِلِهِ    وَأَمَّ كِسرى فَما آواهُ إِيوانُ
- before · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · البُحتُرِيّ: حَضَرَت رَحلِيَ الهُمومُ فَوَجَّه    تُ إِلى أَبيَضَ المَدائِنِ عَنسي
- after · tier 1 · E 1.00 V 1.0 T 0.155 → 0.831 · literal · أبو العَتاهِيَة: سَتَدرُسُ آثارٌ وَتَعقِبُ حَسرَةٌ    سَتَخلو قُصورٌ شُيِّدَت وَحُصونُ
- after · tier 1 · E 1.00 V 1.0 T 0.121 → 0.824 · literal · أبو البقاء الرندي: دارَ الزَمانُ عَلى دارا وَقاتِلِهِ    وَأَمَّ كِسرى فَما آواهُ إِيوانُ
- after · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · البُحتُرِيّ: حَضَرَت رَحلِيَ الهُمومُ فَوَجَّه    تُ إِلى أَبيَضَ المَدائِنِ عَنسي

**awe · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · أحمد شوقي: قِف ناجِ أَهرامَ الجَلالِ وَنادِ    هَل مِن بُناتِكَ مَجلِسٌ أَو نادِ
- before · tier 1 · E 1.00 V 0.7 T 0.032 → 0.701 · scene_association · البُحتُرِيّ: لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · أحمد شوقي: قِف ناجِ أَهرامَ الجَلالِ وَنادِ    هَل مِن بُناتِكَ مَجلِسٌ أَو نادِ
- after · tier 1 · E 1.00 V 0.7 T 0.032 → 0.701 · scene_association · البُحتُرِيّ: لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · ابن زَمرَك: ولله عينا من رأى القصر حوله    منازلُ بالنصر العزيز أواهلُ
- before · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal · ابن قلاقس: خفضَ الخورنقَ والسديرَ سموُّهُ    وثنى قصورَ الروم ذاتَ قُصورِ
- before · tier 1 · E 1.00 V 1.0 T 0.071 → 0.814 · literal · البُحتُرِيّ: وَكَأَنَّ الإيوانَ مِن عَجَبِ الصَن    عَةِ جَوبٌ في جَنبِ أَرعَنَ جِلسِ
- after · tier 1 · E 1.00 V 1.0 T 0.114 → 0.823 · literal · ابن زَمرَك: ولله عينا من رأى القصر حوله    منازلُ بالنصر العزيز أواهلُ
- after · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal · ابن قلاقس: خفضَ الخورنقَ والسديرَ سموُّهُ    وثنى قصورَ الروم ذاتَ قُصورِ
- after · tier 1 · E 1.00 V 1.0 T 0.071 → 0.814 · literal · البُحتُرِيّ: وَكَأَنَّ الإيوانَ مِن عَجَبِ الصَن    عَةِ جَوبٌ في جَنبِ أَرعَنَ جِلسِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.074 → 0.815 · literal · المعولي العماني: واسلمْ سلمتَ سلامةً محروسةً    في حصن بهلا في النعيم مُخلَّدَاً
- before · tier 1 · E 1.00 V 1.0 T 0.07 → 0.814 · literal · ابن الهبارية: بغدادُ دارٌ رياضُها أُنُفُ    والغيثُ في عنفوانِها يَكفُ
- before · tier 1 · E 1.00 V 1.0 T 0.063 → 0.813 · literal · ابن قلاقس: وسرى نسيمُ الروضِ في أثنائه    أرجٌ ثناهُ الى القصورِ ثناؤه
- after · tier 1 · E 1.00 V 1.0 T 0.074 → 0.815 · literal · المعولي العماني: واسلمْ سلمتَ سلامةً محروسةً    في حصن بهلا في النعيم مُخلَّدَاً
- after · tier 1 · E 1.00 V 1.0 T 0.07 → 0.814 · literal · ابن الهبارية: بغدادُ دارٌ رياضُها أُنُفُ    والغيثُ في عنفوانِها يَكفُ
- after · tier 1 · E 1.00 V 1.0 T 0.063 → 0.813 · literal · ابن قلاقس: وسرى نسيمُ الروضِ في أثنائه    أرجٌ ثناهُ الى القصورِ ثناؤه

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.138 → 0.828 · literal · فتيان الشاغوري: دارٌ تديَّرَها السُرورُ فَقَصَّرَت    عَنها القُصورُ وَصدت فيها الصيدا
- before · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal · عماد الدين الأصبهاني: بُشرى الممالكِ فتحُ قلعةِ منبجٍ    فلْيَهْنِ هذا النصرَ كلُّ متوَّجِ
- before · tier 1 · E 1.00 V 1.0 T 0.08 → 0.816 · literal · ابن زَمرَك: ولا يَزالُ القَصْرُ قَصْرُ السلامْ    يختالُ في بُرْدِ الشباب القشيبْ
- after · tier 1 · E 1.00 V 1.0 T 0.138 → 0.828 · literal · فتيان الشاغوري: دارٌ تديَّرَها السُرورُ فَقَصَّرَت    عَنها القُصورُ وَصدت فيها الصيدا
- after · tier 1 · E 1.00 V 1.0 T 0.103 → 0.821 · literal · عماد الدين الأصبهاني: بُشرى الممالكِ فتحُ قلعةِ منبجٍ    فلْيَهْنِ هذا النصرَ كلُّ متوَّجِ
- after · tier 1 · E 1.00 V 1.0 T 0.08 → 0.816 · literal · ابن زَمرَك: ولا يَزالُ القَصْرُ قَصْرُ السلامْ    يختالُ في بُرْدِ الشباب القشيبْ

## heritage · img:places365_sample:Places365_val_00000495 (mosque/outdoor)

- Scene: before place_of_worship 0.50 (confident); after place_of_worship 0.50 (confident)
- Image emotion top-3: before awe 0.843, amusement 0.123, sadness 0.013 (clear); after awe 0.843, amusement 0.123, sadness 0.013 (clear)
- Suggested literary emotion: before ['awe']; after ['awe']
- Confirmed visual items (app suggestion): before ['scene_group.worship', 'scene_group.city']; after ['scene_group.worship', 'scene_group.city']

**longing · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.083 → 0.642 · literal · أبو الفوارس البزاعي: لست أنسى يا ديرُ وقفتنا في    كَ، وإنْ أورثتني النسيانا
- before · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · البرعي: وَسَقى جَوانِب روضة قدسية    مَحروسة في ظل ذاك المسجد
- before · tier 1 · E 1.00 V 0.5 T 0.074 → 0.640 · literal · ابن الوردي: ولو درتُ وادي ديرِ سمعانَ ساعةً    لكنتُ أبلُّ الشوقَ مِنْ عمرِ الرضى
- after · tier 1 · E 1.00 V 0.5 T 0.083 → 0.642 · literal · أبو الفوارس البزاعي: لست أنسى يا ديرُ وقفتنا في    كَ، وإنْ أورثتني النسيانا
- after · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · البرعي: وَسَقى جَوانِب روضة قدسية    مَحروسة في ظل ذاك المسجد
- after · tier 1 · E 1.00 V 0.5 T 0.074 → 0.640 · literal · ابن الوردي: ولو درتُ وادي ديرِ سمعانَ ساعةً    لكنتُ أبلُّ الشوقَ مِنْ عمرِ الرضى

**sadness · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.14 → 0.653 · literal · البهلول الدمشقي: حتى المساجد من أهلِ الصلاةِ خَلَت    من الجماعةِ إلاّ بعض ما ندرا
- before · tier 1 · E 1.00 V 0.5 T 0.082 → 0.641 · literal · ابن الوردي: يا ديرُ إنْ تصمتْ فإنَّكَ ناطقٌ    إنَّ النواعمَ ضمهنَّ قبورُ
- before · tier 1 · E 1.00 V 0.5 T 0.081 → 0.641 · literal · عُبَيد الله بن الرُقَيّات: فَالدَيرُ أَقوى إِلى البَليخِ كَما    أَقوَت مَحاريبُ أُمَّةٍ دَرَسوا
- after · tier 1 · E 1.00 V 0.5 T 0.14 → 0.653 · literal · البهلول الدمشقي: حتى المساجد من أهلِ الصلاةِ خَلَت    من الجماعةِ إلاّ بعض ما ندرا
- after · tier 1 · E 1.00 V 0.5 T 0.082 → 0.641 · literal · ابن الوردي: يا ديرُ إنْ تصمتْ فإنَّكَ ناطقٌ    إنَّ النواعمَ ضمهنَّ قبورُ
- after · tier 1 · E 1.00 V 0.5 T 0.081 → 0.641 · literal · عُبَيد الله بن الرُقَيّات: فَالدَيرُ أَقوى إِلى البَليخِ كَما    أَقوَت مَحاريبُ أُمَّةٍ دَرَسوا

**awe · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.1 → 0.645 · literal · حازم القرطاجني: سبحانَ مَنْ بهمُ أسرى لكعبته    وبيته الطاهر المحفوف بالحرم
- before · tier 1 · E 1.00 V 0.5 T 0.08 → 0.641 · literal · عباس بن فرناس: بنى لهم مسجداً جلت عجائبه    لولا السماءُ لما ضاهاه بنيانُ
- before · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · اللواح: سبحان من أسرى به ليلاً إلى    أقصى المساجد راقياً درجاته
- after · tier 1 · E 1.00 V 0.5 T 0.1 → 0.645 · literal · حازم القرطاجني: سبحانَ مَنْ بهمُ أسرى لكعبته    وبيته الطاهر المحفوف بالحرم
- after · tier 1 · E 1.00 V 0.5 T 0.08 → 0.641 · literal · عباس بن فرناس: بنى لهم مسجداً جلت عجائبه    لولا السماءُ لما ضاهاه بنيانُ
- after · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · اللواح: سبحان من أسرى به ليلاً إلى    أقصى المساجد راقياً درجاته

**serenity · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.102 → 0.645 · literal · مالك بن المرحل: اللهُ أكبرُ للصلاة أقيمُها    بين الصفوفِ من البلاطِ الواسعِ
- before · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · الأمير الصنعاني: ومن هو نور في المساجد ساطع    إذا قام ليلاً خاشعاً يتهجد
- before · tier 1 · E 1.00 V 0.5 T 0.076 → 0.640 · literal · عبد الكريم البَسطي: أؤُمُّ بها في مسجدٍ بجماعةٍ    مُقيمينَ للْخَمْسِ الفروض كِرَامِ
- after · tier 1 · E 1.00 V 0.5 T 0.102 → 0.645 · literal · مالك بن المرحل: اللهُ أكبرُ للصلاة أقيمُها    بين الصفوفِ من البلاطِ الواسعِ
- after · tier 1 · E 1.00 V 0.5 T 0.078 → 0.641 · literal · الأمير الصنعاني: ومن هو نور في المساجد ساطع    إذا قام ليلاً خاشعاً يتهجد
- after · tier 1 · E 1.00 V 0.5 T 0.076 → 0.640 · literal · عبد الكريم البَسطي: أؤُمُّ بها في مسجدٍ بجماعةٍ    مُقيمينَ للْخَمْسِ الفروض كِرَامِ

**joy · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.113 → 0.648 · literal · الآثاري: مِن زَمزَم اِشرَب وَطُف وَاِطرَب بكعبَتِه    قَد زَمزَم السَعدُ لِلمَوصولِ بِالحرمِ
- before · tier 1 · E 1.00 V 0.5 T 0.104 → 0.646 · literal · ابن نباتة المصري: مستقبل الكعبة العظمى له طرب    حيثُ الستور وتمجيد وتطمير
- before · tier 1 · E 1.00 V 0.5 T 0.101 → 0.645 · literal · ابن جُبَير: بلغت المنى وحللت الحرَم    فعاد شبابك بعد الهرَم
- after · tier 1 · E 1.00 V 0.5 T 0.113 → 0.648 · literal · الآثاري: مِن زَمزَم اِشرَب وَطُف وَاِطرَب بكعبَتِه    قَد زَمزَم السَعدُ لِلمَوصولِ بِالحرمِ
- after · tier 1 · E 1.00 V 0.5 T 0.104 → 0.646 · literal · ابن نباتة المصري: مستقبل الكعبة العظمى له طرب    حيثُ الستور وتمجيد وتطمير
- after · tier 1 · E 1.00 V 0.5 T 0.101 → 0.645 · literal · ابن جُبَير: بلغت المنى وحللت الحرَم    فعاد شبابك بعد الهرَم

## water_rain · img:places365_sample:Places365_val_00002131 (river)

- Scene: before sea_coast 0.35 (unsupported); after sea_coast 0.35 (unsupported)
- Image emotion top-3: before awe 0.724, amusement 0.110, contentment 0.094 (clear); after awe 0.724, amusement 0.110, contentment 0.094 (clear)
- Suggested literary emotion: before ['awe']; after ['awe']
- Confirmed visual items (app suggestion): before []; after []

**longing · production** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · أَبو تَمّام: كَم مَنزِلٍ في الأَرضِ يَألَفُهُ الفَتى    وَحَنينُهُ أَبَداً لِأَوَّلِ مَنزِلِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · أَبو تَمّام: كَم مَنزِلٍ في الأَرضِ يَألَفُهُ الفَتى    وَحَنينُهُ أَبَداً لِأَوَّلِ مَنزِلِ

**longing · development** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · أَبو تَمّام: كَم مَنزِلٍ في الأَرضِ يَألَفُهُ الفَتى    وَحَنينُهُ أَبَداً لِأَوَّلِ مَنزِلِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · أَبو تَمّام: كَم مَنزِلٍ في الأَرضِ يَألَفُهُ الفَتى    وَحَنينُهُ أَبَداً لِأَوَّلِ مَنزِلِ

**sadness · production** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · الخَنساء: يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن الرومي: بكاؤكُما يشْفي وإن كان لا يُجْدي    فجُودا فقد أوْدَى نَظيركُمُا عندي

**sadness · development** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · الخَنساء: يُذَكِّرُني طُلوعُ الشَمسِ صَخراً    وَأَذكُرُهُ لِكُلِّ غُروبِ شَمسِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن الرومي: بكاؤكُما يشْفي وإن كان لا يُجْدي    فجُودا فقد أوْدَى نَظيركُمُا عندي

**awe · production** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · البُحتُرِيّ: لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ

**awe · development** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن خفاجة: وَأَرعَنَ طَمّاحِ الذُؤابَةِ باذِخٍ    يُطاوِلُ أَعنانَ السَماءِ بِغارِبِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · البُحتُرِيّ: لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ

**serenity · production** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**serenity · development** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · جرمانوس فرحات: ترى رهبانَهم راضين طوعاً    بذُلِّ الفقر والفقرُ اختيار

**joy · production** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما

**joy · development** — before `partial`, after `partial`
- before · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما
- after · tier 3 · E 1.00 V None T None → 1.000 · emotion-only · البُحتُرِيّ: أَتاكَ الرَبيعُ الطَلقُ يَختالُ ضاحِكاً    مِنَ الحُسنِ حَتّى كادَ أَن يَتَكَلَّما

## water_rain · img:places365_sample:Places365_val_00002175 (lake/natural)

- Scene: before rivers_lakes 0.48 (confident); after rivers_lakes 0.48 (confident)
- Image emotion top-3: before contentment 0.860, excitement 0.103, amusement 0.021 (clear); after contentment 0.860, excitement 0.103, amusement 0.021 (clear)
- Suggested literary emotion: before ['serenity']; after ['serenity']
- Confirmed visual items (app suggestion): before ['scene_group.water']; after ['scene_group.water']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.276 → 0.855 · literal · مهيار الديلمي: وغادروني أغَصُّ شوقاً    بالعذب من دِجلة الزلالِ
- before · tier 1 · E 1.00 V 1.0 T 0.135 → 0.827 · literal · عبد الرحمن الداخل: لو أنها تبكى إذاً لبكت    ماء الفرات ومنبت النخل
- before · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · محمود سامي البارودي: فَيَا رَوْضَةَ الْمِقْيَاسِ جَادَكِ سَلْسَلٌ    مِنَ النِّيلِ يَدْعُو لِلْحَنِينِ السَّوَاقِيَا
- after · tier 1 · E 1.00 V 1.0 T 0.276 → 0.855 · literal · مهيار الديلمي: وغادروني أغَصُّ شوقاً    بالعذب من دِجلة الزلالِ
- after · tier 1 · E 1.00 V 1.0 T 0.135 → 0.827 · literal · عبد الرحمن الداخل: لو أنها تبكى إذاً لبكت    ماء الفرات ومنبت النخل
- after · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · محمود سامي البارودي: فَيَا رَوْضَةَ الْمِقْيَاسِ جَادَكِ سَلْسَلٌ    مِنَ النِّيلِ يَدْعُو لِلْحَنِينِ السَّوَاقِيَا

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.153 → 0.831 · literal · جميل صدقي الزهاوي: لا دجلة دجلة من بعد نكبتها    وَلا الزَمان بواديها كَما عهدا
- before · tier 1 · E 1.00 V 1.0 T 0.137 → 0.827 · literal · أبو القاسم الشابي: يا جدوَلَ الوادي الطَّروبَ    أَلمْ يُرَنِّقْكَ القُطُوبْ
- before · tier 1 · E 1.00 V 1.0 T 0.132 → 0.826 · literal · الأسود بن يعفر النهشلي: نَزلوا بأنقرة يسيلُ عليهمُ    ماءُ الفراتِ يجيءُ من أطوادِ
- after · tier 1 · E 1.00 V 1.0 T 0.153 → 0.831 · literal · جميل صدقي الزهاوي: لا دجلة دجلة من بعد نكبتها    وَلا الزَمان بواديها كَما عهدا
- after · tier 1 · E 1.00 V 1.0 T 0.137 → 0.827 · literal · أبو القاسم الشابي: يا جدوَلَ الوادي الطَّروبَ    أَلمْ يُرَنِّقْكَ القُطُوبْ
- after · tier 1 · E 1.00 V 1.0 T 0.132 → 0.826 · literal · الأسود بن يعفر النهشلي: نَزلوا بأنقرة يسيلُ عليهمُ    ماءُ الفراتِ يجيءُ من أطوادِ

**awe · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.15 → 0.830 · literal · ابن الراعي: تشقها الأنهار والخلجان    وكلُّ نهرٍ منهم سيحانُ
- before · tier 1 · E 1.00 V 1.0 T 0.146 → 0.829 · literal · المعولي العماني: وهي تجري مِنْ تحتها أنهارٌ    من نميرٍ سبحان من أَجْرَاهَا
- before · tier 1 · E 1.00 V 1.0 T 0.146 → 0.829 · literal · أبو القاسم الشابي: في رقصِ أَمواجِ البحيْرة    تَحْتَ أَضواءِ النُّجُومْ
- after · tier 1 · E 1.00 V 1.0 T 0.15 → 0.830 · literal · ابن الراعي: تشقها الأنهار والخلجان    وكلُّ نهرٍ منهم سيحانُ
- after · tier 1 · E 1.00 V 1.0 T 0.146 → 0.829 · literal · المعولي العماني: وهي تجري مِنْ تحتها أنهارٌ    من نميرٍ سبحان من أَجْرَاهَا
- after · tier 1 · E 1.00 V 1.0 T 0.146 → 0.829 · literal · أبو القاسم الشابي: في رقصِ أَمواجِ البحيْرة    تَحْتَ أَضواءِ النُّجُومْ

**serenity · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.303 → 0.861 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 1 · E 1.00 V 1.0 T 0.303 → 0.861 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.145 → 0.829 · literal · يوسف بن أبي الفتح: به من لجين الماء ينساب جدولٌ    تجعِّده أيدي النسيم إذا انحطَّا
- before · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · يحيى الغزال: كَفانِيَ مِن كُلِّ الَّذي أُعجِبوا بِهِ    قُلَيلَةُ ماءٍ تُستَقى لي مِنَ النهرِ
- before · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · بهاء الدين العاملي: تراه في الأنهار جارٍ صافي    كأنه لآلئ الأصداف
- after · tier 1 · E 1.00 V 1.0 T 0.145 → 0.829 · literal · يوسف بن أبي الفتح: به من لجين الماء ينساب جدولٌ    تجعِّده أيدي النسيم إذا انحطَّا
- after · tier 1 · E 1.00 V 1.0 T 0.124 → 0.825 · literal · يحيى الغزال: كَفانِيَ مِن كُلِّ الَّذي أُعجِبوا بِهِ    قُلَيلَةُ ماءٍ تُستَقى لي مِنَ النهرِ
- after · tier 1 · E 1.00 V 1.0 T 0.112 → 0.822 · literal · بهاء الدين العاملي: تراه في الأنهار جارٍ صافي    كأنه لآلئ الأصداف

**joy · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.323 → 0.865 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- before · tier 1 · E 0.60 V 1.0 T 0.303 → 0.681 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ
- after · tier 1 · E 1.00 V 1.0 T 0.323 → 0.865 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- after · tier 1 · E 0.60 V 1.0 T 0.303 → 0.681 · literal · ابن خفاجة: وَالريحُ تَعبَثُ بِالغُصونِ وَقَد جَرى    ذَهَبُ الأَصيلِ عَلى لُجَينِ الماءِ

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.123 → 0.825 · literal · ابن القيسراني: أَوَ ما ترى طرب الغدير    إِلى النسيم إِذا تحرّكْ
- before · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · ابن الحاج النميري: وَيَا حُسْنَهَا لِلنَّاظِرِينَ بُحَيْرَةً    بِهَا رُكَّعُ الأَغْصَانِ بَاتَتْ عَلَى طُهْرِ
- before · tier 1 · E 1.00 V 1.0 T 0.095 → 0.819 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ
- after · tier 1 · E 1.00 V 1.0 T 0.123 → 0.825 · literal · ابن القيسراني: أَوَ ما ترى طرب الغدير    إِلى النسيم إِذا تحرّكْ
- after · tier 1 · E 1.00 V 1.0 T 0.122 → 0.824 · literal · ابن الحاج النميري: وَيَا حُسْنَهَا لِلنَّاظِرِينَ بُحَيْرَةً    بِهَا رُكَّعُ الأَغْصَانِ بَاتَتْ عَلَى طُهْرِ
- after · tier 1 · E 1.00 V 1.0 T 0.095 → 0.819 · literal · ابن خفاجة: يَأَهلَ أَندَلُسٍ لِلَّهِ دَرُّكُمُ    ماءٌ وَظِلٌّ وَأَنهارٌ وَأَشجارُ

## city_night · img:places365_sample:Places365_val_00000323 (street)

- Scene: before old_city_market 0.70 (confident); after old_city_market 0.70 (confident)
- Image emotion top-3: before sadness 0.271, fear 0.213, awe 0.125 (ambiguous); after sadness 0.271, fear 0.213, awe 0.125 (ambiguous)
- Suggested literary emotion: before ['sadness', 'fear']; after []
- Confirmed visual items (app suggestion): before ['scene_group.heritage', 'tag.road']; after ['scene_group.heritage', 'tag.road']

**longing · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**longing · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.085 → 0.642 · literal · البُحتُرِيّ: يَطَّبي أَبيَضُ المَدائِنِ شَوقي    أَفَلا المَذحِجِيُّ أَو غِمدانُه
- before · tier 1 · E 1.00 V 0.5 T 0.062 → 0.637 · literal · المعتمد بن عباد: وَسَلِّم عَلى قَصر الشَراجيب عَن فَتىً    لَهُ أَبَداً شَوقٌ إِلى ذَلِكَ القَصرِ
- before · tier 1 · E 1.00 V 0.5 T 0.059 → 0.637 · literal · ولي الدين يكن: همت شوقاً ببعلبك وماسا    ءلت أطلال بعلبك زماني
- after · tier 1 · E 1.00 V 0.5 T 0.085 → 0.642 · literal · البُحتُرِيّ: يَطَّبي أَبيَضُ المَدائِنِ شَوقي    أَفَلا المَذحِجِيُّ أَو غِمدانُه
- after · tier 1 · E 1.00 V 0.5 T 0.062 → 0.637 · literal · المعتمد بن عباد: وَسَلِّم عَلى قَصر الشَراجيب عَن فَتىً    لَهُ أَبَداً شَوقٌ إِلى ذَلِكَ القَصرِ
- after · tier 1 · E 1.00 V 0.5 T 0.059 → 0.637 · literal · ولي الدين يكن: همت شوقاً ببعلبك وماسا    ءلت أطلال بعلبك زماني

**sadness · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.14 → 0.653 · literal · أبو العَتاهِيَة: سَتَدرُسُ آثارٌ وَتَعقِبُ حَسرَةٌ    سَتَخلو قُصورٌ شُيِّدَت وَحُصونُ
- before · tier 1 · E 1.00 V 0.5 T 0.109 → 0.647 · literal · أبو البقاء الرندي: دارَ الزَمانُ عَلى دارا وَقاتِلِهِ    وَأَمَّ كِسرى فَما آواهُ إِيوانُ
- before · tier 1 · E 1.00 V 0.5 T 0.099 → 0.645 · literal · البُحتُرِيّ: حَضَرَت رَحلِيَ الهُمومُ فَوَجَّه    تُ إِلى أَبيَضَ المَدائِنِ عَنسي
- after · tier 1 · E 1.00 V 0.5 T 0.14 → 0.653 · literal · أبو العَتاهِيَة: سَتَدرُسُ آثارٌ وَتَعقِبُ حَسرَةٌ    سَتَخلو قُصورٌ شُيِّدَت وَحُصونُ
- after · tier 1 · E 1.00 V 0.5 T 0.109 → 0.647 · literal · أبو البقاء الرندي: دارَ الزَمانُ عَلى دارا وَقاتِلِهِ    وَأَمَّ كِسرى فَما آواهُ إِيوانُ
- after · tier 1 · E 1.00 V 0.5 T 0.099 → 0.645 · literal · البُحتُرِيّ: حَضَرَت رَحلِيَ الهُمومُ فَوَجَّه    تُ إِلى أَبيَضَ المَدائِنِ عَنسي

**awe · production** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 0.5 T 0.0 → 0.625 · literal · أحمد شوقي: قِف ناجِ أَهرامَ الجَلالِ وَنادِ    هَل مِن بُناتِكَ مَجلِسٌ أَو نادِ
- before · tier 1 · E 1.00 V 0.35 T 0.032 → 0.579 · scene_association · البُحتُرِيّ: لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ
- after · tier 1 · E 1.00 V 0.5 T 0.0 → 0.625 · literal · أحمد شوقي: قِف ناجِ أَهرامَ الجَلالِ وَنادِ    هَل مِن بُناتِكَ مَجلِسٌ أَو نادِ
- after · tier 1 · E 1.00 V 0.35 T 0.032 → 0.579 · scene_association · البُحتُرِيّ: لَيسَ يُدرى أَصُنعُ إِنسٍ لِجِنٍّ    سَكَنوهُ أَم صُنعُ جِنٍّ لِإِنسِ

**awe · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.102 → 0.645 · literal · ابن زَمرَك: ولله عينا من رأى القصر حوله    منازلُ بالنصر العزيز أواهلُ
- before · tier 1 · E 1.00 V 0.5 T 0.093 → 0.644 · literal · ابن قلاقس: خفضَ الخورنقَ والسديرَ سموُّهُ    وثنى قصورَ الروم ذاتَ قُصورِ
- before · tier 1 · E 1.00 V 0.5 T 0.064 → 0.638 · literal · البُحتُرِيّ: وَكَأَنَّ الإيوانَ مِن عَجَبِ الصَن    عَةِ جَوبٌ في جَنبِ أَرعَنَ جِلسِ
- after · tier 1 · E 1.00 V 0.5 T 0.102 → 0.645 · literal · ابن زَمرَك: ولله عينا من رأى القصر حوله    منازلُ بالنصر العزيز أواهلُ
- after · tier 1 · E 1.00 V 0.5 T 0.093 → 0.644 · literal · ابن قلاقس: خفضَ الخورنقَ والسديرَ سموُّهُ    وثنى قصورَ الروم ذاتَ قُصورِ
- after · tier 1 · E 1.00 V 0.5 T 0.064 → 0.638 · literal · البُحتُرِيّ: وَكَأَنَّ الإيوانَ مِن عَجَبِ الصَن    عَةِ جَوبٌ في جَنبِ أَرعَنَ جِلسِ

**serenity · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.066 → 0.638 · literal · المعولي العماني: واسلمْ سلمتَ سلامةً محروسةً    في حصن بهلا في النعيم مُخلَّدَاً
- before · tier 1 · E 1.00 V 0.5 T 0.063 → 0.638 · literal · ابن الهبارية: بغدادُ دارٌ رياضُها أُنُفُ    والغيثُ في عنفوانِها يَكفُ
- before · tier 1 · E 1.00 V 0.5 T 0.057 → 0.636 · literal · أبو الحسن الجرجاني: فلما حللتُ القَصرَ قَصرَ مسرَّتي    تَفَرَّقنَ عني آيساتٍ جُمُوعَها
- after · tier 1 · E 1.00 V 0.5 T 0.066 → 0.638 · literal · المعولي العماني: واسلمْ سلمتَ سلامةً محروسةً    في حصن بهلا في النعيم مُخلَّدَاً
- after · tier 1 · E 1.00 V 0.5 T 0.063 → 0.638 · literal · ابن الهبارية: بغدادُ دارٌ رياضُها أُنُفُ    والغيثُ في عنفوانِها يَكفُ
- after · tier 1 · E 1.00 V 0.5 T 0.057 → 0.636 · literal · أبو الحسن الجرجاني: فلما حللتُ القَصرَ قَصرَ مسرَّتي    تَفَرَّقنَ عني آيساتٍ جُمُوعَها

**joy · production** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 0.5 T 0.123 → 0.650 · literal · فتيان الشاغوري: دارٌ تديَّرَها السُرورُ فَقَصَّرَت    عَنها القُصورُ وَصدت فيها الصيدا
- before · tier 1 · E 1.00 V 0.5 T 0.093 → 0.644 · literal · عماد الدين الأصبهاني: بُشرى الممالكِ فتحُ قلعةِ منبجٍ    فلْيَهْنِ هذا النصرَ كلُّ متوَّجِ
- before · tier 1 · E 1.00 V 0.5 T 0.072 → 0.639 · literal · ابن زَمرَك: ولا يَزالُ القَصْرُ قَصْرُ السلامْ    يختالُ في بُرْدِ الشباب القشيبْ
- after · tier 1 · E 1.00 V 0.5 T 0.123 → 0.650 · literal · فتيان الشاغوري: دارٌ تديَّرَها السُرورُ فَقَصَّرَت    عَنها القُصورُ وَصدت فيها الصيدا
- after · tier 1 · E 1.00 V 0.5 T 0.093 → 0.644 · literal · عماد الدين الأصبهاني: بُشرى الممالكِ فتحُ قلعةِ منبجٍ    فلْيَهْنِ هذا النصرَ كلُّ متوَّجِ
- after · tier 1 · E 1.00 V 0.5 T 0.072 → 0.639 · literal · ابن زَمرَك: ولا يَزالُ القَصْرُ قَصْرُ السلامْ    يختالُ في بُرْدِ الشباب القشيبْ

## city_night · img:places365_sample:Places365_val_00000740 (skyscraper)

- Scene: before modern_city 0.68 (confident); after modern_city 0.68 (confident)
- Image emotion top-3: before sadness 0.468, awe 0.403, fear 0.085 (ambiguous); after sadness 0.468, awe 0.403, fear 0.085 (ambiguous)
- Suggested literary emotion: before ['sadness', 'awe']; after []
- Confirmed visual items (app suggestion): before ['scene_group.city']; after ['scene_group.city']

**longing · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**longing · development** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**sadness · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**sadness · development** — before `ok`, after `ok`
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · جميل صدقي الزهاوي: بغداد أمست وقد أزرى بها النوب    تبكي على عزها الماضي وتنتحبُ
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · حافظ ابراهيم: وَلا تَسَل بَعدَهُ عَن عَهدِ قُرطُبَةٍ    كَيفَ اِنمَحى بَينَ أَسيافٍ وَنيرانِ
- before · tier 1 · E 0.60 V 1.0 T 0.127 → 0.645 · literal · أبو القاسم الشابي: مَاذا أَوَدُّ مِنَ المدينَةِ وهي لا    ترثي لصوتِ تَفجُّع المَوْتُورِ
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · جميل صدقي الزهاوي: بغداد أمست وقد أزرى بها النوب    تبكي على عزها الماضي وتنتحبُ
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · حافظ ابراهيم: وَلا تَسَل بَعدَهُ عَن عَهدِ قُرطُبَةٍ    كَيفَ اِنمَحى بَينَ أَسيافٍ وَنيرانِ
- after · tier 1 · E 0.60 V 1.0 T 0.127 → 0.645 · literal · أبو القاسم الشابي: مَاذا أَوَدُّ مِنَ المدينَةِ وهي لا    ترثي لصوتِ تَفجُّع المَوْتُورِ

**awe · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**awe · development** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**serenity · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**serenity · development** — before `abstained` no_visual_match_emotion_only_off, after `abstained` no_visual_match_emotion_only_off

**joy · production** — before `abstained` cell_not_covered, after `abstained` cell_not_covered

**joy · development** — before `partial`, after `partial`
- before · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · جميل صدقي الزهاوي: يغلي سروري كُلَّما فكرت في    مجد إِلى بغداد سوف يعاد
- after · tier 1 · E 1.00 V 1.0 T 0.0 → 0.800 · literal · جميل صدقي الزهاوي: يغلي سروري كُلَّما فكرت في    مجد إِلى بغداد سوف يعاد

