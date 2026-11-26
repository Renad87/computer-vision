"""Retrieval quality diagnosis: real runs of the engine over a profile grid, per-item diagnostics, candidate
fix options compared on the same grid, and weak-example extraction (stdlib only).

    python3 -m evaluation.retrieval.quality_diagnosis.diagnose            # writes results.json next to this file

No human relevance judgment exists, so no precision / nDCG is computed. Every number is a transparent proxy:
share of items with a literal relation to a confirmed target, share whose literal evidence span contains one
of the target's taxonomy query terms, share of tier-3 fills, T > 0 rate, abstention rate, duplicate poets.

Options are applied on top of the v1.0.0 candidate generation (retrieval.engine._candidates) so that every
option is compared with the same profiles, corpus and code path. Options never touch the corpus or contracts.
"""
import argparse
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

from contracts.validate import Context, validate_document

from . import grid as G

HERE = os.path.dirname(os.path.abspath(__file__))


def load_engine_package(name):
    """Import `retrieval` (current) or the frozen v1.0.0 copy in backups/retrieval_v1_0_0 as a package."""
    if name == "retrieval":
        import retrieval.engine as eng
        import retrieval.labels as lab
        import retrieval.rank as rank
        import retrieval.preprocess as pre
        return eng, lab, rank, pre
    import importlib
    path = os.path.join(G.REPO, "backups")
    if path not in sys.path:
        sys.path.insert(0, path)
    eng = importlib.import_module(f"{name}.engine")
    return eng, importlib.import_module(f"{name}.labels"), importlib.import_module(f"{name}.rank"), \
        importlib.import_module(f"{name}.preprocess")


# Every option is applied on top of the frozen v1.0.0 engine; "engine_1_1_0" runs the current retrieval package.
ENG, LAB, RANK, PRE = load_engine_package("retrieval_v1_0_0")
CUR_ENG = load_engine_package("retrieval")[0]

# ------------------------------------------------------------------------------------------- term helpers
_TERMS = {lid: [PRE.normalize(t) for t in (lab.get("query_terms_ar") or [])] for lid, lab in G.TAXONOMY.labels.items()}
_TERM_TOKENS = {lid: {tok for t in (lab.get("query_terms_ar") or []) for tok in PRE.tokenize(t, "N1")}
                for lid, lab in G.TAXONOMY.labels.items()}


def span_has_term(text, target):
    """Does a (normalized) text contain one of the target's query terms as a substring? (clitic-tolerant)"""
    norm = PRE.normalize(text or "")
    return any(t and t in norm for t in _TERMS.get(target) or [])


def anchor_relation(record, item_ids):
    """Strongest relation of the record with any confirmed item: literal > scene_association > symbolic."""
    order = {LAB.LITERAL: 0, LAB.SCENE_ASSOCIATION: 1, LAB.SYMBOLIC: 2}
    best = None
    for a in record.get("visual_associations") or []:
        if a.get("target") in item_ids and a.get("relation") in order:
            if best is None or order[a["relation"]] < order[best["relation"]]:
                best = a
    return best


def item_diag(record, tier, scores, item_ids):
    a = anchor_relation(record, item_ids)
    rel = a["relation"].split(".")[1] if a else "none"
    span = (a or {}).get("evidence_span")
    literal_term = bool(a and rel == "literal" and span and span_has_term(span["text"], a["target"]))
    verse_term = any(span_has_term(record["text_original"], x) for x in item_ids)
    meaning_term = any(span_has_term(record.get("meaning_ar") or "", x) for x in item_ids)
    return {
        "verse_id": record["verse_id"], "poet": record["poet"]["name_apcd"], "tier": tier,
        "E": scores["emotion"], "V": scores["visual"], "T": scores["text"], "final": round(scores["final"], 4),
        "relation": rel, "target": (a or {}).get("target"), "has_span": span is not None,
        "literal_term_in_span": literal_term, "verse_has_query_term": verse_term,
        "meaning_has_query_term": meaning_term,
        "justification_ar": (a or {}).get("justification_ar"),
        "scene_conflict": scene_conflict(record, item_ids),
    }


