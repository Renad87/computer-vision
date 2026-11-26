# Development profiles (synthetic)

All files here are SYNTHETIC test fixtures ("fixture": true, origin "synthetic_query", suggested_by_model false).
They are not model predictions and must never be presented as real user data. Queries use corpus_mode
"development" over poetry_corpus/records/p0_ai_drafts_v1.jsonl (AI drafts pending human review).

Expected eligibility was derived by hand from the draft labels under docs/RETRIEVAL_METHOD.md:
tier 1 = literal or scene_association with an anchor item (the focus if set, else every confirmed item);
tier 2 = symbolic with an anchor item when symbolic_allowed; tier 3 = emotion-only candidates when
emotion_only_allowed (the engine returns at most one). Order and scores are the engine's job.

| Profile | Tests | Pair | Tier 1 | Tier 2 | Tier-3 candidates | Expected |
|---|---|---|---|---|---|---|
| DP01_desert_longing | desert scene, longing; association match | DP02 | 10 | - | - | partial |
| DP02_desert_pride | same visual as DP01, different emotion; literal match | DP01 | 31 | - | - | partial |
| DP03_sea_loneliness | sea scene, loneliness; literal match | DP04 | 15 | - | - | partial |
| DP04_sea_joy | same visual as DP03, different emotion; no suitable poetry | DP03 | - | - | - | abstained (no_visual_match_emotion_only_off) |
| DP05_greenery_serenity | greenery, serenity; three literal matches, two by one poet | DP06 | 21, 22, 24 | - | - | ok |
| DP06_greenery_joy | same visual as DP05, different emotion; primary vs secondary emotion ranking | DP05 | 21, 22, 24, 26, 27, 29 | - | - | ok |
| DP07_heritage_awe | heritage, awe; literal and association matches | DP08 | 17, 19 | - | - | partial |
| DP08_heritage_longing | same visual as DP07, different emotion; no suitable poetry | DP07 | - | - | - | abstained (no_visual_match_emotion_only_off) |
| DP09_focus_sky_serenity | focus on sky/night (greenery also confirmed); focus restricts tier 1 | DP10 | 21, 23, 25 | - | - | ok |
| DP10_focus_greenery_serenity | same items as DP09 with the focus on greenery | DP09 | 21, 22, 24 | - | - | ok |
| DP11_sky_fear_symbolic | sky/night, fear, symbolic allowed; tier-2 symbolic match | DP12 | - | 36 | - | partial |
| DP12_sky_fear_no_symbolic | same as DP11 with symbolic not allowed; no suitable poetry | DP11 | - | - | - | abstained (no_visual_match_emotion_only_off) |
| DP13_moon_pride_symbolic | moon tag, pride, symbolic allowed; the literal moon verse has another emotion | - | - | 32 | - | partial |
| DP14_emotion_only_longing | no visual items, emotion-only longing; at most one tier-3 item | - | - | - | 1, 6, 7, 8, 9, 10, 30 | partial |
| DP15_unsupported_scene_sadness | unsupported scene (see synthetic_inference/SI01): no confirmed items, emotion-only | - | - | - | 1, 2, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 23, 40 | partial |
| DP16_missing_falcon_pride | falcon tag never annotated in the corpus; missing labels | - | - | - | - | abstained (cell_not_covered) |
| DP17_missing_worship_awe | worship scene group never annotated in the corpus; missing labels | - | - | - | - | abstained (cell_not_covered) |
| DP18_stars_fear | stars tag, fear; literal tag match | - | 40 | - | - | partial |
| DP19_bird_loneliness | bird tag, loneliness; association match | DP20 | 12 | - | - | partial |
| DP20_bird_serenity | same visual as DP19, different emotion; literal match | DP19 | 22 | - | - | partial |
| DP21_water_serenity | water, serenity; two literal matches | - | 21, 24 | - | - | partial |
| DP22_mountains_awe | mountains, awe; literal match | - | 16 | - | - | partial |
| DP23_desert_longing_emotion_only | DP01 with emotion-only enabled: tier 1 plus at most one tier-3 item | DP01 | 10 | - | 1, 6, 7, 8, 9, 30 | partial |
| DP24_greenery_serenity_secondary_concept | DP05 plus a secondary emotion and a concept; eligibility unchanged | DP05 | 21, 22, 24 | - | - | ok |
