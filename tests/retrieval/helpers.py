"""Shared paths and loaders for the retrieval tests."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURES = os.path.join(ROOT, "fixtures")
DEV_CORPUS = os.path.join(ROOT, "poetry_corpus", "records", "p0_ai_drafts_v1.jsonl")
SNAPSHOT = os.path.join(ROOT, "poetry_corpus", "exports", "corpus_all_v1.jsonl")
APCD_EXTRACT = os.path.join(ROOT, "handoff", "mohammed_m5", "data", "apcd", "apcd_extract_v1.csv")


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def scenarios():
    index = load_json(os.path.join(FIXTURES, "dev_profiles", "index.json"))["profiles"]
    out = []
    for e in index:
        out.append({"name": os.path.basename(e["profile"]).rsplit(".", 1)[0],
                    "profile": load_json(os.path.join(FIXTURES, e["profile"])),
                    "query": load_json(os.path.join(FIXTURES, e["query"])),
                    "expected": e["expected"], "pair": e.get("pair")})
    return out
