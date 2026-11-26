"""Temperature scaling (one scalar per softmax head), fitted on validation logits only.

T minimises the validation NLL of softmax(logits / T). The search is a bounded 1-D minimisation over
log T (scipy), so the result is deterministic. Accuracy is unchanged by construction (argmax is
invariant to T > 0); ECE, NLL and Brier are reported before and after.
"""
import numpy as np
from scipy.optimize import minimize_scalar

from . import metrics
from .heads import softmax

LOG_T_BOUNDS = (np.log(0.05), np.log(20.0))


def fit_temperature(val_logits, val_labels):
    val_labels = np.asarray(val_labels)

    def objective(log_t):
        return metrics.nll(val_labels, softmax(val_logits / np.exp(log_t)))

    result = minimize_scalar(objective, bounds=LOG_T_BOUNDS, method="bounded", options={"xatol": 1e-6})
    t = float(np.exp(result.x))
    at_bound = min(abs(result.x - b) for b in LOG_T_BOUNDS) < 1e-3
    return t, {"temperature": t, "val_nll_before": objective(0.0), "val_nll_after": float(result.fun),
               "at_search_bound": bool(at_bound), "bounds": [float(np.exp(b)) for b in LOG_T_BOUNDS]}


def calibration_table(labels, logits, temperature):
    labels = np.asarray(labels)
    before, after = softmax(logits), softmax(logits / temperature)
    return {stage: {"nll": metrics.nll(labels, p), "ece_15": metrics.ece(labels, p), "brier": metrics.brier(labels, p),
                    "accuracy": metrics.accuracy(labels, p.argmax(1))}
            for stage, p in (("before", before), ("after", after))}
