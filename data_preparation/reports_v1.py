"""v1 reports: near-duplicate section, class distribution, split provenance, EmoSet scene mapping and audit."""
import os
from collections import Counter

from .common import md_table, write_csv, write_json, write_text

REPORTS = os.path.join("datasets", "reports")
SPLITS = ["train", "val", "test", "ood_test"]


def _hist(values, edges):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        out.append((f"{lo}–{hi}", sum(lo <= v < hi for v in values)))
    return out


def near_markdown(state):
    pairs, dist = state["pairs"], state["dist"]
    by = Counter(p["nominated_by"] for p in pairs)
    md = [f"- images searched (after exact-duplicate handling): {len(dist['nearest_neighbour_clip_cosine'])}",
          "- thresholds (provisional, fixed before the search): pHash Hamming ≤ 6 of 64 bits, or CLIP cosine ≥ 0.95 "
          "(`ViT-B-32-quickgelu`/`openai`, L2-normalized). They only nominate pairs; a person decides each pair.",
          f"- candidate pairs: {len(pairs)} — by method: {dict(sorted(by.items()))}",
          f"- across splits: {sum(p['split_a'] != p['split_b'] for p in pairs)}; across sources: "
          f"{sum(p['source_a'] != p['source_b'] for p in pairs)}",
          f"- human decisions: same_image {sum(p['decision'] == 'same_image' for p in pairs)}, different "
          f"{sum(p['decision'] == 'different' for p in pairs)}, pending {state['pending']}",
          "- every pair with its decision, reviewer and date: `near_duplicate_candidates.csv`", ""]
    if state.get("group_sizes") is not None:
        nq = state.get("near_quarantine", [])
        md += [f"- confirmed groups: {len(state['group_sizes'])}; sizes: "
               f"{dict(sorted(Counter(state['group_sizes']).items()))}",
               f"- quarantined (near_duplicate_across_splits): {len(nq)} — per source and split: "
               f"{dict(sorted(Counter((q['source_dataset'], q['removed_from_split']) for q in nq).items()))}", ""]
    md += ["### Distance distributions (nearest neighbour of every image)", "",
           md_table(["CLIP cosine to nearest neighbour", "images"],
                    _hist(dist["nearest_neighbour_clip_cosine"], [-1, 0.7, 0.8, 0.85, 0.9, 0.95, 0.98, 1.01])), "",
           md_table(["pHash Hamming to nearest neighbour", "images"],
                    _hist(dist["nearest_neighbour_phash_hamming"], [0, 3, 7, 11, 16, 21, 65])), "",
           "### Candidate pairs per source and split pair", "",
           md_table(["pair (source/split)", "candidates", "same_image", "different", "pending"],
                    [(k, n, sum(1 for p in state["pairs"] if key(p) == k and p["decision"] == "same_image"),
                      sum(1 for p in state["pairs"] if key(p) == k and p["decision"] == "different"),
                      sum(1 for p in state["pairs"] if key(p) == k and not p["decision"]))
                     for k, n in sorted(Counter(key(p) for p in pairs).items())]), ""]
    return md


def key(p):
    return " ↔ ".join(sorted([f"{p['source_a']}/{p['split_a']}", f"{p['source_b']}/{p['split_b']}"]))