# ---------------------------------------------------------------------------------------------- options
OPTIONS = {
    "v1_0_0": "baseline engine 1.0.0 (backups/retrieval_v1_0_0), production defaults",
    "engine_1_1_0": "current retrieval package (1.1.0): v1.0.0 plus the tier-3 scene-neutral tie-break",
    "drop_T": "T removed (method labels_weighted: E and V only, weights renormalized) -- shows what T changes",
    "assoc_needs_evidence": "tier 1 requires a literal relation or a scene_association WITH an evidence span; an "
                            "unevidenced scene_association drops to tier 2 (shown only when symbolic is allowed) "
                            "or tier 3 (emotion-only)",
    "assoc_rho_0_5": "rho(scene_association) 0.7 -> 0.5 (weight change; recommendation only)",
    "meaning_weight_0": "T = cos(q, verse) only (meaning weight 0.3 -> 0)",
    "meaning_weight_0_5": "T = 0.5 cos(q, verse) + 0.5 cos(q, meaning)",
    "tier3_needs_text": "the single tier-3 (emotion-only) fill requires T > 0 (the verse or its meaning names a "
                        "query term of a confirmed item)",
    "min_score_0_5": "min_score theta = 0.5 (all tiers)",
    "preprocess_N2": "preprocessing variant N2 instead of N1",
    "assoc_needs_evidence+tier3_needs_text": "both gates together",
    "tier3_scene_neutral": "tie-break inside tier 3 only: among equal final scores prefer a verse that does not "
                           "literally depict a scene group the user did not confirm (before the verse_id tie-break)",
    "implied_relations": "CORPUS-SIDE SIMULATION (in memory, corpus file untouched): add a literal relation to a "
                         "visual target when one of the record's own literal evidence spans contains that target's "
                         "query term (e.g. a span 'البحر' labelled only scene_group.sea also implies tag.sea)",
}

# Options whose per-cell lists are stored in results.json for side-by-side reading.
STORED_OPTIONS = ("v1_0_0", "engine_1_1_0", "drop_T", "assoc_needs_evidence", "meaning_weight_0", "tier3_needs_text", "tier3_scene_neutral",
                  "implied_relations")
VISUAL_TARGETS = None  # filled in main()


def implied_corpus(corpus):
    """Copy of the corpus with span-implied literal relations added (see OPTIONS['implied_relations'])."""
    out, added = [], Counter()
    for r in corpus:
        r2 = json.loads(json.dumps(r))
        have = {a["target"] for a in r2.get("visual_associations") or []}
        for a in list(r2.get("visual_associations") or []):
            span = a.get("evidence_span")
            if a.get("relation") != LAB.LITERAL or not span:
                continue
            for x in VISUAL_TARGETS:
                if x not in have and span_has_term(span["text"], x):
                    r2["visual_associations"].append({"target": x, "relation": LAB.LITERAL, "evidence_span": span,
                                                      "justification_ar": None})
                    have.add(x)
                    added[x] += 1
        out.append(r2)
    return out, added


def scene_conflict(record, item_ids):
    return any(a.get("relation") == LAB.LITERAL and a.get("target", "").startswith("scene_group.")
               and a["target"] not in item_ids for a in record.get("visual_associations") or [])


def _rescore(c, weights):
    c["scores"]["final"] = RANK.final_score(c["scores"], weights)


