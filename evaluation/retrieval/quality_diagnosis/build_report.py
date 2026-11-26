"""Build REPORT.md (and add corpus statistics and weak examples to results.json) from a diagnose.py run.

    python3 -m evaluation.retrieval.quality_diagnosis.diagnose
    python3 -m evaluation.retrieval.quality_diagnosis.build_report

Every verse, span, justification and explanation sentence quoted in the report is copied programmatically from the
corpus record or from the engine output; nothing is retyped.
"""
import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict

from contracts.validate import display_allowed

from . import diagnose as D
from . import grid as G
from .report_template import TEMPLATE

HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(HERE, "results.json")
REPORT = os.path.join(HERE, "REPORT.md")
CTX = re.compile("البيت السابق|البيت التالي|الأبيات|في القصيدة|السياق|الضمير|كما في")
NAMES = {i: G.TAXONOMY.labels[i]["name_ar"] for i in G.TAXONOMY.labels}

# (key, mode, cell, verse_id, why) -- why is the diagnosis category; numbers are read from the run.
WEAK = [
    ("W1", "production", "tag.moon|lit_emotion.joy|default", "pv:verse:000028",
     "literal label whose evidence span is a pronoun phrase; the moon is only in the previous verse (needs outside context)"),
    ("W2", "production", "tag.bird|lit_emotion.loneliness|default", "pv:verse:000012",
     "scene_association that rests on the rest of the poem (the dove is never named in this verse)"),
    ("W3", "production", "scene_group.heritage|lit_emotion.awe|default", "pv:verse:000017",
     "scene_association through a pronoun that refers to a building named elsewhere in the poem"),
    ("W4", "production", "scene_group.desert|lit_emotion.loneliness|permissive", "pv:verse:000011",
     "emotion-only (tier 3) fill chosen by the verse_id tie-break; the same verse fills many unrelated cells"),
    ("W5", "production", "scene_group.sea|lit_emotion.awe|permissive", "pv:verse:000016",
     "emotion-only fill that literally depicts another scene (a mountain verse for a sea photo); 1.1.0 picks a "
     "scene-neutral verse instead, which avoids the contradiction but is still not a sea verse (none exists in production "
     "with this emotion)"),
    ("W6", "production", "tag.boat_ship|lit_emotion.longing|permissive", "pv:verse:000008",
     "T > 0 from a polysemous query term: فلك (ship) matches فلك (celestial orbit)"),
    ("W7", "production", "scene_group.mountains|lit_emotion.pride|permissive", "pv:verse:000035",
     "T > 0 from a polysemous query term: شعب (mountain pass) matches الشعب (the people)"),
    ("W8", "production", "scene_group.mountains|lit_emotion.sadness|permissive", "pv:verse:000001",
     "T > 0 from meaning_ar only: the proper name صخر (the poet's brother) matches the query term صخر (rock)"),
    ("W9", "production", "tag.sea|lit_emotion.loneliness|permissive", "pv:verse:000015",
     "label gap: the verse names the sea but is labelled scene_group.sea only, so a tag.sea photo gets it as an "
     "emotion-only fill"),
    ("W10", "production", "scene_group.heritage|lit_emotion.longing|permissive", "pv:verse:000010",
     "label gap: highest T of the grid (منازل is a heritage query term) but labelled only desert/scene_association"),
    ("W11", "development", "scene_group.desert|lit_emotion.pride|default", "pv:verse:000407",
     "incidental literal mention: the camels are a figure in a boast about poems, not a desert scene"),
    ("W12", "development", "scene_group.city|lit_emotion.sadness|default", "pv:verse:000192",
     "a place name labelled literal for a visual scene; T = 0 (no query term), tie broken by verse_id"),
    ("W13", "development", "tag.road|lit_emotion.longing|permissive", "pv:verse:000267",
     "no road verse exists; the tier-3 fill wins on T from سبيل used abstractly ('is there a way')"),
    ("W14", "development", "tag.falcon|lit_emotion.sadness|default", "pv:verse:000221",
     "the only falcon verse, admitted with the selected emotion as a secondary emotion (E = 0.6)"),
    ("W15", "production", "scene_group.greenery|lit_emotion.serenity|default", "pv:verse:000021",
     "duplicate poet: the one-per-poet rule is relaxed because fewer than k candidates exist"),
]

