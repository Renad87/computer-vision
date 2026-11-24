"""Integration contract for the app / backend.

    from ml.emotion.inference import analyze_emotions
    result = analyze_emotions(image_bytes)

Returns a dict with:
    emotion_suggestions          list of suggested emotions for the user to confirm/edit
    visual_affective_attributes  light / colour / contrast / warmth of the image
    uncertainty                  how sure the model is, and whether the image is ambiguous
    model_version                exact model used (for logging and evaluation)
plus `all_trained_scores` and `disclaimer` (extra, optional to use).

Sharing the encoder with Person 1 (visual understanding):
    If Person 1 already computed a CLIP image embedding with the SAME checkpoint
    (see config.DEFAULT_CLIP / the deployed head's model_name), pass it:
        analyze_emotions(image_bytes, clip_embedding=emb, embedding_model_name=name)
    and no second vision model is loaded.

Modes:
    shared     (default) frozen CLIP + trained head; can reuse Person 1's embedding
    finetuned  partially fine-tuned CLIP (set EMOTION_MODE=finetuned); needs its own encoder

CLI:
    python ml/emotion/inference.py path/to/image.jpg
"""
from __future__ import annotations

import io
import json
import os
import threading

import numpy as np

try:
    from . import config
    from .attributes import compute_attributes
    from .head import Head, l2_normalize, softmax
    from .policy import suggest_indices, uncertainty
except ImportError:  # executed as a script
    import config
    from attributes import compute_attributes
    from head import Head, l2_normalize, softmax
    from policy import suggest_indices, uncertainty


