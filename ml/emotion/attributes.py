"""Hand-crafted visual affective attributes (no model, numpy only).

These describe *how* an image looks (light, colour, contrast, warmth) rather
than what emotion it carries. They are used in two places:
  * returned to the app as `visual_affective_attributes`
  * evaluate.py studies how they differ across emotions and how much emotion
    they explain on their own (attribute-only classifier vs. CLIP).

The Arabic descriptor thresholds are simple heuristics, documented as such.
"""
from __future__ import annotations

import io
from typing import Union

import numpy as np
from PIL import Image

# Hasler & Süsstrunk (2003) colourfulness levels (metric M on 0-255 RGB)
_COLORFULNESS_LEVELS = [
    (15, "غير ملونة تقريبًا"),
    (33, "ألوان خفيفة"),
    (45, "ألوان متوسطة"),
    (59, "ألوان واضحة"),
    (82, "ألوان قوية"),
    (float("inf"), "ألوان زاهية جدًا"),
]


def load_rgb(image: Union[bytes, Image.Image, np.ndarray], max_side: int = 256) -> np.ndarray:
    """Return a float32 HxWx3 array in [0, 255], downscaled for speed."""
    if isinstance(image, (bytes, bytearray)):
        image = Image.open(io.BytesIO(image))
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image.astype(np.uint8))
    image = image.convert("RGB")
    w, h = image.size
    scale = max_side / max(w, h)
    if scale < 1:
        image = image.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.BILINEAR)
    return np.asarray(image, dtype=np.float32)


def numeric_attributes(rgb: np.ndarray) -> dict:
    """Five scalar attributes, all in roughly [0, 1] (warmth in [-1, 1])."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0.0)

    rg = r - g
    yb = 0.5 * (r + g) - b
    colorfulness_raw = float(
        np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)
    )

    return {
        "brightness": float(lum.mean()),
        "contrast": float(lum.std()),
        "saturation": float(sat.mean()),
        # 109 ≈ "extremely colourful" in Hasler & Süsstrunk; clip to [0, 1]
        "colorfulness": float(min(colorfulness_raw / 109.0, 1.0)),
        "warmth": float(np.clip((r - b).mean() / 255.0, -1.0, 1.0)),
        "_colorfulness_raw": colorfulness_raw,
    }


def dominant_colors(rgb: np.ndarray, k: int = 3) -> list:
    """Top-k colours after quantising each channel to 4 levels (64 bins)."""
    q = (rgb // 64).astype(np.int32)  # 0..3 per channel
    codes = q[..., 0] * 16 + q[..., 1] * 4 + q[..., 2]
    counts = np.bincount(codes.ravel(), minlength=64)
    total = counts.sum()
    out = []
    for code in np.argsort(counts)[::-1][:k]:
        if counts[code] == 0:
            break
        mask = codes == code
        mean = rgb[mask].mean(axis=0)
        out.append({
            "hex": "#{:02x}{:02x}{:02x}".format(*[int(round(v)) for v in mean]),
            "share": round(float(counts[code] / total), 3),
        })
    return out


def describe(attrs: dict) -> dict:
    """Arabic descriptors (heuristic thresholds)."""
    b = attrs["brightness"]
    light = "معتمة" if b < 0.35 else ("مشرقة" if b > 0.65 else "إضاءة متوسطة")
    w = attrs["warmth"]
    tone = "دافئة" if w > 0.05 else ("باردة" if w < -0.05 else "محايدة")
    c = attrs["contrast"]
    contrast = "تباين منخفض" if c < 0.15 else ("تباين عالٍ" if c > 0.28 else "تباين متوسط")
    raw = attrs["_colorfulness_raw"]
    colour = next(label for thr, label in _COLORFULNESS_LEVELS if raw < thr)
    return {"lighting": light, "tone": tone, "contrast": contrast, "colorfulness": colour}


def compute_attributes(image: Union[bytes, Image.Image, np.ndarray]) -> dict:
    """Full attribute record returned by inference."""
    rgb = load_rgb(image)
    num = numeric_attributes(rgb)
    desc = describe(num)
    num.pop("_colorfulness_raw")
    return {
        **{k: round(v, 4) for k, v in num.items()},
        "dominant_colors": dominant_colors(rgb),
        "descriptors_ar": desc,
        "note": "خصائص بصرية محسوبة مباشرة من البكسلات؛ الأوصاف العربية مبنية على عتبات تقريبية.",
    }


def attribute_vector(image: Union[bytes, Image.Image, np.ndarray]) -> np.ndarray:
    """Numeric vector in config.ATTRIBUTE_KEYS order (used during feature extraction)."""
    num = numeric_attributes(load_rgb(image))
    return np.array(
        [num["brightness"], num["contrast"], num["saturation"], num["colorfulness"], num["warmth"]],
        dtype=np.float32,
    )
