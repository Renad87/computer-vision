"""N1: official EmoSet-118K metadata (image_id, emotion, scene) without any image bytes.

The official release is one 11.3 GB zip on Dropbox (link in the official README,
github.com/JingyuanYY/EmoSet). Its annotation JSON files sit in one contiguous block at the start of
the zip, before every image entry. This tool reads, with HTTP range requests only:

  1. the zip's end records and central directory (entry names, sizes, offsets, CRC32);
  2. the byte span of the annotation/*.json entries (asserted to contain no image/ entry);
  3. the official train.json, val.json, test.json and info.json entries.

Every entry is CRC32-checked. Of each annotation only image_id, emotion and scene are kept;
every fetched byte range is logged in bytes_ledger.jsonl.

    python3 -I -B evaluation/annotation/emoset_n1/emoset_n1.py fetch  --out external/emoset_metadata
    python3 -I -B evaluation/annotation/emoset_n1/emoset_n1.py align  --meta external/emoset_metadata \
        --zip external/renad/emoset.zip --report evaluation/annotation/emoset_n1
    python3 -I -B evaluation/annotation/emoset_n1/emoset_n1.py sample --meta external/emoset_metadata \
        --zip external/renad/emoset.zip --report evaluation/annotation/emoset_n1

Standard library only (plus contracts/ from this repository for the taxonomy).
"""
import argparse
import collections
import csv
import datetime
import hashlib
import json
import math
import os
import random
import struct
import sys
import urllib.request
import zipfile
import zlib

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, REPO)
from contracts.taxonomy import load_taxonomy  # noqa: E402

OFFICIAL_REPO = "https://github.com/JingyuanYY/EmoSet"
OFFICIAL_ZIP_URL = ("https://www.dropbox.com/scl/fi/myue506itjfc06m7svdw6/EmoSet-118K.zip"
                    "?dl=1&rlkey=7f3oyjkr6zyndf0gau7t140rv")
METADATA_FILE = "emoset118k_image_emotion_scene.jsonl"
AUDIT_PER_CLASS = 25
AUDIT_SEED = 42


class RangeReader:
    def __init__(self, url, ledger_path):
        self.url, self.ledger_path, self.total_bytes = url, ledger_path, 0

    def get(self, start, end, note):
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}",
                                                        "User-Agent": "range-reader/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            status, content_range, data = resp.status, resp.headers.get("Content-Range"), resp.read()
        if status != 206 or len(data) != end - start + 1:
            raise SystemExit(f"range {start}-{end}: status {status}, {len(data)} bytes")
        self.total_bytes += len(data)
        with open(self.ledger_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"range": [start, end], "bytes": len(data), "content_range": content_range,
                                 "note": note}) + "\n")
        return data, content_range