def run(profile, query, index, option, index_n2=None):
    """Return (doc, chosen candidate list, all candidates) for one option."""
    q = json.loads(json.dumps(query))
    idx = index
    if option == "min_score_0_5":
        q["min_score"] = 0.5
    if option == "drop_T":
        q["method"] = "labels_weighted"
    if option == "preprocess_N2":
        q["preprocessing_variant"] = "N2"
        idx = index_n2
    cands, stats, anchor_ids = ENG._candidates(profile, q, idx, G.TAXONOMY)
    weights = q["weights"]
    symbolic = bool(profile.get("symbolic_allowed"))
    tiers_enabled = set(q["tiers_enabled"])
    items = profile["confirmed_visual_items"]
    item_ids = [x["id"] for x in items]

    if option in ("meaning_weight_0", "meaning_weight_0_5"):
        mw = 0.0 if option == "meaning_weight_0" else 0.5
        counts = ENG.query_counts(profile, idx.variant, G.TAXONOMY)
        qv, qm = idx.query_vectors(counts, "smoothed") if counts else ({}, {})
        for c in cands:
            i = idx._pos[c["record"]["verse_id"]]
            cv = ENG.clamp01(ENG.cosine(qv, idx.verse_model("smoothed").doc_vectors[i]))
            if i in idx.meaning_pos and mw > 0:
                cm = ENG.clamp01(ENG.cosine(qm, idx.meaning_model("smoothed").doc_vectors[idx.meaning_pos[i]]))
                c["scores"]["text"] = ENG.clamp01((1 - mw) * cv + mw * cm)
            else:
                c["scores"]["text"] = cv
            _rescore(c, weights)

    if option == "assoc_rho_0_5":
        rw = dict(G.TAXONOMY.relation_weights)
        rw[LAB.SCENE_ASSOCIATION] = 0.5
        for c in cands:
            rm = idx.rel_maps[idx._pos[c["record"]["verse_id"]]]
            c["scores"]["visual"] = LAB.visual_score(rm, items, symbolic, rw)
            _rescore(c, weights)

    if option.startswith("assoc_needs_evidence"):
        kept = []
        for c in cands:
            rm = idx.rel_maps[idx._pos[c["record"]["verse_id"]]]
            if c["tier"] == 1:
                strong = any((rm.get(a) or {}).get("relation") == LAB.LITERAL or
                             ((rm.get(a) or {}).get("relation") == LAB.SCENE_ASSOCIATION and
                              (rm.get(a) or {}).get("evidence_span")) for a in anchor_ids)
                if not strong:
                    new = 2 if symbolic else 3
                    if new not in tiers_enabled or (new == 3 and not profile.get("emotion_only_allowed")):
                        continue
                    c["tier"] = c["natural_tier"] = new
            kept.append(c)
        cands = kept

    if option.endswith("tier3_needs_text"):
        cands = [c for c in cands if c["tier"] != 3 or (c["scores"]["text"] or 0) > 0]

    if option == "tier3_scene_neutral":
        def key(c):
            k = RANK.sort_key(c)
            conflict = 1 if c["tier"] == 3 and scene_conflict(c["record"], item_ids) else 0
            return k[:2] + (conflict,) + k[2:]
        cands.sort(key=key)
        chosen = RANK.select(cands, q["k"], q["diversity"], idx.near_dup, max_tier3=1,
                             min_score=float(q.get("min_score", 0.0)))
        chosen.sort(key=key)
    else:
        cands.sort(key=RANK.sort_key)
        chosen = None
    if not cands:  # keep the engine's abstention reasons coherent with the filtered pool
        stats = dict(stats, candidates=0)
    if chosen is None:
        chosen = RANK.select(cands, q["k"], q["diversity"], idx.near_dup, max_tier3=1,
                             min_score=float(q.get("min_score", 0.0)))
    items_out = [ENG._item(n, c, profile, q["corpus_mode"], G.TAXONOMY) for n, c in enumerate(chosen, 1)]
    status = RANK.status_for(len(items_out), q["k"])
    reason = None
    if not items_out:
        reason = RANK.abstention_reason(stats)
    return {"status": status, "items": items_out, "reason": reason}, chosen, cands