SIDE_BY_SIDE = [
    ("production", "scene_group.sea|lit_emotion.awe|permissive"),
    ("production", "scene_group.greenery|lit_emotion.joy|default"),
    ("development", "scene_group.desert|lit_emotion.pride|default"),
    ("development", "tag.sea|lit_emotion.loneliness|default"),
    ("development", "none|lit_emotion.serenity|default"),
]


def pct(x):
    return "—" if x is None else f"{100 * x:.1f}%"


def corpus_label_stats(corpus):
    """Label-quality diagnostics over the whole export (both modes)."""
    out = {}
    for mode in G.MODES:
        recs = [r for r in corpus if display_allowed(r, mode)]
        rel = Counter()
        lit = lit_term = 0
        assoc = assoc_span = 0
        ctx_assoc = 0
        no_visual = 0
        missing = defaultdict(Counter)
        for r in recs:
            vas = r.get("visual_associations") or []
            no_visual += not vas
            for a in vas:
                rel[a["relation"].split(".")[1]] += 1
                if a["relation"] == D.LAB.LITERAL:
                    lit += 1
                    if D.span_has_term(a["evidence_span"]["text"], a["target"]):
                        lit_term += 1
                    else:
                        for tok in D.PRE.tokenize(a["evidence_span"]["text"], "N1"):
                            missing[a["target"]][tok] += 1
                if a["relation"] == D.LAB.SCENE_ASSOCIATION:
                    assoc += 1
                    assoc_span += a.get("evidence_span") is not None
                if a.get("justification_ar") and CTX.search(a["justification_ar"]):
                    ctx_assoc += 1
        out[mode] = {
            "records": len(recs), "records_without_visual_association": no_visual,
            "relations": dict(rel), "literal": lit, "literal_span_contains_target_query_term": lit_term,
            "scene_association": assoc, "scene_association_with_span": assoc_span,
            "justifications_referring_to_outside_context": ctx_assoc,
            "meaning_referring_to_outside_context": sum(1 for r in recs if CTX.search(r.get("meaning_ar") or "")),
            "frequent_literal_span_tokens_not_in_query_terms": {
                t: [w for w, n in c.most_common(8) if n >= 2] for t, c in sorted(missing.items())},
        }
    return out


def n1_near_misses(engine):
    idx = engine.index("development", "N1")
    terms = set()
    for x in G.SCENE_GROUPS + G.EXPOSED_TAGS:
        for t in G.TAXONOMY.labels[x].get("query_terms_ar") or []:
            terms.update(D.PRE.tokenize(t, "N1"))
    vocab = Counter(t for d in idx.verse_tokens for t in d)
    exact = sum(vocab[t] for t in terms)
    prefix = suffix = 0
    examples = []
    for tok, c in vocab.items():
        if tok in terms:
            continue
        if any(tok.endswith(s) and tok[:-len(s)] in terms for s in ("ا", "ها", "ه", "هم", "هن", "ي", "نا", "ك", "كم", "ات")):
            suffix += c
            examples.append(tok)
        elif any(tok.startswith(p) and tok[len(p):] in terms for p in ("و", "ف", "ب", "ل", "ك")):
            prefix += c
            examples.append(tok)
    oov = {x: [t for t in sorted({tok for q in (G.TAXONOMY.labels[x].get("query_terms_ar") or [])
                                  for tok in D.PRE.tokenize(q, "N1")}) if t not in idx.verse_model("smoothed").df]
           for x in G.SCENE_GROUPS + G.EXPOSED_TAGS}
    return {"query_term_occurrences_exact": exact, "near_miss_with_proclitic": prefix,
            "near_miss_with_suffix": suffix, "examples": sorted(examples)[:30],
            "query_tokens_absent_from_development_vocabulary": oov}


def matched_tokens(engine, mode, profile, record):
    counts = D.ENG.query_counts(profile, "N1", G.TAXONOMY)
    verse = set(D.PRE.tokenize(record["text_original"], "N1"))
    meaning = set(D.PRE.tokenize(record.get("meaning_ar") or "", "N1"))
    return sorted(t for t in counts if t in verse), sorted(t for t in counts if t in meaning)


