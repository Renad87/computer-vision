"""Classification and calibration metrics (NumPy). Bootstrap intervals are seeded and resample images."""
import numpy as np


def confusion(y_true, y_pred, n_classes):
    m = np.zeros((n_classes, n_classes), np.int64)
    np.add.at(m, (np.asarray(y_true), np.asarray(y_pred)), 1)
    return m


def per_class_f1(y_true, y_pred, n_classes):
    m = confusion(y_true, y_pred, n_classes)
    tp = np.diag(m).astype(float)
    precision = np.divide(tp, m.sum(0), out=np.zeros(n_classes), where=m.sum(0) > 0)
    recall = np.divide(tp, m.sum(1), out=np.zeros(n_classes), where=m.sum(1) > 0)
    f1 = np.divide(2 * precision * recall, precision + recall, out=np.zeros(n_classes), where=(precision + recall) > 0)
    return precision, recall, f1


def macro_f1(y_true, y_pred, n_classes):
    return float(per_class_f1(y_true, y_pred, n_classes)[2].mean())


def accuracy(y_true, y_pred):
    return float((np.asarray(y_true) == np.asarray(y_pred)).mean())


def top_k_accuracy(y_true, probs, k):
    top = np.argsort(-probs, axis=1)[:, :k]
    return float((top == np.asarray(y_true)[:, None]).any(1).mean())


def nll(y_true, probs, eps=1e-12):
    return float(-np.log(np.clip(probs[np.arange(len(y_true)), y_true], eps, 1.0)).mean())


def brier(y_true, probs):
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(y_true)), y_true] = 1.0
    return float(((probs - onehot) ** 2).sum(1).mean())


def ece(y_true, probs, n_bins=15):
    """Expected calibration error of the top-1 confidence, equal-width bins."""
    conf, pred = probs.max(1), probs.argmax(1)
    correct = (pred == np.asarray(y_true)).astype(float)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (conf > lo) & (conf <= hi)
        if mask.any():
            total += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(total)


def bootstrap_ci(y_true, y_pred, fn, n_boot=1000, seed=42, alpha=0.05):
    rng = np.random.default_rng(seed)
    y_true, y_pred = np.asarray(y_true), np.asarray(y_pred)
    n = len(y_true)
    stats = np.array([fn(y_true[idx], y_pred[idx]) for idx in (rng.integers(0, n, n) for _ in range(n_boot))])
    return float(np.quantile(stats, alpha / 2)), float(np.quantile(stats, 1 - alpha / 2))


def classification_report(y_true, probs, class_ids, n_boot=1000, seed=42):
    y_true = np.asarray(y_true)
    pred = probs.argmax(1)
    k = len(class_ids)
    precision, recall, f1 = per_class_f1(y_true, pred, k)
    return {
        "n": int(len(y_true)),
        "accuracy": accuracy(y_true, pred),
        "accuracy_ci95": bootstrap_ci(y_true, pred, accuracy, n_boot, seed),
        "macro_f1": float(f1.mean()),
        "macro_f1_ci95": bootstrap_ci(y_true, pred, lambda a, b: macro_f1(a, b, k), n_boot, seed),
        "top2_accuracy": top_k_accuracy(y_true, probs, 2),
        "nll": nll(y_true, probs), "ece_15": ece(y_true, probs), "brier": brier(y_true, probs),
        "per_class": {cid: {"precision": float(precision[i]), "recall": float(recall[i]), "f1": float(f1[i]),
                            "support": int((y_true == i).sum())} for i, cid in enumerate(class_ids)},
        "confusion": confusion(y_true, pred, k).tolist(),
        "bootstrap": {"resamples": n_boot, "seed": seed, "unit": "image"},
    }
