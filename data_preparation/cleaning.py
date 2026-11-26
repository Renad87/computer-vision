"""Inventory, cleaning (method section 5) and exact-duplicate handling (method section 6.1)."""
from collections import defaultdict

from .common import MIN_SIDE, PROTECTION, phash64, probe_image, sha256_bytes

# provisional flags for a visual check (method section 5); flagged images are kept unless broken
NEAR_BLACK, NEAR_WHITE, UNIFORM_STD = 0.08, 0.95, 0.02
DECISION_DATE = "2026-11-25"          # date the automatic rules were fixed (method v1); keeps builds deterministic
RULE_DECIDER = "rule:unified_dataset_method_v1_section_6.1"


def inspect(items, with_phash=False):
    """items: iterable of (record, image_bytes, source_member). Returns (records, inventory, excluded, flagged).

    `records` get image_sha256 / width / height from the delivered bytes. Excluded images are left out.
    """
    records, inventory, excluded, flagged = [], [], [], []
    for rec, data, member in items:
        info = probe_image(data)
        sha = sha256_bytes(data)
        ext = member.rsplit(".", 1)[-1].lower()
        row = {"image_id": rec["image_id"], "source_dataset": rec["source_dataset"], "split": rec["split"],
               "label": rec["emotion_label"] or rec["scene_label"] or rec["scene_label_status"],
               "member": member, "bytes": len(data), "sha256": sha, **info,
               "extension": ext,
               "extension_matches_format": info.get("format") == {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG"}.get(ext)}
        if with_phash and info["decodes"]:
            row["phash"] = phash64(data)
        inventory.append(row)
        reason = None
        if not info["decodes"]:
            reason = "undecodable"
        elif min(info["width"], info["height"]) < MIN_SIDE:
            reason = f"smaller_than_{MIN_SIDE}px"
        if reason:
            excluded.append({"image_id": rec["image_id"], "source_dataset": rec["source_dataset"],
                             "split": rec["split"], "source_member": member, "image_sha256": sha,
                             "reason": reason, "detail": info.get("error") or
                             f"{info.get('width')}x{info.get('height')}"})
            continue
        flags = []
        if info["mean_luminance"] < NEAR_BLACK:
            flags.append("near_black")
        if info["mean_luminance"] > NEAR_WHITE:
            flags.append("near_white")
        if info["std_luminance"] < UNIFORM_STD:
            flags.append("near_uniform")
        if flags:
            flagged.append({"image_id": rec["image_id"], "split": rec["split"], "image_path": rec["image_path"],
                            "flags": "+".join(flags), "mean_luminance": info["mean_luminance"],
                            "std_luminance": info["std_luminance"], "visual_check": ""})
        records.append({**rec, "image_sha256": sha, "width": info["width"], "height": info["height"]})
    return records, inventory, excluded, flagged


def _labels(r):
    return (r["scene_label"], r["scene_label_status"], r["emotion_label"], r["emotion_label_status"])


def _q(r, reason, kept=None, evidence=None):
    return {"image_id": r["image_id"], "image_sha256": r["image_sha256"], "source_dataset": r["source_dataset"],
            "removed_from_split": r["split"], "reason": reason,
            "kept_image_id": kept["image_id"] if kept else None, "kept_split": kept["split"] if kept else None,
            "evidence": evidence or {"method": "sha256", "match": "identical"},
            "decided_by": RULE_DECIDER, "date": DECISION_DATE}


def exact_duplicates(records):
    """Apply method 6.1. Returns (kept_records, quarantine, escalations, groups).

    escalations: identical content in two evaluation splits of different sources -> not resolved, report to Omar.
    """
    by_sha = defaultdict(list)
    for r in records:
        by_sha[r["image_sha256"]].append(r)
    removed, quarantine, escalations, groups = set(), [], [], []
    for sha in sorted(by_sha):
        g = sorted(by_sha[sha], key=lambda r: r["image_id"])
        if len(g) < 2:
            continue
        groups.append({"image_sha256": sha, "members": [(r["image_id"], r["split"]) for r in g]})
        # 1) within each split
        survivors = []
        by_split = defaultdict(list)
        for r in g:
            by_split[r["split"]].append(r)
        for split in sorted(by_split):
            s = by_split[split]
            if len(s) == 1:
                survivors.append(s[0])
            elif len({_labels(r) for r in s}) == 1:
                survivors.append(s[0])
                for r in s[1:]:
                    quarantine.append(_q(r, "exact_duplicate_same_split", kept=s[0]))
                    removed.add(r["image_id"])
            else:
                for r in s:
                    quarantine.append(_q(r, "exact_duplicate_label_conflict"))
                    removed.add(r["image_id"])
        # 2) across splits
        if len(survivors) > 1:
            top = max(PROTECTION[r["split"]] for r in survivors)
            best = [r for r in survivors if PROTECTION[r["split"]] == top]
            if top >= PROTECTION["test"] and len({(r["split"], r["source_dataset"]) for r in best}) > 1:
                escalations.append({"image_sha256": sha, "members": [(r["image_id"], r["split"]) for r in survivors],
                                    "reason": "identical content in two evaluation splits; not resolved (method 6.1)"})
                continue
            keep = best[0]
            for r in survivors:
                if r is not keep:
                    quarantine.append(_q(r, "exact_duplicate_across_splits", kept=keep))
                    removed.add(r["image_id"])
    kept = [r for r in records if r["image_id"] not in removed]
    return kept, sorted(quarantine, key=lambda q: q["image_id"]), escalations, groups
