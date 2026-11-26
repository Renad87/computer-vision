"""Linear heads on the shared 512-d CLIP embedding (Stage 1). NumPy only at inference time."""
import json
import os

import numpy as np

from . import config
from .backbone import sha256_file


def softmax(z, axis=-1):
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


class LinearHead:
    """logits = x @ W.T + b. Softmax heads divide logits by `temperature` when calibrated."""

    def __init__(self, name, output_layer, output_ids, W, b, activation, origin, source_file=None, trained_on=None,
                 temperature=None, exposed_ids=None):
        W, b = np.asarray(W, np.float32), np.asarray(b, np.float32)
        if W.shape != (len(output_ids), config.EMBEDDING_DIM) or b.shape != (len(output_ids),):
            raise ValueError(f"head {name}: W {W.shape} / b {b.shape} do not match {len(output_ids)} outputs")
        self.name, self.output_layer, self.output_ids = name, output_layer, list(output_ids)
        self.W, self.b, self.activation, self.origin = W, b, activation, origin
        self.source_file, self.trained_on, self.temperature = source_file, trained_on, temperature
        self.exposed_ids = exposed_ids

    def logits(self, x):
        return np.asarray(x, np.float32) @ self.W.T + self.b

    def probs(self, x, calibrated=True):
        if self.activation != "softmax":
            raise ValueError(f"head {self.name} is not a softmax head")
        z = self.logits(x)
        if calibrated and self.temperature is not None:
            z = z / self.temperature
        return softmax(z)

    def card(self):
        entry = {"name": self.name, "input": "embedding", "output_layer": self.output_layer,
                 "output_ids": self.output_ids}
        if self.exposed_ids is not None:
            entry["exposed_ids"] = list(self.exposed_ids)
        entry.update({"activation": self.activation, "in_dim": config.EMBEDDING_DIM, "out_dim": len(self.output_ids),
                      "params": int(self.W.size + self.b.size), "origin": self.origin, "source_file": self.source_file,
                      "trained_on": ({"manifest_sha256": self.trained_on, "split": "train"}
                                     if isinstance(self.trained_on, str) else self.trained_on),
                      "temperature": self.temperature,
                      "calibrated": self.temperature is not None})
        return entry

    def save(self, path, extra=None):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        meta = {"name": self.name, "output_layer": self.output_layer, "activation": self.activation,
                "origin": self.origin, "source_file": self.source_file, "trained_on": self.trained_on,
                "temperature": self.temperature, "exposed_ids": self.exposed_ids, **(extra or {})}
        np.savez(path, W=self.W, b=self.b, output_ids=np.array(self.output_ids), meta=np.array(json.dumps(meta)))

    @classmethod
    def load(cls, path):
        with np.load(path, allow_pickle=False) as d:
            meta = json.loads(str(d["meta"]))
            return cls(meta["name"], meta["output_layer"], [str(x) for x in d["output_ids"]], d["W"], d["b"],
                       meta["activation"], meta["origin"], meta.get("source_file"), meta.get("trained_on"),
                       meta.get("temperature"), meta.get("exposed_ids"))


def _check(path, expected_sha):
    actual = sha256_file(path)
    if actual != expected_sha:
        raise RuntimeError(f"{path}: sha256 {actual} != expected {expected_sha}")


def load_old_scene_head(taxonomy):
    """Shaden's scene head (16 scenes + background trained as scene.other), reordered by taxonomy class order."""
    _check(config.OLD_SCENE_HEAD, config.OLD_SCENE_HEAD_SHA256)
    with np.load(config.OLD_SCENE_HEAD, allow_pickle=False) as d:
        classes = [str(c) for c in d["classes"]]
        W, b = d["W"], d["b"]
    ids = ["scene.other" if c == config.OLD_SCENE_OTHER else f"scene.{c}" for c in classes]
    order = taxonomy.class_order["scene"]
    if sorted(ids) != sorted(order):
        raise RuntimeError(f"old scene head classes {ids} do not cover the taxonomy scene order")
    idx = [ids.index(i) for i in order]
    return LinearHead("scene", "scene", order, W[idx], b[idx], "softmax", "reused_visual_module_v1",
                      source_file="visual_module/ml/visual/weights/scene_head_clip.npz")


def load_old_tag_head(taxonomy):
    _check(config.OLD_TAG_HEAD, config.OLD_TAG_HEAD_SHA256)
    with np.load(config.OLD_TAG_HEAD, allow_pickle=False) as d:
        ids = [f"tag.{t}" for t in d["ids"]]
        W, b = d["W"], d["b"]
    order = taxonomy.class_order["tag"]
    if sorted(ids) != sorted(order):
        raise RuntimeError("old tag head ids do not cover the taxonomy tag order")
    idx = [ids.index(i) for i in order]
    return LinearHead("tags", "tag", order, W[idx], b[idx], "linear_threshold", "reused_visual_module_v1",
                      source_file="visual_module/ml/visual/weights/tag_heads.npz",
                      exposed_ids=list(taxonomy.exposed_tags))


def load_old_calibration():
    """Thresholds from the previous visual module: scene rejection threshold and one threshold per tag."""
    _check(config.OLD_CALIBRATION, config.OLD_CALIBRATION_SHA256)
    with open(config.OLD_CALIBRATION, encoding="utf-8") as fh:
        calib = json.load(fh)
    return {"scene_supported": float(calib["scene_reject_threshold"]),
            "scene_tpr_target": float(calib["scene_reject_tpr"]),
            "tags": {f"tag.{t}": float(v["threshold"]) for t, v in calib["tags"].items()}}
