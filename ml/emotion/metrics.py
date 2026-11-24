"""Evaluation metrics shared by train.py and evaluate.py."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_recall_fscore_support)


def normalized_entropy(prob: np.ndarray) -> np.ndarray:
    k = prob.shape[1]
    ent = -(prob * np.log(np.clip(prob, 1e-12, None))).sum(axis=1)
    return ent / np.log(k)


def top2_margin(prob: np.ndarray) -> np.ndarray:
    s = np.sort(prob, axis=1)
    return s[:, -1] - s[:, -2]


def topk_accuracy(y: np.ndarray, prob: np.ndarray, k: int) -> float:
    topk = np.argsort(prob, axis=1)[:, -k:]
    return float(np.mean([yi in row for yi, row in zip(y, topk)]))


def expected_calibration_error(y: np.ndarray, prob: np.ndarray, n_bins: int = 15) -> float:
    conf = prob.max(axis=1)
    correct = (prob.argmax(axis=1) == y).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            ece += m.mean() * abs(correct[m].mean() - conf[m].mean())
    return float(ece)


def reliability_bins(y, prob, n_bins=10):
    conf = prob.max(axis=1)
    correct = (prob.argmax(axis=1) == y).astype(float)
    bins = np.linspace(0, 1, n_bins + 1)
    centers, accs, counts = [], [], []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (conf > lo) & (conf <= hi)
        centers.append((lo + hi) / 2)
        accs.append(float(correct[m].mean()) if m.any() else np.nan)
        counts.append(int(m.sum()))
    return np.array(centers), np.array(accs), np.array(counts)


def classification_metrics(y: np.ndarray, prob: np.ndarray, class_names: list) -> dict:
    y = np.asarray(y)
    pred = prob.argmax(axis=1)
    labels = list(range(len(class_names)))
    p, r, f, s = precision_recall_fscore_support(y, pred, labels=labels, zero_division=0)
    return {
        "n": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "macro_precision": float(p.mean()),
        "macro_recall": float(r.mean()),
        "macro_f1": float(f1_score(y, pred, labels=labels, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(y, pred, labels=labels, average="weighted", zero_division=0)),
        "top2_accuracy": topk_accuracy(y, prob, 2),
        "ece": expected_calibration_error(y, prob),
        "per_class": {
            c: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])}
            for i, c in enumerate(class_names)
        },
        "confusion_matrix": confusion_matrix(y, pred, labels=labels).tolist(),
    }


def bootstrap_ci(y, pred, metric_fn, n_boot=1000, seed=0, alpha=0.05):
    """Percentile bootstrap CI for any metric_fn(y, pred)."""
    rng = np.random.default_rng(seed)
    y, pred = np.asarray(y), np.asarray(pred)
    stats = []
    for _ in range(n_boot):
        idx = rng.integers(0, len(y), len(y))
        stats.append(metric_fn(y[idx], pred[idx]))
    lo, hi = np.percentile(stats, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(lo), float(hi)


def macro_f1_fn(n_classes):
    labels = list(range(n_classes))
    return lambda y, p: f1_score(y, p, labels=labels, average="macro", zero_division=0)
