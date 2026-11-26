"""Reports in datasets/reports/ (task prompt section 15). Every number comes from the delivered files."""
import json
import os
import statistics
from collections import Counter, defaultdict

from .common import md_table, sha256_file, write_csv, write_json, write_jsonl, write_text

REPORTS = os.path.join("datasets", "reports")
MANIFESTS = os.path.join("datasets", "manifests")
INVENTORY_FIELDS = ["image_id", "source_dataset", "split", "label", "member", "bytes", "sha256", "decodes", "format",
                    "extension", "extension_matches_format", "mode", "width", "height", "mean_luminance",
                    "std_luminance", "phash", "error"]


def _stats(vals):
    vals = sorted(vals)
    return {"min": vals[0], "median": statistics.median(vals), "max": vals[-1]} if vals else {}


def inventory(state, root):
    inv = state["inventory"]
    by_source = defaultdict(list)
    for r in inv:
        by_source[r["source_dataset"]].append(r)
    summary = {"version": state["version"], "input_archives": state["inputs"], "sources": {}}
    md = [f"# Dataset inventory ({state['version']})", "",
          "Every number below was measured on the delivered files (bytes as delivered, never re-encoded).", "",
          "## Input archives", "",
          md_table(["role", "file", "SHA-256", "bytes"],
                   [(i["role"], i["path"], f"`{i['sha256']}`", i["bytes"]) for i in state["inputs"]]), ""]
    for src in sorted(by_source):
        rows = by_source[src]
        ok = [r for r in rows if r["decodes"]]
        s = {
            "files": len(rows),
            "decoded": len(ok), "undecodable": len(rows) - len(ok),
            "per_split": dict(sorted(Counter(r["split"] for r in rows).items())),
            "per_split_and_class": {f"{sp}|{lab}": n for (sp, lab), n in
                                    sorted(Counter((r["split"], r["label"]) for r in rows).items())},
            "width": _stats([r["width"] for r in ok]), "height": _stats([r["height"] for r in ok]),
            "smaller_than_64px": sum(min(r["width"], r["height"]) < 64 for r in ok),
            "modes": dict(sorted(Counter(r["mode"] for r in ok).items())),
            "formats": dict(sorted(Counter(r["format"] for r in ok).items())),
            "extension_format_mismatch": sum(not r["extension_matches_format"] for r in ok),
            "bytes": _stats([r["bytes"] for r in rows]),
        }
        summary["sources"][src] = s
        splits = sorted(s["per_split"], key=lambda x: ["train", "val", "test", "ood_test"].index(x))
        labels = sorted({r["label"] for r in rows})
        table = [[lab] + [s["per_split_and_class"].get(f"{sp}|{lab}", 0) for sp in splits] +
                 [sum(s["per_split_and_class"].get(f"{sp}|{lab}", 0) for sp in splits)] for lab in labels]
        table.append(["**total**"] + [s["per_split"][sp] for sp in splits] + [len(rows)])
        md += [f"## {src}", "",
               f"- files: {s['files']}; decoded: {s['decoded']}; undecodable: {s['undecodable']}",
               f"- width min/median/max: {s['width'].get('min')}/{s['width'].get('median')}/{s['width'].get('max')}; "
               f"height: {s['height'].get('min')}/{s['height'].get('median')}/{s['height'].get('max')}",
               f"- smaller than 64 px: {s['smaller_than_64px']}",
               f"- colour modes: {s['modes']}; formats: {s['formats']}; "
               f"extension/format mismatches: {s['extension_format_mismatch']}",
               f"- file size (bytes) min/median/max: {s['bytes'].get('min')}/{s['bytes'].get('median')}/"
               f"{s['bytes'].get('max')}", "",
               "Files per split and class:", "", md_table(["class"] + splits + ["total"], table), ""]
    flagged = state["flagged"]
    md += ["## Cleaning", "",
           f"- excluded (undecodable or < 64 px): {len(state['excluded'])} — listed in `excluded_images.jsonl`",
           f"- flagged for a visual check (near-black mean luminance < 0.08, near-white > 0.95, or near-uniform "
           f"std < 0.02; provisional thresholds; kept unless broken): {len(flagged)} — listed in "
           f"`flagged_for_visual_check.csv`",
           f"  - by flag: {dict(sorted(Counter(f['flags'] for f in flagged).items()))}",
           "- per-image record (SHA-256, size, mode, luminance): `image_inventory.csv`", ""]
    summary["excluded"] = len(state["excluded"])
    summary["flagged_for_visual_check"] = len(flagged)
    write_json(os.path.join(root, REPORTS, "dataset_inventory.json"), summary)
    write_text(os.path.join(root, REPORTS, "dataset_inventory.md"), "\n".join(md))
    write_csv(os.path.join(root, REPORTS, "image_inventory.csv"),
              sorted(inv, key=lambda r: r["image_id"]), INVENTORY_FIELDS)
    write_jsonl(os.path.join(root, REPORTS, "excluded_images.jsonl"),
                sorted(state["excluded"], key=lambda r: r["image_id"]))
    write_csv(os.path.join(root, REPORTS, "flagged_for_visual_check.csv"),
              sorted(flagged, key=lambda r: r["image_id"]),
              ["image_id", "split", "image_path", "flags", "mean_luminance", "std_luminance", "visual_check"])


