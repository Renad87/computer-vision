"""Suggestion policy: turn a probability vector into the emotions offered to
the user. Shared by inference.py (what the app shows) and evaluate.py (how
often the offered set contains the true label, and how large it is)."""
from __future__ import annotations

import numpy as np

try:
    from . import config
    from .metrics import normalized_entropy, top2_margin
except ImportError:
    import config
    from metrics import normalized_entropy, top2_margin


def suggest_indices(prob: np.ndarray,
                    cum_prob: float = config.SUGGESTION_CUM_PROB,
                    max_n: int = config.SUGGESTION_MAX,
                    min_prob: float = config.SUGGESTION_MIN_PROB) -> list:
    """Classes in descending probability until the cumulative mass reaches
    `cum_prob`, capped at `max_n`, skipping classes under `min_prob`.
    The top class is always included."""
    order = np.argsort(prob)[::-1]
    chosen, mass = [], 0.0
    for i in order:
        if chosen and (len(chosen) >= max_n or mass >= cum_prob or prob[i] < min_prob):
            break
        chosen.append(int(i))
        mass += float(prob[i])
    return chosen


def uncertainty(prob: np.ndarray) -> dict:
    p = prob[None, :]
    margin = float(top2_margin(p)[0])
    ent = float(normalized_entropy(p)[0])
    amb = margin < config.AMBIGUOUS_MARGIN or ent > config.AMBIGUOUS_ENTROPY
    return {"top1_prob": float(prob.max()), "margin_top1_top2": round(margin, 4),
            "normalized_entropy": round(ent, 4), "is_ambiguous": bool(amb)}


def is_ambiguous_batch(prob: np.ndarray) -> np.ndarray:
    return (top2_margin(prob) < config.AMBIGUOUS_MARGIN) | (normalized_entropy(prob) > config.AMBIGUOUS_ENTROPY)
