"""Bag of Words, TF-IDF and cosine similarity with sparse dict vectors (RETRIEVAL_METHOD.md section 2).

Two weighting schemes:
    smoothed (production, B1/B5):  tf = raw count,            idf(t) = ln((1 + N) / (1 + df(t))) + 1
    lecture  (B1-lecture, Unit 8): tf = count / total terms,  idf(t) = log(N / (1 + df(t)))

Both vectors are L2-normalized, so cosine = dot product. Dividing TF by the document length multiplies a
vector by a constant, which L2 normalization removes: only the IDF differs between the two schemes. The
lecture IDF is <= 0 when df >= N - 1; those terms are reported by `nonpositive_idf_terms()`.
The lecture slide writes "log" without a base; any base gives the same cosine (it scales every IDF by the
same positive constant), so the natural log is used.
"""
import math
from collections import Counter

SMOOTHED = "smoothed"
LECTURE = "lecture"
SCHEMES = (SMOOTHED, LECTURE)


def bag_of_words(tokens):
    """Bag of Words: term -> raw count."""
    return dict(Counter(tokens))


def l2_normalize(vec):
    norm = math.sqrt(sum(w * w for w in vec.values()))
    if norm == 0.0:
        return {}
    return {t: w / norm for t, w in vec.items()}


def cosine(a, b):
    """Cosine of two L2-normalized sparse vectors (the dot product). Empty vectors give 0.0."""
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b[t] for t, w in a.items() if t in b)


class TfidfModel:
    """IDF statistics fitted once over a list of tokenized documents, plus the normalized document vectors."""

    def __init__(self, documents, scheme=SMOOTHED):
        if scheme not in SCHEMES:
            raise ValueError(f"scheme must be one of {SCHEMES}")
        self.scheme = scheme
        self.n_docs = len(documents)
        df = Counter()
        for tokens in documents:
            df.update(set(tokens))
        self.df = dict(df)
        self.idf = {t: self.idf_value(d) for t, d in self.df.items()}
        self.doc_vectors = [self.vector(bag_of_words(tokens)) for tokens in documents]

    def idf_value(self, df):
        n = self.n_docs
        if self.scheme == SMOOTHED:
            return math.log((1 + n) / (1 + df)) + 1
        return math.log(n / (1 + df))

    def weights(self, counts):
        """Unnormalized tf * idf for a {term: count-or-weight} mapping. Terms outside the vocabulary are dropped."""
        if self.scheme == LECTURE:
            total = sum(counts.values())
            if total <= 0:
                return {}
            tf = {t: c / total for t, c in counts.items()}
        else:
            tf = counts
        return {t: f * self.idf[t] for t, f in tf.items() if t in self.idf and f * self.idf[t] != 0.0}

    def vector(self, counts):
        """L2-normalized TF-IDF vector for a {term: count-or-weight} mapping."""
        return l2_normalize(self.weights(counts))

    def nonpositive_idf_terms(self):
        return sorted(t for t, v in self.idf.items() if v <= 0)


def clamp01(x):
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else x
