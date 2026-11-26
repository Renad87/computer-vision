"""Experiment A runner: every method over the same development profiles, queries and corpus.

    python3 -m evaluation.retrieval.run_experiments \
        --corpus poetry_corpus/records/p0_ai_drafts_v1.jsonl --corpus-version p0_ai_drafts_v1

Writes, under evaluation/retrieval/runs/:
    <method>__<corpus_version>__<date>.jsonl          one `recommendations` document per line
    queries__<method>__<corpus_version>__<date>.jsonl one `retrieval_query` per line, with query_terms_ar
    summary__<corpus_version>__<date>.json            engineering diagnostics (see below)

The diagnostics are computed from the AI-draft labels and the hand-derived fixture expectations. They are
engineering checks, NOT human relevance judgments: no human-judgment metric is reported until the blind rating
sheets (make_review_sheet.py) are completed.
"""
import argparse
import datetime
import hashlib
import json
import os
import statistics
import time
import uuid

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, validate_document
from retrieval import labels as L
from retrieval.engine import (ENGINE_VERSION, CorpusIndex, RetrievalEngine, expanded_query, load_corpus,
                              query_counts, recommend)
from retrieval.tfidf import LECTURE, SMOOTHED, cosine

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "fixtures")
RUNS = os.path.join(ROOT, "evaluation", "retrieval", "runs")
TAXONOMY = load_taxonomy()

# code, method, weights (None = the query's own weights 0.45 / 0.35 / 0.20 / 0)
METHODS = (
    ("B1-lecture", "tfidf_lecture", {"emotion": 0.0, "visual": 0.0, "text": 1.0, "semantic": 0.0}),
    ("B1", "tfidf", {"emotion": 0.0, "visual": 0.0, "text": 1.0, "semantic": 0.0}),
    ("B3", "labels_exact", {"emotion": 0.5, "visual": 0.5, "text": 0.0, "semantic": 0.0}),
    ("B4", "labels_weighted", None),
    ("B5", "hybrid", None),
    ("B5-noTier", "hybrid_no_tier", None),
)
LATENCY_REPEATS = 20


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_scenarios():
    index = load_json(os.path.join(FIXTURES, "dev_profiles", "index.json"))
    out = []
    for entry in index["profiles"]:
        out.append({"name": os.path.basename(entry["profile"]).rsplit(".", 1)[0],
                    "profile": load_json(os.path.join(FIXTURES, entry["profile"])),
                    "query": load_json(os.path.join(FIXTURES, entry["query"])),
                    "expected": entry["expected"], "pair": entry.get("pair")})
    return out


def method_query_id(base_id, method):
    digest = hashlib.sha256(f"{base_id}:{method}".encode()).digest()
    return str(uuid.UUID(bytes=digest[:16], version=4))


def method_query(query, method, weights, corpus_version):
    q = dict(query)
    q["method"] = method
    if weights is not None:
        q["weights"] = dict(weights)
    if method != "hybrid":
        q["query_id"] = method_query_id(query["query_id"], method)
    q["corpus_version"] = corpus_version
    return q


def percentile(values, p):
    values = sorted(values)
    if not values:
        return None
    pos = (len(values) - 1) * p / 100
    lo, hi = int(pos), min(int(pos) + 1, len(values) - 1)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def jaccard(a, b):
    a, b = set(a), set(b)
    return 1.0 if not a and not b else len(a & b) / len(a | b)


def label_diagnostics(scenario, doc):
    """Label-derived checks of one result against the AI-draft labels and the hand-derived expectations."""
    profile = scenario["profile"]
    anchor_ids = L.anchors(profile)
    expected = scenario["expected"]
    eligible = set(expected["tier1"]) | set(expected["tier2"]) | set(expected["tier3"])
    reason = doc["abstention"]["reason_code"] if doc["abstention"] else None
    items = doc["items"]
    anchored = sum(1 for it in items if any(t in anchor_ids for t in it["matched"]["visual_targets"]))
    return {
        "status": doc["status"], "reason": reason, "verse_ids": [it["verse_id"] for it in items],
        "status_matches_expected": doc["status"] == expected["status"] and reason == expected["abstain"],
        "items_in_expected_eligible_set": sum(1 for it in items if it["verse_id"] in eligible),
        "items_with_anchor_relation": anchored,
        "items_primary_emotion": sum(1 for it in items if it["matched"]["emotion_role"] == "primary"),
        "tier3_items": sum(1 for it in items if it["tier"] == 3),
    }