class EmotionAnalyzer:
    def __init__(self, artifacts_dir: str | None = None, mode: str | None = None, device: str | None = None):
        self.artifacts_dir = artifacts_dir or config.DEFAULT_ARTIFACTS_DIR
        self.mode = (mode or os.environ.get("EMOTION_MODE", "shared")).lower()
        if self.mode not in ("shared", "finetuned"):
            raise ValueError("mode must be 'shared' or 'finetuned'")
        self.device = device
        head_path = os.path.join(self.artifacts_dir, config.HEAD_FILENAME)
        if not os.path.exists(head_path):
            raise FileNotFoundError(f"{head_path} missing — run train.py first")
        self.head, extras = Head.load(head_path)
        self.class_text = extras["class_text"]
        self.derived_text = extras["derived_text"]
        self.logit_scale = float(extras["logit_scale"])
        self.model_name = str(extras["model_name"])
        self.classes = self.head.meta.get("trained_classes", config.TRAINED_CLASSES)
        self.model_version = self.head.meta.get("model_version", "unknown")
        self._clip = None
        self._ft = None
        self._lock = threading.Lock()
        if self.mode == "finetuned":
            ft_dir = os.path.join(self.artifacts_dir, config.FINETUNED_SUBDIR)
            with open(os.path.join(ft_dir, config.FT_META_FILENAME)) as f:
                self.model_version = json.load(f)["model_version"]

    # ------------------------------------------------------------ encoders
    def _clip_encoder(self):
        with self._lock:
            if self._clip is None:
                try:
                    from .encoders import ClipImageEncoder
                except ImportError:
                    from encoders import ClipImageEncoder
                self._clip = ClipImageEncoder(self.model_name, device=self.device)
        return self._clip

    def _finetuned(self):
        with self._lock:
            if self._ft is None:
                try:
                    from . import finetune
                except ImportError:
                    import finetune
                model, head, meta, device = finetune.load_finetuned(
                    os.path.join(self.artifacts_dir, config.FINETUNED_SUBDIR), self.device)
                self._ft = (model, head, meta, device, finetune.eval_transform(), finetune.forward_logits)
        return self._ft

    # ------------------------------------------------------------ main API
    def analyze(self, image_bytes: bytes, clip_embedding=None, embedding_model_name: str | None = None) -> dict:
        from PIL import Image
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        frozen_emb = None
        if clip_embedding is not None:
            if embedding_model_name and embedding_model_name != self.model_name:
                raise ValueError(f"Embedding from '{embedding_model_name}' but head trained on '{self.model_name}'")
            frozen_emb = l2_normalize(np.asarray(clip_embedding, dtype=np.float32).reshape(1, -1))
            if frozen_emb.shape[1] != self.class_text.shape[1]:
                raise ValueError(f"Embedding dim {frozen_emb.shape[1]} != expected {self.class_text.shape[1]}")

        if self.mode == "shared":
            if frozen_emb is None:
                frozen_emb = self._clip_encoder().encode([image])
            prob = self.head.proba(frozen_emb)[0]
        else:
            import torch
            model, head, meta, device, tfm, fwd = self._finetuned()
            with torch.no_grad():
                logits = fwd(model, head, tfm(image).unsqueeze(0).to(device)).float().cpu().numpy()
            prob = softmax(logits / meta["temperature"])[0]

        return self._build_output(prob, frozen_emb, image_bytes)

    def _build_output(self, prob, frozen_emb, image_bytes):
        suggestions = []
        for i in suggest_indices(prob):
            c = self.classes[i]
            suggestions.append({
                "label": c, "label_ar": config.ARABIC_NAMES[c],
                "project_emotion": config.PROJECT_EMOTION.get(c),
                "score": round(float(prob[i]), 4), "source": "trained",
            })

        # Derived, never-trained concepts (الحنين، الشوق، التأمل) — need a frozen CLIP embedding
        derived_note = None
        if frozen_emb is not None:
            all_text = np.concatenate([self.class_text, self.derived_text])
            share = softmax(self.logit_scale * frozen_emb @ all_text.T)[0][len(self.classes):]
            j = int(np.argmax(share))
            if share[j] >= config.DERIVED_MIN_SCORE:
                name = config.DERIVED_CLASSES[j]
                suggestions.append({
                    "label": name, "label_ar": config.DERIVED_EMOTIONS[name]["ar"],
                    "project_emotion": config.DERIVED_EMOTIONS[name]["ar"],
                    "score": round(float(share[j]), 4), "source": "zero_shot_unvalidated",
                    "note": "اقتراح دلالي من تشابه CLIP مع وصف نصي؛ غير مدرّب ولا مُقيّم على بيانات موسومة.",
                })
        else:
            derived_note = "derived suggestions unavailable in finetuned mode without a frozen CLIP embedding"

        unc = uncertainty(prob)
        unc["note_ar"] = ("الصورة تحتمل أكثر من قراءة عاطفية؛ عُرضت عدة اقتراحات." if unc["is_ambiguous"]
                          else "قراءة عاطفية واضحة نسبيًا.")
        if derived_note:
            unc["derived_note"] = derived_note

        return {
            "emotion_suggestions": suggestions,
            "visual_affective_attributes": compute_attributes(image_bytes),
            "uncertainty": unc,
            "model_version": self.model_version,
            "all_trained_scores": {c: round(float(p), 4) for c, p in zip(self.classes, prob)},
            "disclaimer": config.DISCLAIMER_AR,
        }


_ANALYZER = None
_ANALYZER_LOCK = threading.Lock()


def get_analyzer() -> EmotionAnalyzer:
    global _ANALYZER
    with _ANALYZER_LOCK:
        if _ANALYZER is None:
            _ANALYZER = EmotionAnalyzer()
    return _ANALYZER


def analyze_emotions(image_bytes: bytes, clip_embedding=None, embedding_model_name: str | None = None) -> dict:
    """The integration contract. See module docstring."""
    return get_analyzer().analyze(image_bytes, clip_embedding, embedding_model_name)


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        sys.exit("usage: python inference.py IMAGE")
    with open(sys.argv[1], "rb") as f:
        print(json.dumps(analyze_emotions(f.read()), ensure_ascii=False, indent=2))
