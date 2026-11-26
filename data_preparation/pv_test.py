"""Independent PV-Test (method 3.4): intake with privacy export, blank annotation sheets, merge, freeze.

    python -m data_preparation.pv_test intake --workdir <W>   # originals + intake.csv -> datasets/images/pv_test/
    python -m data_preparation.pv_test sheets --workdir <W>   # two blank annotation sheets
    python -m data_preparation.pv_test merge  --workdir <W>   # two filled sheets (+ adjudication) -> pv_test_v1.jsonl

Inputs (never shared outside the team, never zipped): <W>/external/pv_test_originals/ with the photos and
intake.csv (columns: original_file, photographer_id, written_consent, no_identifiable_faces, planned_group, notes).
`written_consent` and `no_identifiable_faces` are answered `yes` by a person who checked; no model is run.
Nobody runs a model on PV-Test before the freeze, and nothing is tuned on it. A frozen file is never changed:
a correction is pv_test_v2.
"""
import argparse
import io
import os
import sys

from contracts.taxonomy import load_taxonomy
from contracts.validate import validate_file

from .common import (PACKAGE_ROOT, SCHEMA_VERSION, TAXONOMY_VERSION, jsonl_bytes, order_record, read_csv,
                     sha256_bytes, sha256_file, write_bytes, write_csv, write_text)

GROUPS = ["desert", "sea", "greenery", "heritage", "sky_night", "unsupported"]
SHEET_FIELDS = ["pv_id", "scene", "acceptable_img_emotions", "acceptable_lit_emotions", "annotator_id", "date",
                "notes"]
LICENSE_PV = "team photo, used with the photographer's written consent for this project"
PROTOCOL_PV = ("PV-Test: two team annotators labeled each photo independently and blind to any model output: scene "
               "(17 scene ids or ambiguous), acceptable image emotions, acceptable literary emotions. Acceptable sets "
               "are the union of both annotators; scene by agreement, otherwise adjudicated by Omar "
               "(data_preparation/pv_test.py, method section 3.4).")


def paths(w):
    return {"originals": os.path.join(w, "external", "pv_test_originals"),
            "images": os.path.join(w, "datasets", "images", "pv_test"),
            "eval": os.path.join(w, "evaluation", "pv_test"),
            "manifest": os.path.join(w, "datasets", "manifests", "pv_test_v1.jsonl")}


def privacy_export(data):
    """Apply EXIF orientation, drop all metadata (location, device), save as JPEG once. Returns new bytes."""
    from PIL import Image, ImageOps
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    clean = Image.new("RGB", im.size)
    clean.putdata(list(im.getdata()))
    buf = io.BytesIO()
    clean.save(buf, "JPEG", quality=95)
    return buf.getvalue()


def intake(w):
    p = paths(w)
    rows = read_csv(os.path.join(p["originals"], "intake.csv"))
    problems = []
    for r in rows:
        if r["written_consent"].strip().lower() != "yes":
            problems.append(f"{r['original_file']}: no written consent")
        if r["no_identifiable_faces"].strip().lower() != "yes":
            problems.append(f"{r['original_file']}: face check not passed")
        if r["planned_group"] not in GROUPS:
            problems.append(f"{r['original_file']}: planned_group must be one of {GROUPS}")
    if problems:
        raise SystemExit("STOP:\n  " + "\n  ".join(problems))
    if not 30 <= len(rows) <= 40:
        print(f"note: {len(rows)} photos; the plan is 30-40")
    os.makedirs(p["images"], exist_ok=True)
    private_map = []
    for k, r in enumerate(sorted(rows, key=lambda r: r["original_file"]), 1):
        with open(os.path.join(p["originals"], r["original_file"]), "rb") as fh:
            data = privacy_export(fh.read())
        pv_id = f"pv_{k:04d}"
        target = os.path.join(p["images"], pv_id + ".jpg")
        if os.path.exists(target):
            raise SystemExit(f"STOP: {target} exists; PV-Test photos are frozen once exported")
        write_bytes(target, data)
        private_map.append({"pv_id": pv_id, "original_file": r["original_file"], "planned_group": r["planned_group"],
                            "photographer_id": r["photographer_id"], "sha256": sha256_bytes(data)})
    # the original-name map stays with the originals (private); the composition is public
    write_csv(os.path.join(p["originals"], "pv_id_map_private.csv"), private_map,
              ["pv_id", "original_file", "planned_group", "photographer_id", "sha256"])
    write_csv(os.path.join(p["eval"], "composition.csv"), private_map, ["pv_id", "planned_group", "sha256"])
    print(f"exported {len(private_map)} photos to datasets/images/pv_test/")


def sheets(w):
    p = paths(w)
    ids = sorted(f[:-4] for f in os.listdir(p["images"]) if f.endswith(".jpg")) if os.path.isdir(p["images"]) else []
    for who in ("A", "B"):
        write_csv(os.path.join(p["eval"], f"annotation_sheet_{who}.csv"), [{"pv_id": i} for i in ids], SHEET_FIELDS)
    print(f"blank sheets for {len(ids)} photos in evaluation/pv_test/ (annotation_sheet_A.csv, _B.csv)")


def _ids(cell, layer, tax):
    vals = [v.strip() for v in (cell or "").split(";") if v.strip()]
    bad = [v for v in vals if tax.layer(v) != layer]
    if bad:
        raise SystemExit(f"STOP: not {layer} ids: {bad}")
    return vals


