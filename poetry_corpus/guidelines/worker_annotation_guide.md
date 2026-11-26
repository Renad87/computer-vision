# Worker guide: drafting poetry records for one candidate pool

You draft AI annotations for authentic Arabic verses so the corpus can grow toward 1,000 verses. You work on one
disjoint pool; other workers have other pools. A coordinator merges your file, assigns ids and builds the records.

## Hard rules

1. **Never write verse text.** Your output holds APCD row numbers and labels only. The build copies the verse
   verbatim from APCD. Evidence is a short phrase copied from the verse (diacritics optional); the build finds it.
2. **Only rows from your pool file.** Read the `text` and the `context` lines (neighbouring verses of the same poem).
3. **Drafts only.** Never claim human review. Never invent facts: say nothing about a poem's occasion or person
   unless the verse or its context shows it.
4. **Edit nothing but your own output file.** Do not run `build_batch`, do not touch `poetry_corpus/records/`,
   `handoff/`, `contracts/` or anything else. No git, no network, no installs.
5. **Quality over count.** Reject a candidate rather than force a label. Stopping short of the target is fine.

## Reject

- the dominant feeling is love/desire, wine, satire, obscenity, sectarian polemic or plain praise of a patron;
- the scene word is only figurative (a generous man as "a sea", tears as "a sea") and nothing in the verse puts the
  scene in front of a reader. Such verses may still be used with `relation.symbolic`, but they do not count for coverage
  and each verse needs at least one `literal` or `scene_association` relation to a scene group;
- the meaning depends on the next verse (enjambment) and cannot be paraphrased alone;
- the text looks corrupt or you cannot understand it with confidence;
- more than one verse of the same poem for the same scene-emotion cell, or more than about four verses by one poet.

## Labels

**Scene groups** (`scene_group.*`, see `contracts/taxonomy/taxonomy_v1.json`): `desert` (desert, sand, camels,
caravans, campsite ruins أطلال), `sea` (sea, coast, ships), `mountains` (mountains, valleys واد, peaks, snow),
`water` (rivers, lakes, springs, streams, pools; not the sea), `greenery` (gardens, meadows, trees, flowers, palms,
spring), `sky_night` (sky, night, moon, stars, dawn, sunset, clouds), `heritage` (palaces, castles, ancient ruins
of buildings, old cities and markets), `city` (a city and its streets and buildings), `worship` (mosques, the Kaaba
and the Haram, minarets, monasteries, churches).

**Relations:** `relation.literal` (the scene is named in the verse; `evidence` required), `relation.scene_association`
(the verse is set there without naming it; `justification` required), `relation.symbolic` (metaphor or simile;
`justification` required), `relation.negated` / `relation.hypothetical` (`evidence` required). Add exposed tags
when the object is named literally: `tag.horse tag.falcon tag.bird tag.flower tag.moon tag.stars tag.teapot
tag.boat_ship tag.sea tag.fog tag.mosque tag.road tag.child`.

**Literary emotions** (`lit_emotion.*`), as in `poetry_corpus/guidelines/annotation_guide_ar.md`:
`sadness` (grief, elegy, present sorrow), `longing` (yearning for the absent, homeland, standing at abodes to
remember their people), `loneliness` (estrangement, solitude), `awe` (wonder and majesty, including religious
awe), `serenity` (calm, contentment, gentle nature), `joy` (open delight, spring, celebration), `pride` (self or
tribal pride, heroism), `fear` (dread of danger or the unknown). Weeping in love poetry is usually longing, not sadness.

- `primary`: one object (or a list of at most two). `secondary`: list of 0–2. No emotion twice.
- `basis`: `expressed` (an emotion word is in the verse; `evidence` required) or `evoked` (understood from the
  scene; `justification` required). Giving both is fine.
- `justification`: Arabic, at most 15 words. `meaning`: Arabic plain paraphrase, at most 40 words.
- `uncertainty`: `low`, `medium` or `high` (your own confidence).
- `text_note`: null, or an Arabic note when APCD shows an obvious quirk (missing letter, split word across the
  hemistichs). Never correct the text.

## Evidence phrases

Copy one to four consecutive words exactly as they appear in the verse, including attached letters (write
`والبحر` if the verse has `وَالبَحرُ`). The phrase must occur exactly once as whole words. Diacritics and
hamza/alef/ya/ta-marbuta spelling are ignored when matching.

## Output file

```json
{
  "worker": "desert_A",
  "model_id": "<your exact model id>",
  "date": "2026-11-26",
  "verses": [
    {"apcd_row": 1416923,
     "primary": {"id": "lit_emotion.sadness", "basis": "evoked", "evidence": null,
                 "justification": "يهيم ليلًا على الشاطئ حزينًا على شبابه الذي مضى"},
     "secondary": [{"id": "lit_emotion.loneliness", "basis": "evoked", "evidence": null,
                    "justification": "يتيه وحده بين الصخور"}],
     "visual": [{"target": "scene_group.sea", "relation": "relation.literal", "evidence": "شاطي البحر", "justification": null},
                {"target": "tag.sea", "relation": "relation.literal", "evidence": "البحر", "justification": null},
                {"target": "scene_group.sky_night", "relation": "relation.literal", "evidence": "الليل", "justification": null},
                {"target": "tag.moon", "relation": "relation.literal", "evidence": "القمر", "justification": null}],
     "meaning": "يصف الشاعر نفسه تائهًا في الليل بين صخور الشاطئ في ضوء القمر، في قصيدة يبكي فيها شبابه الذي مضى.",
     "text_note": null, "uncertainty": "medium"}
  ]
}
```

## Workflow

1. Read your pool in chunks (`sed -n '1,40p' POOL`), best-ranked first. Rows carry `cue_hits` and `v3_hint_*`:
   these are weak search hints, never labels.
2. Annotate the verses you accept and save the file often (every 10 verses), so nothing is lost.
3. Check: `python3 -B -m poetry_corpus.tools.check_worker_spec OUTPUT --pool POOL`. Fix every reported problem
   (usually an evidence phrase that is not exact) until it exits 0.
4. Finish with: verses written, verses rejected and the main reasons, and the scene-emotion cells where your pool
   had too few authentic candidates.
