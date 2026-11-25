"""Classifier heads stored as plain numpy arrays.

Heads are trained with scikit-learn (train.py) but exported to .npz so that
inference needs no sklearn pickle and the forward pass is identical in
train / evaluate / inference.
"""
from __future__ import annotations

import json

import numpy as np
from scipy.optimize import minimize_scalar


def softmax(z: np.ndarray, axis: int = -1) -> np.ndarray:
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


def l2_normalize(x: np.ndarray, axis: int = -1) -> np.ndarray:
    return x / np.maximum(np.linalg.norm(x, axis=axis, keepdims=True), 1e-12)


class Head:
    """Linear or 1-hidden-layer MLP head with a standard scaler and temperature."""

    def __init__(self, kind, weights, biases, scaler_mean, scaler_scale,
                 temperature=1.0, meta=None):
        assert kind in ("linear", "mlp")
        self.kind = kind
        self.weights = [np.asarray(w, dtype=np.float32) for w in weights]
        self.biases = [np.asarray(b, dtype=np.float32) for b in biases]
        self.scaler_mean = np.asarray(scaler_mean, dtype=np.float32)
        self.scaler_scale = np.asarray(scaler_scale, dtype=np.float32)
        self.temperature = float(temperature)
        self.meta = dict(meta or {})

    # ---------------------------------------------------------------- forward
    def logits(self, x: np.ndarray) -> np.ndarray:
        x = (np.asarray(x, dtype=np.float32) - self.scaler_mean) / self.scaler_scale
        if self.kind == "linear":
            return x @ self.weights[0] + self.biases[0]
        h = np.maximum(x @ self.weights[0] + self.biases[0], 0.0)
        return h @ self.weights[1] + self.biases[1]

    def proba(self, x: np.ndarray, calibrated: bool = True) -> np.ndarray:
        t = self.temperature if calibrated else 1.0
        return softmax(self.logits(x) / t)

    # ----------------------------------------------------------- conversions
    @classmethod
    def from_sklearn(cls, model, scaler, meta=None):
        from sklearn.linear_model import LogisticRegression
        from sklearn.neural_network import MLPClassifier

        if isinstance(model, LogisticRegression):
            return cls("linear", [model.coef_.T], [model.intercept_],
                       scaler.mean_, scaler.scale_, meta=meta)
        if isinstance(model, MLPClassifier):
            if len(model.coefs_) != 2 or model.activation != "relu":
                raise ValueError("Only 1-hidden-layer ReLU MLPs are supported")
            return cls("mlp", model.coefs_, model.intercepts_,
                       scaler.mean_, scaler.scale_, meta=meta)
        raise TypeError(f"Unsupported model type {type(model)}")

    def folded_linear(self):
        """For a linear head, fold the scaler into W, b (used to init fine-tuning)."""
        assert self.kind == "linear"
        w = self.weights[0] / self.scaler_scale[:, None]
        b = self.biases[0] - (self.scaler_mean / self.scaler_scale) @ self.weights[0]
        return w, b

    # ------------------------------------------------------------------ io
    def save(self, path: str, extra_arrays: dict | None = None):
        arrays = {
            "kind": np.array(self.kind),
            "n_layers": np.array(len(self.weights)),
            "scaler_mean": self.scaler_mean,
            "scaler_scale": self.scaler_scale,
            "temperature": np.array(self.temperature, dtype=np.float64),
            "meta_json": np.array(json.dumps(self.meta, ensure_ascii=False)),
        }
        for i, (w, b) in enumerate(zip(self.weights, self.biases)):
            arrays[f"W{i}"] = w
            arrays[f"b{i}"] = b
        for k, v in (extra_arrays or {}).items():
            arrays[f"extra__{k}"] = np.asarray(v)
        np.savez_compressed(path, **arrays)

    @classmethod
    def load(cls, path: str):
        d = np.load(path, allow_pickle=False)
        n = int(d["n_layers"])
        head = cls(
            str(d["kind"]),
            [d[f"W{i}"] for i in range(n)],
            [d[f"b{i}"] for i in range(n)],
            d["scaler_mean"], d["scaler_scale"],
            float(d["temperature"]),
            json.loads(str(d["meta_json"])),
        )
        extras = {k[len("extra__"):]: d[k] for k in d.files if k.startswith("extra__")}
        return head, extras


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    """Temperature scaling (Guo et al., 2017): minimise validation NLL over T."""
    y = np.asarray(y)

    def nll(t):
        p = softmax(logits / t)
        return -np.mean(np.log(np.clip(p[np.arange(len(y)), y], 1e-12, None)))

    res = minimize_scalar(nll, bounds=(0.05, 20.0), method="bounded")
    return float(res.x)
