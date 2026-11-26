"""Near-duplicate search (method 6.2): candidates, human decisions, groups and quarantine.

Candidates: pHash Hamming <= 6 OR CLIP cosine >= 0.95 (both provisional). They only nominate pairs; a person
decides every pair (`same_image` / `different`) in the decisions CSV. Confirmed pairs form connected components
(`near_dup_group`). A group spanning splits keeps only the members in its most protected split.
"""
import os
from collections import defaultdict

from .common import PROTECTION, read_csv

PHASH_MAX = 6
CLIP_MIN = 0.95
DECISIONS = ("same_image", "different")
CANDIDATE_FIELDS = ["pair_no", "image_id_a", "image_id_b", "split_a", "split_b", "source_a", "source_b",
                    "image_path_a", "image_path_b", "phash_hamming", "clip_cosine", "nominated_by",
                    "decision", "reviewer_id", "date", "notes"]


def _popcount(x):
    import numpy as np
    x = x - ((x >> np.uint64(1)) & np.uint64(0x5555555555555555))
    x = (x & np.uint64(0x3333333333333333)) + ((x >> np.uint64(2)) & np.uint64(0x3333333333333333))
    x = (x + (x >> np.uint64(4))) & np.uint64(0x0F0F0F0F0F0F0F0F)
    return ((x * np.uint64(0x0101010101010101)) >> np.uint64(56)).astype(np.int64)


def candidates(records, phash, emb):
    """records: kept manifest records (sorted). phash: image_id -> 16-hex. emb: image_path -> unit vector.

    Returns (pairs, distributions). Pairs of identical files are handled by the exact rules, not here.
    """
    import numpy as np
    ids = [r["image_id"] for r in records]
    by_id = {r["image_id"]: r for r in records}
    ph = np.array([int(phash[i], 16) for i in ids], dtype=np.uint64)
    X = np.stack([emb[r["image_path"]] for r in records]).astype(np.float32)
    n = len(ids)
    found = {}
    nn_cos = np.full(n, -1.0)
    nn_ham = np.full(n, 64)
    for a in range(0, n, 512):
        d = _popcount(ph[a:a + 512, None] ^ ph[None, :])
        S = X[a:a + 512] @ X.T
        for k in range(d.shape[0]):
            d[k, a + k] = 99
            S[k, a + k] = -1
        nn_ham[a:a + 512] = d.min(1)
        nn_cos[a:a + 512] = S.max(1)
        hit = (d <= PHASH_MAX) | (S >= CLIP_MIN)
        for i, j in zip(*np.nonzero(hit)):
            i += a
            if i < j:
                found[(i, j)] = (int(d[i - a, j]), float(S[i - a, j]))
    pairs = []
    for (i, j), (ham, cos) in sorted(found.items(), key=lambda kv: (ids[kv[0][0]], ids[kv[0][1]])):
        A, B = by_id[ids[i]], by_id[ids[j]]
        if A["image_sha256"] == B["image_sha256"]:
            continue
        by = "+".join(m for m, ok in (("phash", ham <= PHASH_MAX), ("clip", cos >= CLIP_MIN)) if ok)
        pairs.append({"image_id_a": A["image_id"], "image_id_b": B["image_id"], "split_a": A["split"],
                      "split_b": B["split"], "source_a": A["source_dataset"], "source_b": B["source_dataset"],
                      "image_path_a": A["image_path"], "image_path_b": B["image_path"], "phash_hamming": ham,
                      "clip_cosine": round(cos, 4), "nominated_by": by})
    for k, p in enumerate(pairs, 1):
        p["pair_no"] = k
    dist = {"nearest_neighbour_phash_hamming": [int(x) for x in nn_ham],
            "nearest_neighbour_clip_cosine": [round(float(x), 4) for x in nn_cos]}
    return pairs, dist


def read_decisions(path):
    """Decisions CSV (same columns as near_duplicate_candidates.csv). Returns {(id_a, id_b): row}."""
    if not path or not os.path.exists(path):
        return {}
    out = {}
    for r in read_csv(path):
        d = (r.get("decision") or "").strip()
        if d and d not in DECISIONS:
            raise ValueError(f"pair {r.get('pair_no')}: decision must be one of {DECISIONS}, got {d!r}")
        if d and not (r.get("reviewer_id") or "").strip():
            raise ValueError(f"pair {r.get('pair_no')}: a decision needs reviewer_id")
        out[(r["image_id_a"], r["image_id_b"])] = r
    return out


def merge_decisions(pairs, decisions):
    pending = 0
    for p in pairs:
        d = decisions.get((p["image_id_a"], p["image_id_b"]), {})
        p["decision"] = (d.get("decision") or "").strip()
        p["reviewer_id"] = (d.get("reviewer_id") or "").strip()
        p["date"] = (d.get("date") or "").strip()
        p["notes"] = (d.get("notes") or "").strip()
        pending += not p["decision"]
    return pending


def groups_and_quarantine(records, pairs):
    """Connected components of confirmed pairs -> (group_of, quarantine, escalations, group_sizes)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    evidence = {}
    for p in pairs:
        if p["decision"] == "same_image":
            a, b = find(p["image_id_a"]), find(p["image_id_b"])
            if a != b:
                parent[max(a, b)] = min(a, b)
            evidence.setdefault(p["image_id_a"], p)
            evidence.setdefault(p["image_id_b"], p)
    by = {r["image_id"]: r for r in records}
    comps = defaultdict(list)
    for x in list(parent):
        comps[find(x)].append(x)
    comps = sorted((sorted(m) for m in comps.values() if len(m) > 1), key=lambda m: m[0])
    group_of, quarantine, escalations, sizes = {}, [], [], []
    for k, members in enumerate(comps, 1):
        gid = f"g:{k:06d}"
        sizes.append(len(members))
        splits = {by[m]["split"] for m in members}
        if len(splits) == 1:
            for m in members:
                group_of[m] = gid
            continue
        top = max(PROTECTION[s] for s in splits)
        top_members = [m for m in members if PROTECTION[by[m]["split"]] == top]
        if top >= PROTECTION["test"] and len({(by[m]["split"], by[m]["source_dataset"]) for m in top_members}) > 1:
            escalations.append({"group": gid, "members": [(m, by[m]["split"]) for m in members],
                                "reason": "near duplicate between two evaluation sets (method 6.1/6.2): Omar decides"})
            continue
        keep_split = by[top_members[0]]["split"]
        kept = [m for m in members if by[m]["split"] == keep_split]
        for m in members:
            if by[m]["split"] == keep_split:
                group_of[m] = gid
            else:
                p = evidence[m]
                quarantine.append({
                    "image_id": m, "image_sha256": by[m]["image_sha256"], "source_dataset": by[m]["source_dataset"],
                    "removed_from_split": by[m]["split"], "reason": "near_duplicate_across_splits",
                    "kept_image_id": kept[0], "kept_split": keep_split,
                    "evidence": {"method": {"phash": "phash", "clip": "clip", "phash+clip": "phash_and_clip"}[
                        p["nominated_by"]], "phash_hamming": int(p["phash_hamming"]),
                        "clip_cosine": float(p["clip_cosine"]), "human_confirmed": True},
                    "decided_by": p["reviewer_id"], "date": p["date"]})
        if len(kept) < 2:
            for m in kept:
                group_of.pop(m, None)
    return group_of, sorted(quarantine, key=lambda q: q["image_id"]), escalations, sizes