def preprocessing_evidence(corpus, scenarios):
    """Compare N0 / N1 / N2 on the development data: vocabulary, query-term coverage, records reached by the
    text component, and whether the hybrid result changes."""
    out = {}
    base = {}
    for variant in ("N0", "N1", "N2"):
        index = CorpusIndex(corpus, "development", variant)
        vocab = index.verse_model(SMOOTHED).idf
        hits = total = reached = 0
        changed = []
        for s in scenarios:
            counts = query_counts(s["profile"], variant)
            total += len(counts)
            hits += sum(1 for t in counts if t in vocab)
            qv, _ = index.query_vectors(counts, SMOOTHED) if counts else ({}, {})
            reached += sum(1 for d in index.verse_model(SMOOTHED).doc_vectors if cosine(qv, d) > 0)
            q = dict(s["query"], preprocessing_variant=variant)
            ids = [it["verse_id"] for it in recommend(s["profile"], corpus, q, index=index)["items"]]
            if variant == "N1":
                base[s["name"]] = ids
            out.setdefault("_ids", {}).setdefault(variant, {})[s["name"]] = ids
        out[variant] = {"verse_vocabulary": len(vocab), "query_tokens": total, "query_tokens_in_vocabulary": hits,
                        "mean_records_with_verse_cosine_gt0": reached / len(scenarios)}
    ids = out.pop("_ids")
    for variant in ("N0", "N2"):
        out[variant]["profiles_with_different_hybrid_result_than_N1"] = sorted(
            n for n in base if ids[variant][n] != base[n])
    return out