def class_distribution(state, root):
    recs, tax = state["records"], state["taxonomy"]
    scene_order, emo_order = tax.class_order["scene"], tax.class_order["img_emotion"]
    out = {"status_counts": {}, "scene_counts": {}, "emotion_counts": {}, "imbalance_ratio": {},
           "inverse_frequency_weights_train": {}, "joint_scene_emotion": {},
           "emoset_scene_labels": {"approach": "B", "before_audit": 0, "after_audit": 0},
           "pv_test": "pending: no photos or annotations yet"}
    md = ["# Class distribution (manifest_v1)", "", "All counts are from `manifest_v1.jsonl`.", "",
          "## Status counts per source and split", ""]
    rows = []
    for (src, split), n in sorted(Counter((r["source_dataset"], r["split"]) for r in recs).items(),
                                  key=lambda kv: (kv[0][0], SPLITS.index(kv[0][1]))):
        sub = [r for r in recs if r["source_dataset"] == src and r["split"] == split]
        sc = Counter(r["scene_label_status"] for r in sub)
        ec = Counter(r["emotion_label_status"] for r in sub)
        out["status_counts"][f"{src}|{split}"] = {"rows": n, "scene": dict(sc), "emotion": dict(ec)}
        rows.append((src, split, n, ", ".join(f"{k} {v}" for k, v in sorted(sc.items())),
                     ", ".join(f"{k} {v}" for k, v in sorted(ec.items()))))
    md += [md_table(["source", "split", "rows", "scene status", "emotion status"], rows), ""]
    for task, field, order in (("scene", "scene_label", scene_order), ("emotion", "emotion_label", emo_order)):
        md += [f"## {task.capitalize()} classes (labeled rows) per source and split", ""]
        cols = sorted({(r["source_dataset"], r["split"]) for r in recs if r[field]},
                      key=lambda x: (x[0], SPLITS.index(x[1])))
        table, counts = [], {}
        for c in order:
            row = [c]
            for src, split in cols:
                n = sum(1 for r in recs if r[field] == c and r["source_dataset"] == src and r["split"] == split)
                row.append(n)
                counts.setdefault(f"{src}|{split}", {})[c] = n
            table.append(row)
        out[f"{task}_counts"] = counts
        md += [md_table(["class"] + [f"{s} / {sp}" for s, sp in cols], table), ""]
        md += ["Imbalance ratio (largest / smallest class among labeled rows):", ""]
        ir = []
        for split in SPLITS:
            c = Counter(r[field] for r in recs if r["split"] == split and r[field])
            if c:
                vals = [c.get(k, 0) for k in order]
                nz = [v for v in vals if v]
                ratio = round(max(nz) / min(nz), 3)
                out["imbalance_ratio"][f"{task}|{split}"] = {"ratio": ratio, "classes_with_zero_rows": vals.count(0)}
                ir.append((split, max(nz), min(nz), ratio, vals.count(0)))
        md += [md_table(["split", "largest", "smallest (non-zero)", "ratio", "classes with 0 rows"], ir), ""]
        tr = Counter(r[field] for r in recs if r["split"] == "train" and r[field])
        total, k = sum(tr.values()), len(order)
        w = {c: (round(total / (k * tr[c]), 4) if tr.get(c) else None) for c in order}
        out["inverse_frequency_weights_train"][task] = w
        md += ["Inverse-frequency class weights on `train` only (information for Omar; w = N / (K · n_c)):", "",
               md_table(["class", "train rows", "weight"], [(c, tr.get(c, 0), w[c]) for c in order]), ""]
    both = [r for r in recs if r["scene_label"] and r["emotion_label"]]
    out["joint_scene_emotion"] = {"rows_with_both_labels": len(both)}
    md += ["## Joint scene × emotion", "",
           f"Rows with both labels: {len(both)}. Approach B was used (no EmoSet scene metadata; approval N1 not "
           "given), so no image carries both labels and there is no joint table.", "",
           "## EmoSet-derived scene labels", "", "Before the audit: 0. After the audit: 0 (approach B).", "",
           "## PV-Test", "", "Pending: no team photos or annotation sheets yet (`pv_test_v1.jsonl` not built).", ""]
    write_json(os.path.join(root, REPORTS, "class_distribution.json"), out)
    write_text(os.path.join(root, REPORTS, "class_distribution.md"), "\n".join(md))