def run_cell(engine, mode, cell):
    items, emotion, setting = cell.split("|")
    item_ids = () if items == "none" else tuple(items.split("+"))
    profile = G.build_profile(item_ids, emotion, setting)
    query = G.build_query(profile, mode, D.CUR_ENG.expanded_query)
    return profile, engine.recommend(profile, query)


def weak_examples(results, corpus_map, current, baseline):
    out = []
    reuse = Counter()
    for k, v in results["per_cell"].items():
        if k.startswith("production|") and k.endswith("|permissive"):
            for it in v["v1_0_0"]["items"]:
                if it["tier"] == 3:
                    reuse[it["verse_id"]] += 1
    for key, mode, cell, vid, why in WEAK:
        row = results["per_cell"][f"{mode}|{cell}"]["v1_0_0"]
        diag = next(i for i in row["items"] if i["verse_id"] == vid)
        rec = corpus_map[vid]
        profile, doc = run_cell(baseline, mode, cell)
        item = next(i for i in doc["items"] if i["verse_id"] == vid)
        _, doc_new = run_cell(current, mode, cell)
        vtok, mtok = matched_tokens(baseline, mode, profile, rec)
        assoc = [a for a in rec.get("visual_associations") or [] if a["target"] == diag["target"]]
        out.append({
            "key": key, "mode": mode, "cell": cell, "verse_id": vid, "why": why,
            "text_original": rec["text_original"], "poet": rec["poet"]["name_apcd"],
            "tier": diag["tier"], "E": diag["E"], "V": diag["V"], "T": diag["T"], "final": diag["final"],
            "relation": diag["relation"], "target": diag["target"],
            "evidence_span": (assoc[0].get("evidence_span") or {}).get("text") if assoc else None,
            "justification_ar": assoc[0].get("justification_ar") if assoc else None,
            "record_visual_associations": [(a["target"], a["relation"].split(".")[1],
                                            (a.get("evidence_span") or {}).get("text"))
                                           for a in rec.get("visual_associations") or []],
            "meaning_ar": rec.get("meaning_ar"),
            "query_tokens_in_verse": vtok, "query_tokens_in_meaning": mtok,
            "explanation_sentences_ar": item["explanation"]["sentences_ar"],
            "list_v1_0_0": [i["verse_id"] for i in doc["items"]],
            "list_v1_1_0": [i["verse_id"] for i in doc_new["items"]],
            "tier3_reuse_in_production_permissive_cells": reuse.get(vid, 0),
        })
    return out