def run(corpus_path, corpus_version, date, out_dir=RUNS, scenarios=None, latency_repeats=LATENCY_REPEATS):
    corpus = load_corpus(corpus_path)
    corpus_map = {r["verse_id"]: r for r in corpus}
    scenarios = scenarios or load_scenarios()
    with open(corpus_path, "rb") as fh:
        corpus_sha = hashlib.sha256(fh.read()).hexdigest()
    os.makedirs(out_dir, exist_ok=True)
    t = time.perf_counter()
    engine = RetrievalEngine(corpus)
    engine.index("development")
    build_ms = (time.perf_counter() - t) * 1000
    ctx = Context(taxonomy=TAXONOMY, mode="development", corpus=corpus_map)
    is_p0 = corpus_version == "p0_ai_drafts_v1"
    summary = {"corpus_path": os.path.relpath(corpus_path, ROOT), "corpus_sha256": corpus_sha,
               "corpus_version": corpus_version, "records": len(corpus), "engine_version": ENGINE_VERSION,
               "date": date, "profiles": len(scenarios), "index_build_ms": build_ms,
               "note": "Engineering diagnostics from AI-draft labels and hand-derived expectations; not human "
                       "relevance judgments.",
               "expectations_apply": is_p0, "methods": {}}
    results = {}
    for code, method, weights in METHODS:
        docs, queries, latencies, diags, issues = [], [], [], [], 0
        for s in scenarios:
            q = method_query(s["query"], method, weights, corpus_version)
            doc = engine.recommend(s["profile"], q)
            for _ in range(latency_repeats):
                t = time.perf_counter()
                engine.recommend(s["profile"], q)
                latencies.append((time.perf_counter() - t) * 1000)
            issues += len(validate_document("recommendations", doc, ctx))
            issues += len(validate_document("retrieval_query", expanded_query(s["profile"], q), ctx))
            docs.append(doc)
            queries.append(expanded_query(s["profile"], q))
            diags.append(label_diagnostics(s, doc))
        results[method] = {s["name"]: d for s, d in zip(scenarios, diags)}
        name = f"{method}__{corpus_version}__{date}.jsonl"
        with open(os.path.join(out_dir, name), "w", encoding="utf-8") as fh:
            for doc in docs:
                fh.write(json.dumps(doc, ensure_ascii=False) + "\n")
        with open(os.path.join(out_dir, "queries__" + name), "w", encoding="utf-8") as fh:
            for q in queries:
                fh.write(json.dumps(q, ensure_ascii=False) + "\n")
        returned = sum(len(d["verse_ids"]) for d in diags)
        statuses, reasons = {}, {}
        for d in diags:
            statuses[d["status"]] = statuses.get(d["status"], 0) + 1
            if d["reason"]:
                reasons[d["reason"]] = reasons.get(d["reason"], 0) + 1
        m = {"code": code, "run_file": name, "contract_issues": issues, "status_counts": statuses,
             "abstention_reasons": reasons, "items_returned": returned,
             "coverage": sum(1 for d in diags if d["status"] != "abstained") / len(diags),
             "items_with_anchor_relation": sum(d["items_with_anchor_relation"] for d in diags),
             "items_primary_emotion": sum(d["items_primary_emotion"] for d in diags),
             "tier3_items": sum(d["tier3_items"] for d in diags),
             "latency_ms_p50": percentile(latencies, 50), "latency_ms_p95": percentile(latencies, 95),
             "latency_samples": len(latencies)}
        if is_p0:
            m["status_and_reason_match_expected"] = sum(d["status_matches_expected"] for d in diags)
            m["items_in_expected_eligible_set"] = sum(d["items_in_expected_eligible_set"] for d in diags)
        summary["methods"][method] = m
    hybrid = results["hybrid"]
    for method in results:
        summary["methods"][method]["mean_jaccard_with_hybrid"] = statistics.mean(
            jaccard(results[method][n]["verse_ids"], hybrid[n]["verse_ids"]) for n in hybrid)
    pairs = []
    for s in scenarios:
        pair = s["pair"]
        if pair and s["name"] < pair and pair in hybrid:
            a, b = hybrid[s["name"]], hybrid[pair]
            pairs.append({"a": s["name"], "b": pair, "a_items": a["verse_ids"], "b_items": b["verse_ids"],
                          "jaccard": jaccard(a["verse_ids"], b["verse_ids"])})
    summary["hybrid_pairs"] = pairs
    cold = []
    for s in scenarios:
        q = method_query(s["query"], "hybrid", None, corpus_version)
        t = time.perf_counter()
        recommend(s["profile"], corpus, q)
        cold.append((time.perf_counter() - t) * 1000)
    summary["latency_cold_recommend_ms"] = {"p50": percentile(cold, 50), "p95": percentile(cold, 95),
                                            "note": "pure recommend(): index rebuilt on every call"}
    lecture = engine.index("development").verse_model(LECTURE)
    summary["lecture_nonpositive_idf_terms"] = {"count": len(lecture.nonpositive_idf_terms()),
                                                "terms": lecture.nonpositive_idf_terms()[:30],
                                                "n_docs": lecture.n_docs}
    summary["preprocessing"] = preprocessing_evidence(corpus, scenarios)
    summary["per_profile"] = {m: {n: {"status": d["status"], "reason": d["reason"], "items": d["verse_ids"]}
                                  for n, d in r.items()} for m, r in results.items()}
    path = os.path.join(out_dir, f"summary__{corpus_version}__{date}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    return summary, path


def main(argv=None):
    parser = argparse.ArgumentParser(description="Experiment A runs (development profiles)")
    parser.add_argument("--corpus", default=os.path.join(ROOT, "poetry_corpus", "records", "p0_ai_drafts_v1.jsonl"))
    parser.add_argument("--corpus-version", default="p0_ai_drafts_v1")
    parser.add_argument("--date", default=datetime.date.today().isoformat())
    parser.add_argument("--out-dir", default=RUNS)
    args = parser.parse_args(argv)
    summary, path = run(args.corpus, args.corpus_version, args.date, args.out_dir)
    for method, m in summary["methods"].items():
        print(f"{m['code']:10} {method:16} issues={m['contract_issues']} status={m['status_counts']} "
              f"p95={m['latency_ms_p95']:.2f}ms")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
