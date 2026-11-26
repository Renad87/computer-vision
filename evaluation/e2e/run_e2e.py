"""End-to-end check of the running app over HTTP (real model, real corpus). Writes evaluation/e2e/e2e_report_<date>.json.

    python3 -m evaluation.e2e.run_e2e --base http://127.0.0.1:8010 --images <dir> --date 2026-11-26

This measures system behaviour (statuses, latency, contract validity, mode rules). It is NOT an accuracy or
relevance evaluation: no human judged these results.
"""
import argparse
import json
import os
import statistics
import time
import urllib.request
import uuid

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, load_corpus, validate_document

TAX = load_taxonomy()


def post_image(base, path):
    boundary = uuid.uuid4().hex
    with open(path, "rb") as fh:
        data = fh.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{os.path.basename(path)}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(base + "/api/analyze", body, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return call(req)


def post_json(base, path, obj):
    req = urllib.request.Request(base + path, json.dumps(obj).encode(), {"Content-Type": "application/json"})
    return call(req)


def call(req):
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            status, payload = r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        status, payload = e.code, json.loads(e.read())
    return status, payload, (time.perf_counter() - t0) * 1000


def top(preds, n=3):
    return [(p["id"], round(p["score"], 3)) for p in sorted(preds, key=lambda p: -p["score"])[:n]]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8010")
    ap.add_argument("--images", required=True)
    ap.add_argument("--corpus", default="poetry_corpus/exports/corpus_all_v1.jsonl")
    ap.add_argument("--date", required=True)
    args = ap.parse_args(argv)
    corpus = load_corpus(args.corpus)
    with urllib.request.urlopen(args.base + "/api/ready") as r:
        ready = json.loads(r.read())
    cases, http_ms, issues_total = [], {"analyze": [], "recommend": []}, 0
    images = sorted(f for f in os.listdir(args.images) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")))
    for name in images:
        status, a, ms = post_image(args.base, os.path.join(args.images, name))
        case = {"image": name, "analyze_http": status, "analyze_ms": round(ms, 1)}
        if status != 200:
            case["error"] = a.get("error", {}).get("code")
            cases.append(case)
            continue
        http_ms["analyze"].append(ms)
        inf = a["inference"]
        case.update({"model_timings_ms": inf["timings_ms"], "scene_status": inf["scene"]["status"],
                     "scene_top": top(inf["scene"]["predictions"]), "emotion_status": inf["emotion"]["status"],
                     "emotion_top": top(inf["emotion"]["predictions"]),
                     "tags_present": [t["id"] for t in inf["tags"] if t["present"]],
                     "suggestion": a["suggestion"], "runs": []})
        sug = a["suggestion"]
        items = [{"id": it["id"], "user_selection": "primary"} for it in sug["visual_items"]]
        lits = [s["id"] for s in sug["lit_emotions"]] or ["lit_emotion.longing"]
        variants = [("suggested", lits[0], items)]
        variants.append(("emotion_changed", "lit_emotion.sadness" if lits[0] != "lit_emotion.sadness" else "lit_emotion.joy", items))
        if len(items) >= 2:
            variants.append(("focus_last_item", lits[0], [dict(i, user_selection="secondary") for i in items[:-1]]
                             + [dict(items[-1], user_selection="focus")]))
        for label, lit, its in variants:
            for mode in ("production", "development"):
                st, rr, ms = post_json(args.base, "/api/recommend", {"analysis_id": a["analysis_id"], "mode": mode,
                                                                     "selected_lit_emotion": lit, "confirmed_visual_items": its})
                run = {"variant": label, "mode": mode, "lit_emotion": lit, "http": st, "ms": round(ms, 2)}
                if st == 200:
                    http_ms["recommend"].append(ms)
                    rec = rr["recommendations"]
                    ctx = Context(taxonomy=TAX, mode=mode, corpus=corpus)
                    iss = validate_document("recommendations", rec, ctx) + validate_document("image_profile", rr["profile"], ctx)
                    issues_total += len(iss)
                    run.update({"status": rec["status"], "abstention": rec["abstention"] and rec["abstention"]["reason_code"],
                                "verses": [i["verse_id"] for i in rec["items"]], "tiers": [i["tier"] for i in rec["items"]],
                                "engine_ms": round(rr["timings_ms"]["retrieval"], 3), "contract_issues": len(iss),
                                "draft_disclosed": all("T_DRAFT_DISCLOSURE" in i["explanation"]["template_ids"] for i in rec["items"])})
                case["runs"].append(run)
        cases.append(case)
    # legitimate abstention case from the dev profiles: falcon x pride (no pride verse carries a falcon association)
    st, a, _ = post_image(args.base, os.path.join(args.images, images[0]))
    st, rr, _ = post_json(args.base, "/api/recommend", {"analysis_id": a["analysis_id"], "mode": "development",
                                                        "selected_lit_emotion": "lit_emotion.pride",
                                                        "confirmed_visual_items": [{"id": "tag.falcon", "user_selection": "focus"}]})
    abst = {"profile": "tag.falcon (focus) x lit_emotion.pride, development", "status": rr["recommendations"]["status"],
            "reason_code": (rr["recommendations"]["abstention"] or {}).get("reason_code")}

    def stats(xs):
        xs = sorted(xs)
        return {"n": len(xs), "median": round(statistics.median(xs), 2), "p95": round(xs[int(0.95 * (len(xs) - 1))], 2)} if xs else None

    report = {"date": args.date, "kind": "system_check_not_accuracy", "base_url": args.base,
              "model": {k: ready["model"].get(k) for k in ("model_id", "model_version", "device", "fingerprints")},
              "corpus": {k: ready["corpus"].get(k) for k in ("version", "sha256", "count", "displayable")},
              "images": len(images), "http_latency_ms": {k: stats(v) for k, v in http_ms.items()},
              "model_forward_ms": stats([c["model_timings_ms"]["forward"] for c in cases if "model_timings_ms" in c]),
              "contract_issues_total": issues_total, "abstention_case": abst, "cases": cases}
    out = os.path.join("evaluation", "e2e", f"e2e_report_{args.date}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: report[k] for k in ("images", "http_latency_ms", "model_forward_ms", "contract_issues_total",
                                             "abstention_case")}, ensure_ascii=False, indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()