def options_table(results, mode, group):
    cols = ["abstention", "items/profile", "tier-3 share", "literal share", "literal span has query term",
            "verse has query term", "unevidenced assoc", "T>0", "tier-3 fill depicts other scene", "dup-poet lists"]
    lines = ["| option | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for opt in D.OPTIONS:
        s = results["summary"].get(f"{mode}|{opt}", {}).get(group)
        if not s:
            continue
        ts = s.get("tier_share") or {}
        lines.append("| " + " | ".join([
            f"`{opt}`", pct(s["abstention_rate"]), f"{s['mean_items_per_profile']:.2f}", pct(ts.get("3")),
            pct(s.get("literal_share")), pct(s.get("literal_term_in_span_share")),
            pct(s.get("verse_has_query_term_share")), pct(s.get("unevidenced_assoc_share")), pct(s.get("T_gt0_rate")),
            pct(s.get("tier3_with_scene_conflict_share")), str(s.get("profiles_with_duplicate_poet", 0))]) + " |")
    return "\n".join(lines)


def coverage_table(results, mode, setting):
    mat = results["coverage_matrix"][f"{mode}|{setting}"]
    em = G.LIT_EMOTIONS
    lines = ["| target | " + " | ".join(e.split(".")[1] for e in em) + " |", "|---" * (len(em) + 1) + "|"]
    for x, row in mat.items():
        cells = []
        for e in em:
            v = row[e]
            cells.append("—" if v.startswith("A:") else v.split(":")[1])
        lines.append(f"| `{x}` | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def eligible_table(results, mode):
    em = G.LIT_EMOTIONS
    lines = ["| target | " + " | ".join(e.split(".")[1] for e in em) + " |", "|---" * (len(em) + 1) + "|"]
    for x, row in results["tier1_eligible_counts"][mode].items():
        lines.append(f"| `{x}` | " + " | ".join(
            f"{row[e]['primary_literal']}/{row[e]['primary_assoc']}/{row[e]['secondary']}" for e in em) + " |")
    return "\n".join(lines)


def side_by_side(results, corpus_map):
    out = []
    for mode, cell in SIDE_BY_SIDE:
        v = results["per_cell"][f"{mode}|{cell}"]
        out.append(f"**{mode} · `{cell}`**\n")
        out.append("| option | rank | verse | tier | E | V | T | final | relation | text |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for opt in ("v1_0_0", "engine_1_1_0", "drop_T", "meaning_weight_0", "assoc_needs_evidence",
                    "implied_relations"):
            row = v.get(opt)
            if row is None:
                continue
            if not row["items"]:
                out.append(f"| `{opt}` | — | abstained: {row['reason']} | | | | | | | |")
            for n, it in enumerate(row["items"], 1):
                text = corpus_map[it["verse_id"]]["text_original"]
                out.append(f"| `{opt}` | {n} | {it['verse_id'][-6:]} | {it['tier']} | {it['E']} | "
                           f"{'—' if it['V'] is None else round(it['V'], 2)} | "
                           f"{'—' if it['T'] is None else round(it['T'], 3)} | {it['final']} | {it['relation']} | "
                           f"{text} |")
        out.append("")
    return "\n".join(out)


def weak_section(examples):
    out = []
    for w in examples:
        out.append(f"#### {w['key']} — {w['mode']} · `{w['cell']}` · {w['verse_id']}\n")
        out.append(f"- **Why weak:** {w['why']}.")
        out.append(f"- **Verse** ({w['poet']}): «{w['text_original']}»")
        out.append(f"- **Scores (v1.0.0):** tier {w['tier']}, E {w['E']}, V {w['V']}, "
                   f"T {'null' if w['T'] is None else round(w['T'], 4)}, final {w['final']}; relation "
                   f"`{w['relation']}`" + (f" to `{w['target']}`" if w["target"] else "") + ".")
        if w["evidence_span"] or w["justification_ar"]:
            span = f"«{w['evidence_span']}»" if w["evidence_span"] else "none"
            just = f"«{w['justification_ar']}»" if w["justification_ar"] else "none"
            out.append(f"- **Label:** span {span} · justification {just}")
        out.append(f"- **All visual labels of the record:** {w['record_visual_associations']}")
        out.append(f"- **Query tokens found:** verse {w['query_tokens_in_verse']} · meaning "
                   f"{w['query_tokens_in_meaning']}")
        if w["meaning_ar"]:
            out.append(f"- **meaning_ar:** «{w['meaning_ar']}»")
        out.append(f"- **Explanation shown to the user:** " + " / ".join(f"«{s}»" for s in w["explanation_sentences_ar"]))
        out.append(f"- **List v1.0.0:** {w['list_v1_0_0']} → **1.1.0:** {w['list_v1_1_0']}"
                   + (f" · this verse is the tier-3 fill in {w['tier3_reuse_in_production_permissive_cells']} "
                      f"production permissive cells" if w["tier"] == 3 and w["mode"] == "production" else ""))
        out.append("")
    return "\n".join(out)


def extra_blocks(results):
    n1 = results["n1_query_term_matching"]
    v = results["contract_validation"]
    ch = results["changes_1_0_0_to_1_1_0"]
    kinds = Counter(c["cell"].split("|")[0] + (" no-item" if c["cell"].split("|")[1] == "none" else
                                                " " + c["cell"].split("|")[-1]) for c in ch["cells"])
    rows = []
    for label, mode, group in (("production, permissive, single items", "production", "permissive/single"),
                               ("production, permissive, combinations", "production", "permissive/combo"),
                               ("production, no-item profiles", "production", "default/none"),
                               ("development, permissive, single items", "development", "permissive/single"),
                               ("development, no-item profiles", "development", "default/none")):
        a = results["summary"][f"{mode}|v1_0_0"][group].get("tier3_with_scene_conflict_share")
        b = results["summary"][f"{mode}|engine_1_1_0"][group].get("tier3_with_scene_conflict_share")
        rows.append(f"| {label} | {pct(a)} | {pct(b)} |")
    tdist = ["| T over | mode | n | =0 | (0,0.05) | [0.05,0.1) | [0.1,0.2) | [0.2,0.3) | [0.3,0.5) | median | p90 |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, key in (("all E-eligible candidates", "T_distribution_all_candidates"),
                      ("tier-1 candidates", "T_distribution_tier1_candidates")):
        for mode, d in results[key].items():
            tdist.append(f"| {name} | {mode} | {d['n']} | {d['=0']} | {d['(0,0.05)']} | {d['[0.05,0.1)']} | "
                         f"{d['[0.1,0.2)']} | {d['[0.2,0.3)']} | {d['[0.3,0.5)']} | {d['median']} | {d['p90']} |")
    return {
        "VALIDATION": "; ".join(f"engine {k}: {x['documents']} documents, {x['issues']} issues" for k, x in v.items()),
        "N1_COUNTS": f"{n1['query_term_occurrences_exact']} exact matches; {n1['near_miss_with_proclitic']} "
                     f"occurrences with a proclitic and {n1['near_miss_with_suffix']} with a suffix are missed",
        "N1_EXAMPLES": "، ".join(n1["examples"][:20]),
        "OOV": "; ".join(f"`{t}`: {'، '.join(v)}" for t, v in n1["query_tokens_absent_from_development_vocabulary"].items() if v),
        "T_DIST": "\n   ".join(tdist),
        "CHANGES": f"{ch['cells_changed']} of 2 × {results['grid_cells_per_mode']} cells change ("
                   + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())) + "). "
                   + ("**In every changed cell the tier-1 and tier-2 items are identical; only the tier-3 fill "
                      "differs.**" if ch["all_tier_1_2_unchanged"] else "WARNING: tier-1/2 items changed."),
        "CONFLICT_ROWS": "\n".join(rows),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=REPORT, help="report path, or '-' for stdout")
    args = ap.parse_args(argv)
    with open(RESULTS, encoding="utf-8") as f:
        results = json.load(f)
    baseline = D.ENG.RetrievalEngine.from_jsonl(G.CORPUS_PATH)
    current = D.CUR_ENG.RetrievalEngine(baseline.corpus)
    corpus_map = {r["verse_id"]: r for r in baseline.corpus}
    results["corpus_label_stats"] = corpus_label_stats(baseline.corpus)
    results["n1_query_term_matching"] = n1_near_misses(baseline)
    results["weak_examples"] = weak_examples(results, corpus_map, current, baseline)
    with open(RESULTS, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)

    text = TEMPLATE
    blocks = {**extra_blocks(results),
        "WEAK_EXAMPLES": weak_section(results["weak_examples"]),
        "SIDE_BY_SIDE": side_by_side(results, corpus_map),
        "COVERAGE_PROD_DEFAULT": coverage_table(results, "production", "default"),
        "COVERAGE_PROD_PERMISSIVE": coverage_table(results, "production", "permissive"),
        "COVERAGE_DEV_DEFAULT": coverage_table(results, "development", "default"),
        "ELIGIBLE_PROD": eligible_table(results, "production"),
        "ELIGIBLE_DEV": eligible_table(results, "development"),
    }
    for mode in G.MODES:
        for group in ("default/single", "default/combo", "permissive/single", "permissive/combo", "default/none"):
            blocks[f"OPTIONS:{mode}:{group}"] = options_table(results, mode, group)
    for key, block in blocks.items():
        text = text.replace("{{" + key + "}}", block)
    left = re.findall(r"\{\{[^}]+\}\}", text)
    if left:
        raise SystemExit(f"unfilled placeholders: {left}")
    if args.out == "-":
        sys.stdout.write(text)
        return
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"wrote {args.out} and updated {RESULTS}")


if __name__ == "__main__":
    main()
