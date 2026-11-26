"""Frozen CLIP ViT-B/32 (OpenAI weights) image encoder, loaded offline from the local cache."""
import functools
import hashlib
import io
import os

from . import config

config.offline_env()

import numpy as np  # noqa: E402
import torch  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402


class ImageError(ValueError):
    """Raised for bytes that cannot be used as an image. `code` follows inference_output.error.code."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def pick_device(name="auto"):
    if name == "auto":
        return "mps" if torch.backends.mps.is_available() else "cpu"
    if name == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("MPS requested but not available")
    return name


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


@functools.lru_cache(maxsize=1)
def verify_weights():
    path = config.weights_path()
    if not os.path.isfile(path):
        raise FileNotFoundError(f"CLIP weights not found at {path} (download it and set PV_HF_CACHE; see README)")
    actual = sha256_file(path)
    if actual != config.WEIGHTS_SHA256:
        raise RuntimeError(f"CLIP weights sha256 {actual} != expected {config.WEIGHTS_SHA256}")
    return path


@functools.lru_cache(maxsize=4)
def load_clip(device="cpu", check_weights=True):
    """Returns (model, preprocess). The model is in eval mode with every parameter frozen."""
    import open_clip

    if check_weights:
        verify_weights()
    if open_clip.__version__ != config.CLIP_LIBRARY_VERSION:
        raise RuntimeError(f"open_clip {open_clip.__version__} != pinned {config.CLIP_LIBRARY_VERSION}")
    model, _, preprocess = open_clip.create_model_and_transforms(config.CLIP_ARCH, pretrained=config.CLIP_PRETRAINED)
    model = model.to(device).eval()
    for param in model.parameters():
        param.requires_grad_(False)
    return model, preprocess


def decode_image(data):
    """bytes -> RGB PIL image with EXIF orientation applied. Raises ImageError."""
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:  # noqa: BLE001
        raise ImageError("invalid_image", f"could not decode image: {type(exc).__name__}") from exc
    if img.format not in (None, "JPEG", "PNG", "WEBP", "BMP", "GIF", "MPO"):
        raise ImageError("unsupported_format", f"unsupported image format {img.format}")
    img = ImageOps.exif_transpose(img).convert("RGB")
    if min(img.size) < config.MIN_IMAGE_SIDE:
        raise ImageError("too_small", f"image side below {config.MIN_IMAGE_SIDE} px")
    return img


class ClipEncoder:
    """Shared feature extractor: images -> (N, 512) float32, L2-normalised."""

    def __init__(self, device="auto", check_weights=True):
        self.device = pick_device(device)
        self.model, self.preprocess = load_clip(self.device, check_weights)

    @torch.no_grad()
    def encode_tensors(self, batch):
        feats = self.model.encode_image(batch.to(self.device)).float()
        feats = feats / feats.norm(dim=-1, keepdim=True).clamp_min(1e-8)
        return feats.cpu().numpy().astype(np.float32)

    def encode_images(self, images, batch_size=64):
        out = []
        for i in range(0, len(images), batch_size):
            batch = torch.stack([self.preprocess(im) for im in images[i:i + batch_size]])
            out.append(self.encode_tensors(batch))
        return np.concatenate(out) if out else np.zeros((0, config.EMBEDDING_DIM), np.float32)
