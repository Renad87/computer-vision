"""Public interface of the retrieval engine.

    from retrieval.engine import recommend
    result = recommend(profile, corpus, query)          # a `recommendations` document (contracts/CONTRACTS.md)

`recommend` is a pure function: no I/O, no global state change, inputs not mutated, and the same inputs give a
byte-identical JSON result (`timings_ms` is null). It builds the corpus index on every call. A long-running
application should build the index once with `RetrievalEngine` and reuse it; `RetrievalEngine.reload()` (or a new
engine) picks up a newer corpus snapshot without code changes.

Methods (retrieval_query.method; RETRIEVAL_METHOD.md section 9):
    hybrid          B5         E gate, tiers, Score = wE*E + wV*V + wT*T (smoothed TF-IDF)
    hybrid_no_tier  B5-noTier  E gate, the same Score, no eligibility tiers
    labels_weighted B4         E gate, tiers, E and V only (T null, weights renormalized)
    labels_exact    B3         E gate, exact literal / scene_association match with any confirmed item
    tfidf           B1         E gate, rank by smoothed TF-IDF T only
    tfidf_lecture   B1-lecture E gate, rank by lecture TF-IDF T only
The E gate is kept in every method because the `recommendations` contract requires an emotion match (primary or
secondary) for every item. Methods without tiers report tier 1 for every item (a single pool).
"""
import time

from contracts.taxonomy import load_taxonomy
from contracts.validate import display_allowed, load_jsonl

from . import labels as L
from .explain import abstention_message, explain
from .preprocess import DEFAULT_VARIANT, tokenize
from .rank import abstention_reason, final_score, select, sort_key, status_for
from .tfidf import LECTURE, SMOOTHED, TfidfModel, clamp01, cosine

ENGINE_VERSION = "1.1.0"  # 1.1.0: tier-3 tie-break prefers scene-neutral verses (quality_diagnosis)
SCHEMA_VERSION = "1.0.0"
VERSE_WEIGHT, MEANING_WEIGHT = 0.7, 0.3
TIERED_METHODS = ("hybrid", "labels_weighted")
TEXT_METHODS = {"hybrid": SMOOTHED, "hybrid_no_tier": SMOOTHED, "tfidf": SMOOTHED, "tfidf_lecture": LECTURE}
VISUAL_METHODS = ("hybrid", "hybrid_no_tier", "labels_weighted", "labels_exact")
SUPPORTED_METHODS = ("hybrid", "hybrid_no_tier", "labels_weighted", "labels_exact", "tfidf", "tfidf_lecture")

TAXONOMY = load_taxonomy()  # read once at import; recommend() itself does no I/O


class CorpusIndex:
    """Displayable records of one corpus in one mode, with their TF-IDF spaces (verse and meaning).

    Built once per (corpus, mode, variant) and reused across requests."""

    def __init__(self, corpus, corpus_mode, variant=DEFAULT_VARIANT):
        self.corpus_mode = corpus_mode
        self.variant = variant
        self.records = sorted((r for r in corpus if display_allowed(r, corpus_mode)), key=lambda r: r["verse_id"])
        self.rel_maps = [L.relation_map(r) for r in self.records]
        self.verse_tokens = [tokenize(r["text_original"], variant) for r in self.records]
        self.meaning_pos = {}
        meaning_docs = []
        for i, r in enumerate(self.records):
            if (r.get("meaning_ar") or "").strip():
                self.meaning_pos[i] = len(meaning_docs)
                meaning_docs.append(tokenize(r["meaning_ar"], variant))
        self._meaning_docs = meaning_docs
        self._pos = {r["verse_id"]: i for i, r in enumerate(self.records)}
        self._models = {}
        self.verse_model(SMOOTHED)  # the production space (also used for near-duplicate detection)
        self.meaning_model(SMOOTHED)

    def verse_model(self, scheme):
        key = ("verse", scheme)
        if key not in self._models:
            self._models[key] = TfidfModel(self.verse_tokens, scheme)
        return self._models[key]

    def meaning_model(self, scheme):
        key = ("meaning", scheme)
        if key not in self._models:
            self._models[key] = TfidfModel(self._meaning_docs, scheme)
        return self._models[key]

    def query_vectors(self, counts, scheme):
        return self.verse_model(scheme).vector(counts), self.meaning_model(scheme).vector(counts)

    def text_score(self, query_vecs, i, scheme):
        """T = 0.7 cos(q, verse) + 0.3 cos(q, meaning); T = cos(q, verse) without a meaning."""
        qv, qm = query_vecs
        cv = clamp01(cosine(qv, self.verse_model(scheme).doc_vectors[i]))
        if i not in self.meaning_pos:
            return cv
        cm = clamp01(cosine(qm, self.meaning_model(scheme).doc_vectors[self.meaning_pos[i]]))
        return clamp01(VERSE_WEIGHT * cv + MEANING_WEIGHT * cm)

    def near_dup(self, a, b):
        vecs = self.verse_model(SMOOTHED).doc_vectors
        return cosine(vecs[self._pos[a["verse_id"]]], vecs[self._pos[b["verse_id"]]])


