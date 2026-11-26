"""manifest_v1: Places365 sample + EmoSet sample (approach B unless approval N1), near duplicates confirmed by a person.

Two runs:
  1. without decisions: writes datasets/reports/near_duplicate_candidates.csv, a blank decisions sheet
     datasets/review/near_duplicate_decisions.csv and review pages, then stops (exit 3). No manifest yet.
  2. after a person fills every `decision` (same_image / different) with reviewer_id and date: builds the manifest.
"""
import os

from contracts.taxonomy import load_taxonomy

from .cleaning import exact_duplicates, inspect
from .common import read_csv, write_csv
from .neardup import CANDIDATE_FIELDS, candidates, groups_and_quarantine, merge_decisions, read_decisions
from .sources import InputError, iter_emoset, iter_places


class ReviewPending(Exception):
    pass


def load_embeddings(path):
    import numpy as np
    if not os.path.exists(path):
        raise InputError(f"CLIP embeddings not found ({os.path.basename(path)}): run "
                         f"`python -m data_preparation.embeddings --workdir <W>` first")
    z = np.load(path)
    return dict(zip(z["paths"].tolist(), z["feats"]))


def build_v1(a, root):
    from .build import NAMES, input_entry, write_manifest
    from .common import rel
    tax = load_taxonomy()
    p_recs, p_inv, p_exc, p_flag = inspect(iter_places(a.places_dir, tax), with_phash=True)
    e_recs, e_inv, e_exc, e_flag = inspect(iter_emoset(a.emoset_zip, tax), with_phash=True)
    records, inventory = p_recs + e_recs, p_inv + e_inv
    excluded, flagged = p_exc + e_exc, p_flag + e_flag
    kept, quarantine, escalations, exact_groups = exact_duplicates(records)
    if escalations:
        raise InputError(f"{len(escalations)} exact duplicates between evaluation sets: report to Omar {escalations[:3]}")
    phash = {r["image_id"]: r["phash"] for r in inventory if r.get("phash")}
    emb_path = a.clip_features or os.path.join(root, "datasets", "cache", "clip_embeddings.npz")
    emb = load_embeddings(emb_path)
    missing = [r["image_path"] for r in kept if r["image_path"] not in emb]
    if missing:
        raise InputError(f"{len(missing)} images have no CLIP embedding (e.g. {missing[:2]}): re-run embeddings")
    kept = sorted(kept, key=lambda r: r["image_id"])
    pairs, dist = candidates(kept, phash, emb)
    decisions_path = a.near_dup_decisions or os.path.join(root, "datasets", "review", "near_duplicate_decisions.csv")
    pending = merge_decisions(pairs, read_decisions(decisions_path))
    write_csv(os.path.join(root, "datasets", "reports", "near_duplicate_candidates.csv"), pairs, CANDIDATE_FIELDS)
    candidates_in = [
        (os.path.join(a.places_dir, "data", "places_manifest.csv"), "S1 places_manifest.csv"),
        (os.path.join(a.places_dir, "data", "raw", "places365", "IO_places365.txt"), "S6 IO_places365.txt"),
        (os.path.join(a.places_dir, "data", "features", "places_clip.npz"),
         "S3 places_clip.npz (near-duplicate search only)"),
        (a.emoset_zip, "R1 emoset.zip (Renad)"),
        (emb_path, "CLIP embeddings (near-duplicate search only)")]
    inputs = [input_entry(p, role, root) for p, role in candidates_in if os.path.exists(p)]
    state = {"version": "v1", "inventory": inventory, "excluded": excluded, "flagged": flagged,
             "quarantine": quarantine, "exact_groups": exact_groups, "inputs": inputs, "taxonomy": tax,
             "pairs": pairs, "dist": dist, "pending": pending, "decisions_path": rel(decisions_path, root)}
    if pending:
        if not os.path.exists(decisions_path):
            write_csv(decisions_path, pairs, CANDIDATE_FIELDS)
        state["near"] = {"markdown": []}
        raise ReviewPending(state)
    group_of, near_q, near_esc, sizes = groups_and_quarantine(kept, pairs)
    if near_esc:
        raise InputError(f"{len(near_esc)} near-duplicate groups between evaluation sets: report to Omar {near_esc}")
    removed = {q["image_id"] for q in near_q}
    final = []
    for r in kept:
        if r["image_id"] in removed:
            continue
        final.append({**r, "near_dup_group": group_of.get(r["image_id"])})
    quarantine = sorted(quarantine + near_q, key=lambda q: q["image_id"])
    state.update(quarantine=quarantine, near_quarantine=near_q, group_sizes=sizes, group_of=group_of)
    extra = {"excluded_images": len(excluded), "quarantined_images": len(quarantine),
             "exact_duplicate_groups": len(exact_groups),
             "near_duplicate_search": {"candidates": len(pairs),
                                       "confirmed_same_image": sum(p["decision"] == "same_image" for p in pairs),
                                       "rejected_different": sum(p["decision"] == "different" for p in pairs),
                                       "groups": len(sizes), "quarantined": len(near_q),
                                       "thresholds": {"phash_hamming_max": 6, "clip_cosine_min": 0.95}},
             "scene_approach": "B: EmoSet scene unavailable, scene_source_raw absent (approval N1 not given)"}
    command = (f"python -m data_preparation.build v1 --places-dir {rel(a.places_dir, root)} --emoset-zip "
               f"{rel(a.emoset_zip, root)} --near-dup-decisions {rel(decisions_path, root)}")
    recs, issues, build = write_manifest(NAMES["v1"], final, inputs, extra, root, command)
    state["records"] = recs
    return recs, issues, build, state