def merge(w, date):
    p = paths(w)
    if os.path.exists(p["manifest"]):
        raise SystemExit("STOP: pv_test_v1.jsonl is frozen; a correction is pv_test_v2 with a changelog")
    tax = load_taxonomy()
    scenes = set(tax.class_order["scene"])
    a = {r["pv_id"]: r for r in read_csv(os.path.join(p["eval"], "annotation_sheet_A.csv"))}
    b = {r["pv_id"]: r for r in read_csv(os.path.join(p["eval"], "annotation_sheet_B.csv"))}
    adj_path = os.path.join(p["eval"], "adjudication.csv")
    adj = {r["pv_id"]: r for r in read_csv(adj_path)} if os.path.exists(adj_path) else {}
    if set(a) != set(b):
        raise SystemExit("STOP: the two sheets list different photos")
    ann = sorted({r["annotator_id"] for r in a.values()} | {r["annotator_id"] for r in b.values()})
    if len({r["annotator_id"] for r in a.values()}) != 1 or len({r["annotator_id"] for r in b.values()}) != 1 \
            or a[next(iter(a))]["annotator_id"] == b[next(iter(b))]["annotator_id"]:
        raise SystemExit("STOP: each sheet needs one annotator id, and the two must differ")
    recs, need_adj = [], []
    for pv_id in sorted(a):
        ra, rb = a[pv_id], b[pv_id]
        for r in (ra, rb):
            if r["scene"] not in scenes | {"ambiguous"}:
                raise SystemExit(f"STOP: {pv_id}: scene must be one of the 17 scene ids or 'ambiguous'")
        if ra["scene"] == rb["scene"] != "ambiguous":
            scene, review, ambiguous = ra["scene"], "human_double", False
        elif pv_id in adj and adj[pv_id]["scene"] in scenes:
            scene, review, ambiguous = adj[pv_id]["scene"], "adjudicated", True
        else:
            need_adj.append(pv_id)
            continue
        img = os.path.join(p["images"], pv_id + ".jpg")
        from PIL import Image
        with Image.open(img) as im:
            wdt, hgt = im.size
        recs.append({
            "schema_version": SCHEMA_VERSION, "taxonomy_version": TAXONOMY_VERSION,
            "image_id": f"img:pv_test:{pv_id}", "source_dataset": "pv_test", "source_image_id": pv_id,
            "image_path": f"datasets/images/pv_test/{pv_id}.jpg", "image_sha256": sha256_file(img),
            "width": wdt, "height": hgt, "split": "test", "split_origin": "independent_test", "near_dup_group": None,
            "scene_label": scene, "scene_label_status": "labeled", "scene_label_source": "human_annotation",
            "scene_source_raw": None, "scene_ambiguous": ambiguous,
            "emotion_label": None, "emotion_label_status": "labeled_set", "emotion_label_source": "human_annotation",
            "acceptable_img_emotions": sorted(set(_ids(ra["acceptable_img_emotions"], "img_emotion", tax)) |
                                              set(_ids(rb["acceptable_img_emotions"], "img_emotion", tax))),
            "acceptable_lit_emotions": sorted(set(_ids(ra["acceptable_lit_emotions"], "lit_emotion", tax)) |
                                              set(_ids(rb["acceptable_lit_emotions"], "lit_emotion", tax))),
            "annotation_provenance": {"protocol": PROTOCOL_PV, "annotators": ann, "date": date},
            "review_status": review, "license_terms": LICENSE_PV})
    if need_adj:
        write_csv(adj_path if not os.path.exists(adj_path) else adj_path + ".todo.csv",
                  [{"pv_id": i, "scene_A": a[i]["scene"], "scene_B": b[i]["scene"]} for i in need_adj],
                  ["pv_id", "scene_A", "scene_B", "scene", "adjudicator_id", "date"])
        raise SystemExit(f"STOP: {len(need_adj)} photos need Omar's scene adjudication (evaluation/pv_test/"
                         f"adjudication.csv)")
    data = jsonl_bytes([order_record(r) for r in recs])
    write_bytes(p["manifest"], data)
    issues = validate_file("image_manifest", p["manifest"], mode="production")
    if issues:
        os.remove(p["manifest"])
        raise SystemExit(f"STOP: validator found {len(issues)} issues; nothing frozen: {issues[:3]}")
    lines = [f"{sha256_bytes(data)}  datasets/manifests/pv_test_v1.jsonl"] + \
            [f"{r['image_sha256']}  {r['image_path']}" for r in recs]
    write_text(p["manifest"].replace(".jsonl", ".sha256"), "\n".join(lines) + "\n")
    print(f"frozen pv_test_v1.jsonl: {len(recs)} photos; hashes in pv_test_v1.sha256")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["intake", "sheets", "merge"])
    ap.add_argument("--workdir", default=PACKAGE_ROOT)
    ap.add_argument("--date", default=None, help="merge: annotation date YYYY-MM-DD (required for merge)")
    a = ap.parse_args(argv)
    w = os.path.abspath(a.workdir)
    if a.step == "intake":
        intake(w)
    elif a.step == "sheets":
        sheets(w)
    else:
        if not a.date:
            raise SystemExit("merge needs --date YYYY-MM-DD")
        merge(w, a.date)
    return 0


if __name__ == "__main__":
    sys.exit(main())