def split_provenance(state, root):
    recs = state["records"]
    c = Counter((r["source_dataset"], r["split"]) for r in recs)
    q = Counter((x["source_dataset"], x["removed_from_split"]) for x in state["quarantine"])
    md = ["# Split provenance (manifest_v1)", "",
          "Every image keeps its source split. Nothing was re-split, rebalanced or moved between splits; leakage "
          "was fixed only by quarantining the copy in the less protected split (`quarantine.jsonl`).", "",
          md_table(["source", "split", "rows in manifest", "quarantined from this split"],
                   [(s, sp, n, q.get((s, sp), 0)) for (s, sp), n in
                    sorted(c.items(), key=lambda kv: (kv[0][0], SPLITS.index(kv[0][1])))]), "",
          "## EmoSet-118K sample (`emoset118k`, `split_origin` = `hf_mirror_split`)", "",
          "- Evidence: the folder split in Renad's `emoset.zip` (input R1, SHA-256 "
          f"`{next(i['sha256'] for i in state['inputs'] if i['role'].startswith('R1'))}`).",
          "- Renad's code (`references/old_emotion_module/emoset_sampling_cells.md`, cell 4) streamed the mirror "
          "splits `train`, `val`, `test` of `Woleek/EmoSet-118K` with `shuffle(seed=42, buffer_size=2000)` and kept "
          "the first 600 / 150 / 400 per emotion. Her printed counts (4,800 / 1,200 / 3,200) equal the files.",
          "- Not confirmed: Renad's run note (R2: run date, `datasets` version, her SHA-256 of the zip) has not "
          "been received; whether the mirror splits equal the official EmoSet split lists is unknown (lists not "
          "available).", "",
          "## Places365 sample (`places365_sample`, `split_origin` = `reconstructed_from_official_val_seed42`)", "",
          "- Evidence: `places_manifest.csv` (input S1) lists only official Places365 validation files "
          "(`Places365_val_<digits>.jpg`).",
          "- `prepare_data.py` (copy in `references/old_visual_module/`) sampled them per category and re-split "
          "60/20/20 with `random.Random(42)`. The counts equal `references/derived/PREPROCESSING_AND_SPLITS.md`: "
          "16 scenes 2,580 / 860 / 860, background → `scene.other` 648 / 216 / 216, OOD 600.",
          "- The 600 OOD rows (old split `test`) were moved to `ood_test` as the method requires; they carry "
          "`excluded_ood` and no scene label.", "",
          "## PV-Test", "", "Pending: no photos yet, so no freeze record.", ""]
    write_text(os.path.join(root, REPORTS, "split_provenance.md"), "\n".join(md))


def emoset_scene_reports(state, root):
    reason = ("Approach B (method section 11): approval N1 to use EmoSet scene metadata has not been given, so no "
              "metadata was joined. Every EmoSet record has `scene_label_status = unavailable` and no "
              "`scene_source_raw` field (counted as 'not joined').")
    n = sum(1 for r in state["records"] if r["source_dataset"] == "emoset118k")
    write_text(os.path.join(root, REPORTS, "emoset_scene_mapping.md"),
               "\n".join(["# EmoSet scene mapping", "", reason, "",
                          f"- EmoSet records: {n}; joined: 0; not joined: {n}",
                          "- `emoset_scene_mapping.csv` therefore has its header only.",
                          "- If N1 is approved later, the mapping (raw → normalized → Places365 name yes/no → "
                          "`map_places365` outcome → counts per split) and the audit come as a new version "
                          "(v1.1), never as a silent change.", ""]))
    write_csv(os.path.join(root, REPORTS, "emoset_scene_mapping.csv"), [],
              ["raw_scene", "normalized", "is_places365_name", "outcome", "scene_label", "train", "val", "test"])
    write_text(os.path.join(root, REPORTS, "metadata_audit.md"),
               "\n".join(["# EmoSet metadata audit", "", reason, "",
                          "No audit sample was drawn and no image was reviewed, so `metadata_audit_sample.csv` has its "
                          "header only. Prepared rule for approach D (fixed in advance): up to 25 images per class, "
                          "seed 42, Wilson 95% intervals, a class is kept if its audited precision is ≥ 0.80.", ""]))
    write_csv(os.path.join(root, REPORTS, "metadata_audit_sample.csv"), [],
              ["image_id", "scene_label", "decision", "reviewer_id", "date"])


def write_v1_reports(state, root):
    if state.get("records") is None:
        return
    class_distribution(state, root)
    split_provenance(state, root)
    emoset_scene_reports(state, root)
