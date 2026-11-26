"""Side-by-side before/after report from two benchmark runs (same images, same queries).

    python3 -m evaluation.quality.compare --before before --after after

Writes evaluation/quality/COMPARISON_<before>_vs_<after>.md. Counts only observable behaviour (status, tiers,
relations, model probabilities). It does not score relevance: no human judgments exist.
"""
import argparse
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def load(label):
    with open(os.path.join(HERE, "runs", f"{label}.json"), encoding="utf-8") as fh:
        return json.load(fh)


def short(i):
    return i.split(".", 1)[-1]


def summary(run):
    c = Counter()
    for case in run["cases"]:
        c["images"] += 1
        top = case.get("emotion_top") or [["", 0]]
        c["awe_top1"] += top[0][0] == "img_emotion.awe"
        c["top1_ge_0.95"] += top[0][1] >= 0.95
        c["emotion_ambiguous"] += case.get("emotion_status") == "ambiguous"
        c["auto_suggested_lit"] += bool(case.get("suggested_lit"))
        for r in case.get("runs", []):
            c[f"{r['mode']}:{r.get('status')}"] += 1
            for it in r.get("items", []):
                c[f"{r['mode']}:items"] += 1
                c[f"{r['mode']}:tier{it['tier']}"] += 1
                c[f"{r['mode']}:literal"] += "relation.literal" in it["relations"]
                c[f"{r['mode']}:T>0"] += (it["scores"].get("text") or 0) > 0
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--before", default="before")
    ap.add_argument("--after", default="after")
    args = ap.parse_args()
    b, a = load(args.before), load(args.after)
    sb, sa = summary(b), summary(a)
    keys = sorted(set(sb) | set(sa))
    out = [f"# Quality benchmark: {args.before} vs {args.after}", "",
           f"- Before: model {b['model'].get('model_version')}, engine {b.get('engine_version')}, corpus {b['corpus'].get('version')} ({b['created']})",
           f"- After: model {a['model'].get('model_version')}, engine {a.get('engine_version')}, corpus {a['corpus'].get('version')} ({a['created']})",
           "- Same 16 real Places365 test photos (`benchmark_set.json`), same queries: app-suggested visual items x 5 pilot literary emotions x 2 modes.",
           "- Behaviour counts only. No human relevance judgments exist; nothing here is an accuracy or quality score.", "",
           "| Count | Before | After |", "|---|---|---|"]
    out += [f"| {k} | {sb.get(k, 0)} | {sa.get(k, 0)} |" for k in keys]
    out.append("")
    for cb, ca in zip(b["cases"], a["cases"]):
        assert cb["image_id"] == ca["image_id"]
        out += [f"## {cb['type']} · {cb['image_id']} ({cb['places_category']})", "",
                f"- Scene: before {short(cb['scene_top'][0][0])} {cb['scene_top'][0][1]:.2f} ({cb['scene_status']}); "
                f"after {short(ca['scene_top'][0][0])} {ca['scene_top'][0][1]:.2f} ({ca['scene_status']})",
                f"- Image emotion top-3: before {', '.join(f'{short(x)} {p:.3f}' for x, p in cb['emotion_top'])} ({cb['emotion_status']}); "
                f"after {', '.join(f'{short(x)} {p:.3f}' for x, p in ca['emotion_top'])} ({ca['emotion_status']})",
                f"- Suggested literary emotion: before {[short(x) for x in cb['suggested_lit']]}; after {[short(x) for x in ca['suggested_lit']]}",
                f"- Confirmed visual items (app suggestion): before {cb['suggested_items']}; after {ca['suggested_items']}", ""]
        for rb, ra in zip(cb["runs"], ca["runs"]):
            if rb["lit"] != ra["lit"] or rb["mode"] != ra["mode"]:
                continue
            out.append(f"**{short(rb['lit'])} · {rb['mode']}** — before `{rb.get('status')}`{' ' + rb['abstention'] if rb.get('abstention') else ''}, "
                       f"after `{ra.get('status')}`{' ' + ra['abstention'] if ra.get('abstention') else ''}")
            for tag, r in (("before", rb), ("after", ra)):
                for it in r.get("items", []):
                    s = it["scores"]
                    rel = ",".join(short(x) for x in it["relations"]) or "emotion-only"
                    out.append(f"- {tag} · tier {it['tier']} · E {s['emotion']:.2f} V {s['visual'] if s['visual'] is None else round(s['visual'], 2)} "
                               f"T {s['text'] if s['text'] is None else round(s['text'], 3)} → {s['final']:.3f} · {rel} · {it['poet']}: {it['text']}")
            out.append("")
    path = os.path.join(HERE, f"COMPARISON_{args.before}_vs_{args.after}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
