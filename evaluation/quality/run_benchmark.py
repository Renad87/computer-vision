"""Frozen before/after quality benchmark over the running app (real model, real retrieval).

    python3 -m evaluation.quality.run_benchmark select            # writes evaluation/quality/benchmark_set.json (once)
    python3 -m evaluation.quality.run_benchmark run --label before # runs every image x emotion x mode, writes runs/<label>.json

Images: 16 real photos from the Places365 TEST split (2 per scene type), chosen deterministically (sorted ids).
Places365 terms are not verified: internal research use only, images are not redistributed (not copied into git).
Queries: the app's own suggestion for visual items + each of the 5 pilot literary emotions, in production and development.
This is a system/behaviour benchmark for side-by-side human reading. It is NOT an accuracy or relevance measurement.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SET_PATH = os.path.join(HERE, "benchmark_set.json")
RUNS = os.path.join(HERE, "runs")
PLACES_DIR = os.path.join(REPO, "external", "shaden_visual", "data", "places365")
# scene type -> Places365 raw categories (first two sorted test images across these categories)
TYPES = [
    ("mountains", ["mountain", "valley"]),
    ("sea", ["coast", "beach", "ocean"]),
    ("desert", ["desert/sand", "desert/vegetation"]),
    ("sky_sunset_stars", ["sky"]),
    ("greenery", ["forest/broadleaf", "botanical_garden", "formal_garden"]),
    ("heritage", ["ruin", "castle", "palace", "temple/asia", "pagoda", "medina", "mosque/outdoor", "tower"]),
    ("water_rain", ["waterfall", "river", "lake/natural", "creek"]),
    ("city_night", ["skyscraper", "downtown", "street"]),
]
LIT = ["lit_emotion.longing", "lit_emotion.sadness", "lit_emotion.awe", "lit_emotion.serenity", "lit_emotion.joy"]


def select():
    rows = [json.loads(l) for l in open(os.path.join(REPO, "datasets", "manifests", "manifest_v1.jsonl"), encoding="utf-8")]
    test = sorted((r for r in rows if r["source_dataset"].startswith("places") and r["split"] == "test"),
                  key=lambda r: r["image_id"])
    chosen = []
    for kind, cats in TYPES:
        pool = [r for r in test if r.get("scene_source_raw") in cats]
        for r in pool[:2]:
            raw = r["scene_source_raw"].replace("/", "-")
            path = os.path.join(PLACES_DIR, raw, r["source_image_id"] + ".jpg")
            with open(path, "rb") as fh:
                sha = hashlib.sha256(fh.read()).hexdigest()
            assert sha == r["image_sha256"], path
            chosen.append({"type": kind, "image_id": r["image_id"], "places_category": r["scene_source_raw"],
                           "scene_label": r["scene_label"], "path": os.path.relpath(path, REPO), "sha256": sha})
    with open(SET_PATH, "w", encoding="utf-8") as fh:
        json.dump({"created": "2026-11-26", "note": __doc__.strip().splitlines()[3], "images": chosen,
                   "lit_emotions": LIT, "modes": ["production", "development"]}, fh, ensure_ascii=False, indent=1)
    print(len(chosen), "images ->", SET_PATH)


def call(req):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read()), (time.perf_counter() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), (time.perf_counter() - t0) * 1000


def analyze(base, path):
    b = uuid.uuid4().hex
    data = open(path, "rb").read()
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"x.jpg\"\r\n"
            f"Content-Type: image/jpeg\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
    return call(urllib.request.Request(base + "/api/analyze", body, {"Content-Type": f"multipart/form-data; boundary={b}"}))


def recommend(base, payload):
    return call(urllib.request.Request(base + "/api/recommend", json.dumps(payload).encode(),
                                       {"Content-Type": "application/json"}))


def top(preds, n=3):
    return [[p["id"], round(p["score"], 4)] for p in sorted(preds, key=lambda p: -p["score"])[:n]]


def run(base, label):
    spec = json.load(open(SET_PATH, encoding="utf-8"))
    ready = json.loads(urllib.request.urlopen(base + "/api/ready").read())
    cases = []
    for img in spec["images"]:
        st, a, ms = analyze(base, os.path.join(REPO, img["path"]))
        case = dict(img, analyze_http=st)
        if st != 200:
            case["error"] = a
            cases.append(case)
            continue
        inf = a["inference"]
        sug = a["suggestion"]
        items = [{"id": v["id"], "user_selection": "primary"} for v in sug["visual_items"]]
        case.update({"scene_status": inf["scene"]["status"], "scene_top": top(inf["scene"]["predictions"]),
                     "emotion_status": inf["emotion"]["status"], "emotion_top": top(inf["emotion"]["predictions"]),
                     "emotion_extra": {k: inf["emotion"].get(k) for k in ("margin", "entropy")},
                     "tags_present": [t["id"] for t in inf["tags"] if t["present"]],
                     "suggested_items": [v["id"] for v in sug["visual_items"]],
                     "suggested_lit": [s["id"] for s in sug["lit_emotions"]], "runs": []})
        for lit in spec["lit_emotions"]:
            for mode in spec["modes"]:
                st, r, ms = recommend(base, {"analysis_id": a["analysis_id"], "mode": mode, "selected_lit_emotion": lit,
                                             "confirmed_visual_items": items})
                run_ = {"lit": lit, "mode": mode, "http": st}
                if st == 200:
                    rec = r["recommendations"]
                    run_.update({"status": rec["status"],
                                 "abstention": (rec["abstention"] or {}).get("reason_code"),
                                 "items": [{"verse_id": it["verse_id"], "tier": it["tier"], "scores": it["scores"],
                                            "relations": it["matched"]["relations"],
                                            "targets": it["matched"]["visual_targets"],
                                            "emotion_role": it["matched"]["emotion_role"],
                                            "poet": it["poet_name_apcd"], "text": it["text_original"],
                                            "why": it["explanation"]["sentences_ar"]} for it in rec["items"]]})
                else:
                    run_["error"] = r
                case["runs"].append(run_)
        cases.append(case)
    os.makedirs(RUNS, exist_ok=True)
    out = os.path.join(RUNS, f"{label}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"label": label, "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "model": {k: ready["model"].get(k) for k in ("model_version", "fingerprints")},
                   "corpus": {k: ready["corpus"].get(k) for k in ("version", "sha256", "count", "displayable")},
                   "engine_version": ready.get("engine_version"), "cases": cases}, fh, ensure_ascii=False, indent=1)
    print("wrote", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["select", "run"])
    ap.add_argument("--base", default="http://127.0.0.1:8010")
    ap.add_argument("--label", default="before")
    args = ap.parse_args()
    select() if args.cmd == "select" else run(args.base, args.label)
