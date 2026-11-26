"""Human-judgment retrieval metrics from completed blind ratings (RETRIEVAL_METHOD.md section 10).

    python3 -m evaluation.retrieval.metrics --ratings evaluation/retrieval/review/ratings_R1.jsonl [...] \
        --mapping evaluation/retrieval/review/mapping__<cv>__<date>.json --corpus-version <cv> --date <date>

Refuses (exit code 3) when there are no ratings or when any pooled item is unrated: no metric is ever
computed from missing or synthetic judgments.

Per method: P@3 (denominator 3; relevant = mean overall >= 2), precision among returned, nDCG@3 over the pooled
judgments (gain = mean overall, ideal = best 3 pooled items of the query; unjudged items cannot occur because
the pool is complete), emotion relevance and visual relevance (share of returned items with mean fit >= 2),
coverage, abstention rate, abstention correctness (an abstention is correct when no pooled item of that query is
relevant), latency p50/p95 (from the run summary), and a paired bootstrap of the per-query difference to the
hybrid method (1,000 resamples, fixed seed, 95% percentile interval). Abstained queries score 0 on P@3 and nDCG@3.
"""
import argparse
import json
import math
import os
import random
import sys

from contracts.taxonomy import load_taxonomy
from contracts.validate import Context, load_jsonl, validate_records

from .make_review_sheet import item_id, load_runs
from .run_experiments import RUNS

RELEVANT = 2
BOOTSTRAP = 1000
SEED = 20261126


class MissingRatings(Exception):
    pass


def load_ratings(paths):
    records = []
    for path in paths:
        if not os.path.isfile(path):
            raise MissingRatings(f"{path}: no such ratings file")
        rows, issues = load_jsonl(path)
        issues += validate_records("evaluation_record", rows, Context(taxonomy=load_taxonomy(), mode="production"))
        if issues:
            raise MissingRatings(f"{path}: invalid evaluation records: {issues[0]}")
        records += [r for _, r in rows if r["layer"] == "retrieval"]
    if not records:
        raise MissingRatings("no completed retrieval ratings")
    return records


def mean_ratings(records):
    acc = {}
    for r in records:
        acc.setdefault(r["item_id"], []).append(r["rating"])
    return {iid: {c: sum(x[c] for x in rs) / len(rs) for c in ("visual_fit", "emotion_fit", "overall")}
            for iid, rs in acc.items()}


def dcg(gains):
    return sum(g / math.log2(i + 2) for i, g in enumerate(gains))


def bootstrap(diffs, seed=SEED, n=BOOTSTRAP):
    rng = random.Random(seed)
    means = sorted(sum(rng.choice(diffs) for _ in diffs) / len(diffs) for _ in range(n))
    return {"mean_diff": sum(diffs) / len(diffs), "ci95": [means[int(0.025 * n)], means[int(0.975 * n) - 1]]}


def compute(ratings, mapping, runs, summary=None):
    unrated = sorted(set(mapping["items"]) - set(ratings))
    if unrated:
        raise MissingRatings(f"{len(unrated)} pooled items have no complete rating (first: {unrated[0]})")
    by_query = {}
    for iid, m in mapping["items"].items():
        by_query.setdefault(m["profile_id"], []).append(ratings[iid]["overall"])
    ideal = {q: dcg(sorted(v, reverse=True)[:3]) for q, v in by_query.items()}
    per_query, out = {}, {}
    for method, docs in runs.items():
        p3, ndcg, returned, rel, emo, vis, abst, abst_ok = [], [], 0, 0, 0, 0, 0, 0
        for doc in docs:
            q = doc["profile_id"]
            gains = [ratings[item_id(q, it["verse_id"])] for it in doc["items"][:3]]
            hits = sum(g["overall"] >= RELEVANT for g in gains)
            p3.append(hits / 3)
            ndcg.append(dcg([g["overall"] for g in gains]) / ideal[q] if ideal.get(q) else 0.0)
            returned += len(gains)
            rel += hits
            emo += sum(g["emotion_fit"] >= RELEVANT for g in gains)
            vis += sum(g["visual_fit"] >= RELEVANT for g in gains)
            if doc["status"] == "abstained":
                abst += 1
                abst_ok += all(v < RELEVANT for v in by_query.get(q, []))
        per_query[method] = {"p3": p3, "ndcg3": ndcg}
        n = len(docs)
        out[method] = {"queries": n, "P@3": sum(p3) / n, "nDCG@3": sum(ndcg) / n,
                       "precision_among_returned": rel / returned if returned else None,
                       "emotion_relevance": emo / returned if returned else None,
                       "visual_relevance": vis / returned if returned else None,
                       "coverage": (n - abst) / n, "abstention_rate": abst / n,
                       "abstention_correctness": abst_ok / abst if abst else None}
        if summary and method in summary.get("methods", {}):
            out[method]["latency_ms_p50"] = summary["methods"][method]["latency_ms_p50"]
            out[method]["latency_ms_p95"] = summary["methods"][method]["latency_ms_p95"]
    if "hybrid" in per_query:
        for method in per_query:
            if method == "hybrid":
                continue
            out[method]["bootstrap_vs_hybrid"] = {
                metric: bootstrap([a - b for a, b in zip(per_query[method][metric], per_query["hybrid"][metric])])
                for metric in ("p3", "ndcg3")}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description="Retrieval metrics from completed blind ratings")
    parser.add_argument("--ratings", nargs="+", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--runs-dir", default=RUNS)
    parser.add_argument("--corpus-version", required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        ratings = mean_ratings(load_ratings(args.ratings))
        with open(args.mapping, encoding="utf-8") as fh:
            mapping = json.load(fh)
        methods = {m for item in mapping["items"].values() for m in item["methods"]}
        runs = load_runs(args.runs_dir, args.corpus_version, args.date, methods)
        summary_path = os.path.join(args.runs_dir, f"summary__{args.corpus_version}__{args.date}.json")
        summary = json.load(open(summary_path, encoding="utf-8")) if os.path.isfile(summary_path) else None
        result = compute(ratings, mapping, runs, summary)
    except MissingRatings as exc:
        print(f"REFUSED: {exc}. Metrics are reported only from completed human rating sheets.", file=sys.stderr)
        return 3
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