def duplicates(state, root):
    q = state["quarantine"]
    write_jsonl(os.path.join(root, REPORTS, "quarantine.jsonl"), q)
    md = [f"# Duplicate detection ({state['version']})", "",
          "## Exact duplicates (SHA-256 of the file bytes, method 6.1)", "",
          f"- images hashed: {len(state['inventory'])}",
          f"- groups of identical files: {len(state['exact_groups'])}",
          f"- quarantined: {len(q)} — by reason: {dict(sorted(Counter(x['reason'] for x in q).items()))}", ""]
    if state["exact_groups"]:
        md += [md_table(["SHA-256", "members (image_id, split)"],
                        [(f"`{g['image_sha256'][:16]}…`", "; ".join(f"{i} ({s})" for i, s in g["members"]))
                         for g in state["exact_groups"]]), ""]
    near = state.get("near")
    md += ["## Near duplicates (pHash ≤ 6 or CLIP cosine ≥ 0.95, method 6.2)", ""]
    if near is None:
        md += ["Not run in v0.9 (method 3.1): it comes with `manifest_v1`. `near_dup_group` is null for every "
               "v0.9 record.", ""]
    else:
        md += near["markdown"]
    write_text(os.path.join(root, REPORTS, "duplicate_detection.md"), "\n".join(md))


def validation(root, run_validator):
    mdir = os.path.join(root, MANIFESTS)
    rows, detail = [], []
    for name in sorted(os.listdir(mdir)) if os.path.isdir(mdir) else []:
        if not name.endswith(".jsonl"):
            continue
        rel_path = f"datasets/manifests/{name}"
        code, lines = run_validator(rel_path, root)
        build_path = os.path.join(mdir, name[:-len(".jsonl")] + ".build.json")
        build = json.load(open(build_path, encoding="utf-8")) if os.path.exists(build_path) else {}
        with open(os.path.join(mdir, name), encoding="utf-8") as fh:
            recs = [json.loads(x) for x in fh if x.strip()]
        per = Counter((r["source_dataset"], r["split"]) for r in recs)
        rows.append((f"`{name}`", code, len(lines), len(recs),
                     f"`{sha256_file(os.path.join(mdir, name))}`",
                     f"`{sha256_file(build_path)}`" if build else "—"))
        detail += [f"### {name}", "", "```", f"python -m contracts.validate image_manifest {rel_path}", "```", "",
                   f"- exit code: {code}; issues: {len(lines)} (must be 0); records: {len(recs)}",
                   f"- per source and split: " + ", ".join(f"{s}/{sp}: {n}" for (s, sp), n in sorted(per.items())),
                   f"- build command: `{build.get('command', '—')}`", ""]
        detail += [f"  - {ln}" for ln in lines[:50]]
    md = ["# Dataset validation", "",
          "Every manifest validated with the shared validator in production mode (the default).", "",
          md_table(["manifest", "exit code", "issues", "records", "SHA-256 (manifest)", "SHA-256 (.build.json)"],
                   rows), "", *detail]
    write_text(os.path.join(root, REPORTS, "dataset_validation.md"), "\n".join(md))


def write_all(state, root, run_validator):
    inventory(state, root)
    duplicates(state, root)
    if state["version"] == "v1":
        from .reports_v1 import write_v1_reports
        write_v1_reports(state, root)
    validation(root, run_validator)
