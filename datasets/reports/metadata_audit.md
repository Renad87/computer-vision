# EmoSet metadata audit

Approach B (method section 11): approval N1 to use EmoSet scene metadata has not been given, so no metadata was joined. Every EmoSet record has `scene_label_status = unavailable` and no `scene_source_raw` field (counted as 'not joined').

No audit sample was drawn and no image was reviewed, so `metadata_audit_sample.csv` has its header only. Prepared rule for approach D (fixed in advance): up to 25 images per class, seed 42, Wilson 95% intervals, a class is kept if its audited precision is ≥ 0.80.
