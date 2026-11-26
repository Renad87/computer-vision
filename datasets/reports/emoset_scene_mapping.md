# EmoSet scene mapping

Approach B (method section 11): approval N1 to use EmoSet scene metadata has not been given, so no metadata was joined. Every EmoSet record has `scene_label_status = unavailable` and no `scene_source_raw` field (counted as 'not joined').

- EmoSet records: 9200; joined: 0; not joined: 9200
- `emoset_scene_mapping.csv` therefore has its header only.
- If N1 is approved later, the mapping (raw → normalized → Places365 name yes/no → `map_places365` outcome → counts per split) and the audit come as a new version (v1.1), never as a silent change.