def parse_central_directory(cd):
    entries, p = [], 0
    while p < len(cd):
        (sig, _, _, _, method, _, _, crc, csize, usize, nlen, elen, clen, _, _, _,
         lho) = struct.unpack("<IHHHHHHIIIHHHHHII", cd[p:p + 46])
        if sig != 0x02014B50:
            raise SystemExit(f"bad central directory signature at {p}")
        name = cd[p + 46:p + 46 + nlen].decode("utf-8")
        extra, q = cd[p + 46 + nlen:p + 46 + nlen + elen], 0
        while q + 4 <= len(extra):
            hid, hlen = struct.unpack("<HH", extra[q:q + 4])
            if hid == 1:  # zip64 extended information
                vals, k = list(struct.unpack("<" + "Q" * (hlen // 8), extra[q + 4:q + 4 + hlen // 8 * 8])), 0
                if usize == 0xFFFFFFFF:
                    usize, k = vals[k], k + 1
                if csize == 0xFFFFFFFF:
                    csize, k = vals[k], k + 1
                if lho == 0xFFFFFFFF:
                    lho, k = vals[k], k + 1
            q += 4 + hlen
        entries.append({"name": name, "method": method, "crc": crc, "csize": csize, "usize": usize, "lho": lho})
        p += 46 + nlen + elen + clen
    return entries


def unpack_entry(blob, base, entry):
    o = entry["lho"] - base
    sig, _, _, method, _, _, _, _, _, nlen, elen = struct.unpack("<IHHHHHIIIHH", blob[o:o + 30])
    if sig != 0x04034B50:
        raise SystemExit(f"bad local header for {entry['name']}")
    raw = blob[o + 30 + nlen + elen:o + 30 + nlen + elen + entry["csize"]]
    data = zlib.decompress(raw, -15) if method == 8 else raw
    if len(data) != entry["usize"] or (zlib.crc32(data) & 0xFFFFFFFF) != entry["crc"]:
        raise SystemExit(f"CRC/size mismatch for {entry['name']}")
    return data


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def cmd_fetch(args):
    os.makedirs(args.out, exist_ok=True)
    ledger = os.path.join(args.out, "bytes_ledger.jsonl")
    if os.path.exists(ledger):
        os.remove(ledger)
    reader = RangeReader(OFFICIAL_ZIP_URL, ledger)
    _, content_range = reader.get(0, 0, "size probe")
    total = int(content_range.split("/")[1])
    tail_len = 1 << 16
    tail, _ = reader.get(total - tail_len, total - 1, "end of central directory + zip64 locator")
    eocd = struct.unpack("<4sHHHHIIH", tail[tail.rfind(b"PK\x05\x06"):][:22])
    count, cd_size, cd_off = eocd[4], eocd[5], eocd[6]
    loc = tail.rfind(b"PK\x06\x07")
    if loc != -1:
        z64_off = struct.unpack("<4sIQI", tail[loc:loc + 20])[2]
        rec, _ = reader.get(z64_off, z64_off + 55, "zip64 end of central directory record")
        fields = struct.unpack("<4sQHHIIQQQQ", rec[:56])
        count, cd_size, cd_off = fields[7], fields[8], fields[9]
    cd, _ = reader.get(cd_off, cd_off + cd_size - 1, "central directory (names, sizes, offsets only)")
    entries = sorted(parse_central_directory(cd), key=lambda e: e["lho"])
    if len(entries) != count:
        raise SystemExit("entry count mismatch")
    next_offset = {e["name"]: (entries[i + 1]["lho"] if i + 1 < len(entries) else cd_off)
                   for i, e in enumerate(entries)}
    block = []
    for entry in entries:
        if not entry["name"].startswith("annotation/"):
            break
        block.append(entry)
    if any(not e["name"].startswith("annotation/") for e in block):
        raise SystemExit("annotation block contains a non-annotation entry")
    first_after = entries[len(block)]["name"]
    if not first_after.startswith(("image/", "info.json", "train.json", "val.json", "test.json")):
        raise SystemExit(f"unexpected entry after annotation block: {first_after}")
    start, end = block[0]["lho"], next_offset[block[-1]["name"]] - 1
    blob, _ = reader.get(start, end, "annotation/*.json block (no image/ entry inside)")
    annotations = {}
    for entry in block:
        if entry["name"].endswith(".json"):
            record = json.loads(unpack_entry(blob, start, entry))
            annotations[record["image_id"]] = {"image_id": record["image_id"], "emotion": record["emotion"],
                                               "scene": record.get("scene"), "zip_entry": entry["name"]}
    del blob
    split_of = {}
    official_files = {}
    for name in ("train.json", "val.json", "test.json", "info.json"):
        entry = next(e for e in entries if e["name"] == name)
        data, _ = reader.get(entry["lho"], next_offset[name] - 1, f"official {name}")
        official_files[name] = unpack_entry(data, entry["lho"], entry)
        if name != "info.json":
            for emotion, image_path, annotation_path in json.loads(official_files[name]):
                image_id = os.path.splitext(os.path.basename(image_path))[0]
                if image_id in split_of:
                    raise SystemExit(f"{image_id} in two official splits")
                split_of[image_id] = (name[:-5], emotion, annotation_path)
    with open(os.path.join(args.out, "official_zip_info.json"), "wb") as fh:
        fh.write(official_files["info.json"])
    rows = []
    for image_id in sorted(annotations):
        a = annotations[image_id]
        split, split_emotion, annotation_path = split_of.get(image_id, (None, None, None))
        if split_emotion is not None and (split_emotion != a["emotion"] or annotation_path != a["zip_entry"]):
            raise SystemExit(f"official split file disagrees with annotation for {image_id}")
        rows.append({"image_id": image_id, "emotion": a["emotion"], "scene": a["scene"], "official_split": split})
    meta_path = os.path.join(args.out, METADATA_FILE)
    with open(meta_path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    info_path = os.path.join(args.out, "official_repo_info.json")
    with urllib.request.urlopen(f"https://raw.githubusercontent.com/JingyuanYY/EmoSet/{args.repo_commit}/info.json",
                                timeout=120) as resp:
        info_bytes = resp.read()
    with open(info_path, "wb") as fh:
        fh.write(info_bytes)
    provenance = {
        "dataset": "EmoSet-118K (Yang et al., ICCV 2023)",
        "official_repository": OFFICIAL_REPO,
        "official_repository_commit": args.repo_commit,
        "official_zip_url": OFFICIAL_ZIP_URL,
        "official_zip_bytes": total,
        "official_zip_entries": count,
        "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "HTTP range requests: zip central directory, the contiguous annotation/*.json block, and the "
                  "official split/info JSON entries. No image/ entry was requested. Every entry CRC32-checked.",
        "fields_kept": ["image_id", "emotion", "scene", "official_split"],
        "fields_discarded": "every other annotation attribute (brightness, colorfulness, object, facial_expression, "
                            "human_action); they were transferred inside the same JSON files but not stored",
        "bytes_transferred_from_zip": reader.total_bytes,
        "bytes_transferred_from_github": len(info_bytes),
        "annotation_files": len(annotations),
        "rows_with_scene": sum(1 for r in rows if r["scene"]),
        "official_split_counts": dict(collections.Counter(r["official_split"] for r in rows)),
        "licence": "not stated for the data; the repository's MIT licence covers its code",
        "files": {name: {"sha256": sha256_file(os.path.join(args.out, name)),
                         "bytes": os.path.getsize(os.path.join(args.out, name))}
                  for name in (METADATA_FILE, "official_zip_info.json", "official_repo_info.json", "bytes_ledger.jsonl")},
    }
    with open(os.path.join(args.out, "PROVENANCE.json"), "w", encoding="utf-8") as fh:
        json.dump(provenance, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps({k: provenance[k] for k in ("bytes_transferred_from_zip", "annotation_files", "rows_with_scene",
                                                 "official_split_counts")}))


def load_metadata(meta_dir):
    with open(os.path.join(meta_dir, METADATA_FILE), encoding="utf-8") as fh:
        return {r["image_id"]: r for r in map(json.loads, fh)}


def recovered_images(zip_path):
    rows = []
    with zipfile.ZipFile(zip_path) as z:
        for name in sorted(z.namelist()):
            if name.endswith(".jpg"):
                _, split, emotion, filename = name.split("/")
                rows.append({"split": split, "emotion": emotion, "image_id": filename[:-4], "zip_path": name})
    return rows


def wilson(k, n, z=1.96):
    if n == 0:
        return None, None
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return round(centre - half, 4), round(centre + half, 4)


def scene_outcomes(meta_dir, zip_path):
    tax = load_taxonomy()
    meta = load_metadata(meta_dir)
    with open(os.path.join(meta_dir, "official_repo_info.json"), encoding="utf-8") as fh:
        vocab = set(json.load(fh)["scene"]["label2idx"])
    known = {c: label for label, cats in tax.data["places365_mapping"].items() for c in cats}
    out = []
    for img in recovered_images(zip_path):
        m = meta.get(img["image_id"])
        row = dict(img, matched=m is not None, meta_emotion=m and m["emotion"], official_split=m and m["official_split"],
                   scene_raw=m and m["scene"], scene_label=None, scene_status=None, truncation_candidates=[])
        if m is not None and m["scene"]:
            label, status = tax.map_places365(m["scene"])
            row["scene_label"], row["scene_status"] = label, status
            row["in_official_vocab"] = m["scene"] in vocab
            if status == "unmapped":
                row["truncation_candidates"] = sorted(f"{c} -> {lab}" for c, lab in known.items()
                                                      if c.startswith(m["scene"] + "/"))
        elif m is not None:
            row["scene_status"] = "missing"
        out.append(row)
    return out


def cmd_align(args):
    rows = scene_outcomes(args.meta, args.zip)
    os.makedirs(args.report, exist_ok=True)
    unmatched = [r["image_id"] for r in rows if not r["matched"]]
    emotion_mismatch = [r["image_id"] for r in rows if r["matched"] and r["meta_emotion"] != r["emotion"]]
    split_cmp = collections.Counter(f"{r['split']}->{r['official_split']}" for r in rows)
    status = collections.Counter(r["scene_status"] for r in rows)
    per_split = collections.defaultdict(collections.Counter)
    per_emotion = collections.defaultdict(collections.Counter)
    labels = collections.Counter()
    raw = collections.defaultdict(lambda: {"count": 0, "splits": collections.Counter()})
    for r in rows:
        per_split[r["split"]][r["scene_status"]] += 1
        per_emotion[r["emotion"]][r["scene_status"]] += 1
        if r["scene_status"] == "labeled":
            labels[(r["scene_label"], r["split"])] += 1
        if r["scene_raw"]:
            entry = raw[r["scene_raw"]]
            entry["count"] += 1
            entry["splits"][r["split"]] += 1
            entry.update(status=r["scene_status"], label=r["scene_label"], in_official_vocab=r["in_official_vocab"],
                         truncation_candidates=r["truncation_candidates"])
    ambiguous = {k: v for k, v in raw.items() if v["truncation_candidates"]}
    summary = {
        "recovered_images": len(rows), "unmatched_ids": unmatched, "emotion_mismatches": emotion_mismatch,
        "renad_split_vs_official_split": dict(split_cmp),
        "scene_status": dict(status),
        "scene_status_per_split": {k: dict(v) for k, v in sorted(per_split.items())},
        "scene_status_per_emotion": {k: dict(v) for k, v in sorted(per_emotion.items())},
        "labeled_per_class_and_split": {f"{lab}|{split}": n for (lab, split), n in sorted(labels.items())},
        "distinct_raw_scenes": len(raw),
        "raw_outside_official_vocabulary": sorted(k for k, v in raw.items() if not v["in_official_vocab"]),
        "ambiguous_truncated_names": {k: {"count": v["count"], "candidates": v["truncation_candidates"]}
                                      for k, v in sorted(ambiguous.items(), key=lambda kv: -kv[1]["count"])},
    }
    with open(os.path.join(args.report, "alignment_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(args.report, "emoset_scene_raw_values.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["scene_raw", "count", "train", "val", "test", "map_places365_status", "scene_label",
                    "in_official_vocabulary", "truncation_candidates"])
        for k, v in sorted(raw.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            w.writerow([k, v["count"], v["splits"]["train"], v["splits"]["val"], v["splits"]["test"], v["status"],
                        v["label"] or "", v["in_official_vocab"], "; ".join(v["truncation_candidates"])])
    print(json.dumps({k: summary[k] for k in ("recovered_images", "renad_split_vs_official_split", "scene_status")}))
    print("unmatched", len(unmatched), "emotion mismatches", len(emotion_mismatch),
          "ambiguous truncated names", len(ambiguous), "images", sum(v["count"] for v in ambiguous.values()))


def cmd_sample(args):
    rows = [r for r in scene_outcomes(args.meta, args.zip) if r["scene_status"] == "labeled"]
    by_class = collections.defaultdict(list)
    for r in rows:
        by_class[r["scene_label"]].append(r)
    tax = load_taxonomy()
    sample, sizes = [], {}
    for label in tax.class_order["scene"]:
        pool = sorted(by_class.get(label, []), key=lambda r: r["image_id"])
        chosen = sorted(random.Random(f"{AUDIT_SEED}:{label}").sample(pool, min(AUDIT_PER_CLASS, len(pool))),
                        key=lambda r: r["image_id"])
        sizes[label] = {"available": len(pool), "sampled": len(chosen),
                        "max_precision_ci_width_if_all_yes": (None if not chosen else
                                                              round(1 - wilson(len(chosen), len(chosen))[0], 4))}
        sample.extend(chosen)
    path = os.path.join(args.report, "scene_audit_sample_v1.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["image_id", "zip_path", "split", "emotion", "scene_raw", "scene_label", "decision", "reviewer_id",
                    "date", "notes"])
        for r in sample:
            w.writerow([r["image_id"], r["zip_path"], r["split"], r["emotion"], r["scene_raw"], r["scene_label"],
                        "", "", "", ""])
    with open(os.path.join(args.report, "scene_audit_sample_sizes.json"), "w", encoding="utf-8") as fh:
        json.dump({"seed": AUDIT_SEED, "per_class_cap": AUDIT_PER_CLASS, "threshold": 0.80,
                   "decisions": "pending human review; none recorded", "classes": sizes}, fh, indent=1)
        fh.write("\n")
    print(f"sampled {len(sample)} images over {sum(1 for s in sizes.values() if s['sampled'])} classes")
    for label, s in sizes.items():
        print(f"  {label:28s} available {s['available']:4d}  sampled {s['sampled']:2d}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fetch")
    p.add_argument("--out", required=True)
    p.add_argument("--repo-commit", default="4e3288652a07c7b2334c55d2694f7a1d59692f40")
    for name in ("align", "sample"):
        p = sub.add_parser(name)
        p.add_argument("--meta", required=True)
        p.add_argument("--zip", required=True)
        p.add_argument("--report", required=True)
    args = parser.parse_args(argv)
    {"fetch": cmd_fetch, "align": cmd_align, "sample": cmd_sample}[args.cmd](args)


if __name__ == "__main__":
    main()