def query_counts(profile, variant, taxonomy=TAXONOMY):
    """Weighted query bag of words: {token: summed weight} from the confirmed items and the concept."""
    counts = {}
    for term, weight in L.query_terms(profile, taxonomy):
        for tok in tokenize(term, variant):
            counts[tok] = counts.get(tok, 0.0) + weight
    return counts


def expanded_query(profile, query, taxonomy=TAXONOMY):
    """A copy of `query` carrying `query_terms_ar` (the expanded Arabic terms, deduplicated, in order)."""
    out = dict(query)
    seen = []
    for term, _ in L.query_terms(profile, taxonomy):
        if term not in seen:
            seen.append(term)
    out["query_terms_ar"] = seen
    return out


def _item(rank, c, profile, corpus_mode, taxonomy):
    r = c["record"]
    return {
        "rank": rank,
        "verse_id": r["verse_id"],
        "apcd_row": r["apcd_row"],
        "text_original": r["text_original"],
        "poet_name_apcd": r["poet"]["name_apcd"],
        "era_apcd": r["era_apcd"],
        "attribution_status": r["attribution_status"],
        "tier": c["tier"],
        "scores": dict(c["scores"]),
        "matched": {
            "lit_emotion": profile["selected_lit_emotion"],
            "emotion_role": c["role"],
            "visual_targets": list(c["matched_targets"]),
            "relations": list(c["matched_relations"]),
        },
        "explanation": explain(c, profile, corpus_mode, taxonomy),
        "review_status": r["review"]["status"],
    }


def _candidates(profile, query, index, taxonomy):
    method = query["method"]
    if method not in SUPPORTED_METHODS:
        raise ValueError(f"method {method!r} is not implemented (supported: {', '.join(SUPPORTED_METHODS)})")
    weights = query["weights"]
    tiers_enabled = set(query["tiers_enabled"])
    items = profile.get("confirmed_visual_items") or []
    anchor_ids = L.anchors(profile)
    symbolic = bool(profile.get("symbolic_allowed"))
    selected = profile["selected_lit_emotion"]
    secondary = profile.get("secondary_lit_emotion")
    rw = taxonomy.relation_weights

    scheme = TEXT_METHODS.get(method)
    counts = query_counts(profile, index.variant, taxonomy) if scheme else {}
    qvecs = index.query_vectors(counts, scheme) if counts else None

    stats = {"displayable": len(index.records), "emotion_eligible": 0, "anchor_covered": 0, "candidates": 0}
    out = []
    for i, r in enumerate(index.records):
        rm = index.rel_maps[i]
        if anchor_ids and L.covers_anchor(rm, anchor_ids, symbolic):
            stats["anchor_covered"] += 1
        e, role = L.emotion_match(r, selected)
        if e is None:
            continue
        stats["emotion_eligible"] += 1
        natural = L.natural_tier(rm, anchor_ids, symbolic)
        if method in TIERED_METHODS:
            if not L.allowed_tier(natural, profile, tiers_enabled):
                continue
            tier = natural
        elif method == "labels_exact":
            if not any((rm.get(x["id"]) or {}).get("relation") in L.TIER1_RELATIONS for x in items):
                continue
            tier = 1
        else:
            tier = 1
        if method == "labels_exact":
            v = 1.0
        elif method in VISUAL_METHODS:
            v = L.visual_score(rm, items, symbolic, rw)
        else:
            v = None
        t = index.text_score(qvecs, i, scheme) if qvecs is not None else None
        scores = {"emotion": e, "visual": v, "text": t, "semantic": None}
        scores["final"] = final_score(scores, weights)
        targets, relations = L.matched_visuals(rm, items, symbolic, rw)
        conflict = tier == 3 and L.scene_conflict(rm, [x["id"] for x in items])
        out.append({"record": r, "role": role, "tier": tier, "natural_tier": natural, "scores": scores,
                    "secondary_match": L.secondary_match(r, secondary), "anchors": anchor_ids,
                    "matched_targets": targets, "matched_relations": relations, "scene_conflict": conflict})
    stats["candidates"] = len(out)
    out.sort(key=sort_key)
    return out, stats, anchor_ids