# ----------------------------------------------------------------------------------------------- metrics
def summarize(rows):
    """rows: list of per-profile dicts {status, reason, items: [item_diag]}."""
    n = len(rows)
    items = [it for r in rows for it in r["items"]]
    m = len(items)
    st = Counter(r["status"] for r in rows)
    out = {
        "profiles": n,
        "status": dict(st),
        "abstention_rate": round(st.get("abstained", 0) / n, 4) if n else None,
        "abstention_reasons": dict(Counter(r["reason"] for r in rows if r["reason"])),
        "items": m,
        "mean_items_per_profile": round(m / n, 3) if n else None,
    }
    if m:
        out.update({
            "tier_share": {str(t): round(sum(it["tier"] == t for it in items) / m, 4) for t in (1, 2, 3)},
            "relation_share": {k: round(v / m, 4) for k, v in sorted(Counter(it["relation"] for it in items).items())},
            "literal_share": round(sum(it["relation"] == "literal" for it in items) / m, 4),
            "literal_term_in_span_share": round(sum(it["literal_term_in_span"] for it in items) / m, 4),
            "verse_has_query_term_share": round(sum(it["verse_has_query_term"] for it in items) / m, 4),
            "unevidenced_assoc_share": round(sum(it["relation"] == "scene_association" and not it["has_span"]
                                                 for it in items) / m, 4),
            "T_gt0_rate": round(sum((it["T"] or 0) > 0 for it in items) / m, 4),
            "T_mean": round(statistics.mean(it["T"] or 0 for it in items), 4),
            "final_mean": round(statistics.mean(it["final"] for it in items), 4),
            "tier3_with_scene_conflict_share": round(
                sum(it["tier"] == 3 and it["scene_conflict"] for it in items) / max(1, sum(it["tier"] == 3 for it in items)), 4),
            "distinct_verses": len({it["verse_id"] for it in items}),
            "max_reuse_of_one_verse": max(Counter(it["verse_id"] for it in items).values()),
            "tier3_distinct_verses": len({it["verse_id"] for it in items if it["tier"] == 3}),
            "profiles_with_duplicate_poet": sum(
                1 for r in rows if len({it["poet"] for it in r["items"]}) < len(r["items"])),
        })
    return out


def distribution(values, bins=(0.0, 1e-12, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0000001)):
    """Histogram of values in [0,1]: first bin is exactly 0."""
    values = [v for v in values if v is not None]
    out = {}
    labels = ["=0", "(0,0.05)", "[0.05,0.1)", "[0.1,0.2)", "[0.2,0.3)", "[0.3,0.5)", "[0.5,1]"]
    for i, lab in enumerate(labels):
        lo, hi = bins[i], bins[i + 1]
        out[lab] = sum(1 for v in values if (v == 0 if i == 0 else lo <= v < hi))
    if values:
        qs = statistics.quantiles(values, n=10) if len(values) > 1 else [values[0]] * 9
        out["n"] = len(values)
        out["mean"] = round(statistics.mean(values), 4)
        out["median"] = round(statistics.median(values), 4)
        out["p90"] = round(qs[8], 4)
    return out