def _recommend(profile, query, index, taxonomy, with_timings=False):
    t0 = time.perf_counter()
    corpus_mode = query["corpus_mode"]
    cands, stats, anchor_ids = _candidates(profile, query, index, taxonomy)
    t1 = time.perf_counter()
    k = query["k"]
    max_tier3 = 1 if query["method"] in TIERED_METHODS else None
    chosen = select(cands, k, query["diversity"], index.near_dup, max_tier3=max_tier3,
                    min_score=float(query.get("min_score", 0.0)))
    t2 = time.perf_counter()
    items = [_item(n, c, profile, corpus_mode, taxonomy) for n, c in enumerate(chosen, 1)]
    abstention = None
    if not items:
        reason = abstention_reason(stats)
        gap = None if reason == "empty_corpus" else {"visual_targets": list(anchor_ids),
                                                      "lit_emotion": profile["selected_lit_emotion"]}
        abstention = {"reason_code": reason,
                      "message_ar": abstention_message(reason, anchor_ids, profile["selected_lit_emotion"], taxonomy),
                      "coverage_gap": gap}
    t3 = time.perf_counter()
    doc = {"schema_version": SCHEMA_VERSION, "taxonomy_version": taxonomy.version}
    if profile.get("fixture") is True or query.get("fixture") is True:
        doc["fixture"] = True
    w = query["weights"]
    doc.update({
        "query_id": query["query_id"],
        "profile_id": query.get("profile_id", profile["profile_id"]),
        "engine_version": ENGINE_VERSION,
        "corpus_version": query["corpus_version"],
        "corpus_mode": corpus_mode,
        "k": k,
        "weights": {n: float(w[n]) for n in ("emotion", "visual", "text", "semantic")},
        "status": status_for(len(items), k),
        "items": items,
        "abstention": abstention,
        "timings_ms": None,
    })
    if with_timings:
        doc["timings_ms"] = {"retrieve": (t1 - t0) * 1000, "rank": (t2 - t1) * 1000, "explain": (t3 - t2) * 1000,
                             "total": (t3 - t0) * 1000}
    return doc


def recommend(profile, corpus, query, *, index=None, taxonomy=None):
    """Recommend up to k verses for a confirmed image profile, or abstain with a reason.

    profile: `image_profile` dict; corpus: list of `poetry_record` dicts; query: `retrieval_query` dict.
    Only records with display_allowed(record, query["corpus_mode"]) are considered. Pass a prebuilt
    `CorpusIndex` (same corpus, mode and variant) to skip index construction."""
    taxonomy = taxonomy or TAXONOMY
    variant = query.get("preprocessing_variant", DEFAULT_VARIANT)
    if index is None or index.corpus_mode != query["corpus_mode"] or index.variant != variant:
        index = CorpusIndex(corpus, query["corpus_mode"], variant)
    return _recommend(profile, query, index, taxonomy)


def load_corpus(path):
    """Read a poetry_record JSONL snapshot into a list of dicts (read-only)."""
    records, issues = load_jsonl(path)
    if issues:
        raise ValueError(f"{path}: {issues[0]}")
    return [r for _, r in records]


class RetrievalEngine:
    """Integration wrapper: holds one corpus snapshot and reuses its indexes across requests.

        engine = RetrievalEngine.from_jsonl("poetry_corpus/exports/corpus_all_v1.jsonl")
        result = engine.recommend(profile, query)
        engine.reload(load_corpus(newer_snapshot_path))     # new snapshot, indexes rebuilt on demand
    """

    def __init__(self, corpus, taxonomy=None):
        self.taxonomy = taxonomy or TAXONOMY
        self.reload(corpus)

    @classmethod
    def from_jsonl(cls, path, taxonomy=None):
        return cls(load_corpus(path), taxonomy)

    def reload(self, corpus):
        self.corpus = list(corpus)
        self._indexes = {}

    def index(self, corpus_mode, variant=DEFAULT_VARIANT):
        key = (corpus_mode, variant)
        if key not in self._indexes:
            self._indexes[key] = CorpusIndex(self.corpus, corpus_mode, variant)
        return self._indexes[key]

    def recommend(self, profile, query, with_timings=False):
        index = self.index(query["corpus_mode"], query.get("preprocessing_variant", DEFAULT_VARIANT))
        return _recommend(profile, query, index, self.taxonomy, with_timings=with_timings)