# ------------------------------------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(HERE, "results.json"))
    args = ap.parse_args(argv)

    global VISUAL_TARGETS
    VISUAL_TARGETS = G.SCENE_GROUPS + G.EXPOSED_TAGS
    engine = ENG.RetrievalEngine.from_jsonl(G.CORPUS_PATH)
    current = CUR_ENG.RetrievalEngine(engine.corpus)
    corpus = {r["verse_id"]: r for r in engine.corpus}
    aug, added = implied_corpus(engine.corpus)
    engine_implied = ENG.RetrievalEngine(aug)
    cells = G.grid()
    results = {"baseline_engine_version": ENG.ENGINE_VERSION, "current_engine_version": CUR_ENG.ENGINE_VERSION, "corpus": G.CORPUS_VERSION,
               "corpus_records": len(engine.corpus), "options": OPTIONS, "grid_cells_per_mode": len(cells)}

    per_option = {}
    per_cell = defaultdict(dict)
    t_all_candidates = defaultdict(list)       # (mode) -> T of every E-eligible candidate (baseline)
    t_tier1_candidates = defaultdict(list)
    validation = {ENG.ENGINE_VERSION: [0, 0], CUR_ENG.ENGINE_VERSION: [0, 0]}  # version -> [documents, issues]
    vctx = {m: Context(taxonomy=G.TAXONOMY, mode=m, corpus=corpus) for m in G.MODES}
    for mode in G.MODES:
        for option in OPTIONS:
            eng_o = engine_implied if option == "implied_relations" else engine
            index = eng_o.index(mode, "N1")
            index_n2 = eng_o.index(mode, "N2")
            rows = defaultdict(list)
            for cell_id, item_ids, emotion, setting in cells:
                profile = G.build_profile(item_ids, emotion, setting)
                query = G.build_query(profile, mode, ENG.expanded_query)
                vc = vctx["development"] if mode == "development" else vctx["production"]
                if option == "engine_1_1_0":
                    real = current.recommend(profile, query)
                    issues = validate_document("recommendations", real, vc)
                    validation[CUR_ENG.ENGINE_VERSION][0] += 1
                    validation[CUR_ENG.ENGINE_VERSION][1] += len(issues)
                    doc = {"status": real["status"],
                           "reason": (real["abstention"] or {}).get("reason_code")}
                    chosen = [{"record": corpus[i["verse_id"]], "tier": i["tier"], "scores": i["scores"]}
                              for i in real["items"]]
                    cands = []
                else:
                    doc, chosen, cands = run(profile, query, index, option, index_n2)
                diags = [item_diag(c["record"], c["tier"], c["scores"], list(item_ids)) for c in chosen]
                kind = {0: "none", 1: "single"}.get(len(item_ids), "combo")
                row = {"cell": cell_id, "status": doc["status"], "reason": doc["reason"], "items": diags}
                rows[(setting, kind)].append(row)
                if option in STORED_OPTIONS:
                    per_cell[(mode, cell_id)][option] = row
                if option == "v1_0_0":
                    for c in cands:
                        t_all_candidates[mode].append(c["scores"]["text"])
                        if c["tier"] == 1:
                            t_tier1_candidates[mode].append(c["scores"]["text"])
                    # validate the real engine output for this profile against the contract
                    real = engine.recommend(profile, query)
                    issues = validate_document("recommendations", real, vc)
                    validation[ENG.ENGINE_VERSION][0] += 1
                    validation[ENG.ENGINE_VERSION][1] += len(issues)
                    assert [i["verse_id"] for i in real["items"]] == [d["verse_id"] for d in diags], cell_id
            per_option[(mode, option)] = {f"{s}/{k}": summarize(v) for (s, k), v in sorted(rows.items())}
    results["implied_relations_added"] = {"total": sum(added.values()), "by_target": dict(added.most_common())}
    results["contract_validation"] = {v: {"documents": d, "issues": n} for v, (d, n) in validation.items()}
    results["summary"] = {f"{m}|{o}": v for (m, o), v in per_option.items()}
    results["T_distribution_all_candidates"] = {m: distribution(v) for m, v in t_all_candidates.items()}
    results["T_distribution_tier1_candidates"] = {m: distribution(v) for m, v in t_tier1_candidates.items()}

    # coverage matrix (baseline, single items, default and permissive settings)
    cov = {}
    for mode in G.MODES:
        for setting in G.SETTINGS:
            mat = {}
            for x in G.SCENE_GROUPS + G.EXPOSED_TAGS:
                mat[x] = {}
                for e in G.LIT_EMOTIONS:
                    row = per_cell[(mode, f"{x}|{e}|{setting}")]["v1_0_0"]
                    tiers = "".join(str(it["tier"]) for it in row["items"])
                    mat[x][e] = f"{row['status'][0]}{len(row['items'])}:{tiers}" if row["items"] else \
                        f"A:{row['reason']}"
            cov[f"{mode}|{setting}"] = mat
    results["coverage_matrix"] = cov

    # number of tier-1-eligible displayable records per (visual target, emotion): literal / scene_association
    # with the target and the emotion as primary (P) or secondary (S)
    elig = {}
    for mode in G.MODES:
        idx = engine.index(mode, "N1")
        mat = {}
        for x in G.SCENE_GROUPS + G.EXPOSED_TAGS:
            mat[x] = {}
            for e in G.LIT_EMOTIONS:
                p_lit = p_assoc = sec = 0
                for i, rec in enumerate(idx.records):
                    rel = (idx.rel_maps[i].get(x) or {}).get("relation")
                    if rel not in (LAB.LITERAL, LAB.SCENE_ASSOCIATION):
                        continue
                    _, role = LAB.emotion_match(rec, e)
                    if role == "primary":
                        p_lit += rel == LAB.LITERAL
                        p_assoc += rel == LAB.SCENE_ASSOCIATION
                    elif role == "secondary":
                        sec += 1
                mat[x][e] = {"primary_literal": p_lit, "primary_assoc": p_assoc, "secondary": sec}
        elig[mode] = mat
    results["tier1_eligible_counts"] = elig

    # within one returned list: does a scene_association item outrank a literal one, and does a primary-emotion
    # association outrank a secondary-emotion literal?
    pairs = Counter()
    for (m, c), v in per_cell.items():
        its = [i for i in v["v1_0_0"]["items"] if i["tier"] == 1]
        for a_i, a in enumerate(its):
            for b in its[a_i + 1:]:
                if a["relation"] == "scene_association" and b["relation"] == "literal":
                    pairs[(m, "assoc_above_literal_same_E" if a["E"] == b["E"] else "assoc_E1_above_literal_E0.6")] += 1
    results["assoc_vs_literal_order"] = {f"{m}|{k}": n for (m, k), n in sorted(pairs.items())}

    # how much does T change the returned lists? (v1.0.0 vs the same engine without T)
    infl = {}
    for mode in G.MODES:
        for setting in G.SETTINGS:
            cells_ms = [v for (m, c), v in per_cell.items() if m == mode and c.endswith("|" + setting)]
            ok = [v for v in cells_ms if v["v1_0_0"]["items"]]
            order = sum(1 for v in ok if [i["verse_id"] for i in v["v1_0_0"]["items"]] !=
                        [i["verse_id"] for i in v["drop_T"]["items"]])
            sets = sum(1 for v in ok if {i["verse_id"] for i in v["v1_0_0"]["items"]} !=
                       {i["verse_id"] for i in v["drop_T"]["items"]})
            infl[f"{mode}|{setting}"] = {"non_abstained_cells": len(ok), "order_differs": order, "set_differs": sets}
    results["T_influence_vs_drop_T"] = infl

    # every cell whose list differs between engine 1.0.0 and 1.1.0
    changes = []
    for (m, c), v in sorted(per_cell.items()):
        a, b = v["v1_0_0"]["items"], v["engine_1_1_0"]["items"]
        if [i["verse_id"] for i in a] != [i["verse_id"] for i in b]:
            same_upper = [i["verse_id"] for i in a if i["tier"] != 3] == [i["verse_id"] for i in b if i["tier"] != 3]
            changes.append({"cell": f"{m}|{c}", "tiers_1_2_unchanged": same_upper,
                            "before": [(i["verse_id"], i["tier"], i["final"], i["scene_conflict"]) for i in a],
                            "after": [(i["verse_id"], i["tier"], i["final"], i["scene_conflict"]) for i in b]})
    results["changes_1_0_0_to_1_1_0"] = {"cells_changed": len(changes),
                                         "all_tier_1_2_unchanged": all(x["tiers_1_2_unchanged"] for x in changes),
                                         "cells": changes}

    # side-by-side lists for selected cells
    results["per_cell"] = {f"{m}|{c}": v for (m, c), v in per_cell.items()}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1, sort_keys=False)
    print(f"wrote {args.out}: contract validation {results['contract_validation']}")


if __name__ == "__main__":
    main()
