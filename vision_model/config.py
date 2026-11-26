"""Paths and constants for PoetryVisionNet (Stage 1: frozen CLIP ViT-B/32 + linear heads).

CLIP weights are read offline from a Hugging Face cache (PV_HF_CACHE, default ~/.cache/huggingface/hub) and
sha256-checked. The reused scene and tag heads ship in artifacts/heads/reused/ (override with PV_REUSED_HEADS).
"""
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OLD_PROJECT = os.environ.get("PV_OLD_PROJECT", os.path.join(REPO, "external", "poetry_vision_old"))
_OLD_HF = os.path.join(OLD_PROJECT, "product", "models", "hf")
HF_CACHE = os.environ.get("PV_HF_CACHE") or (
    _OLD_HF if os.path.isdir(_OLD_HF) else os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub"))
OLD_VISUAL = os.path.join(OLD_PROJECT, "product", "vendor", "visual_module", "ml", "visual")
_REUSED = os.path.join(REPO, "artifacts", "heads", "reused")
OLD_WEIGHTS = os.environ.get("PV_REUSED_HEADS") or (_REUSED if os.path.isdir(_REUSED) else os.path.join(OLD_VISUAL, "weights"))
EMOSET_ZIP = os.environ.get("PV_EMOSET_ZIP", os.path.join(REPO, "external", "renad", "emoset.zip"))
ARTIFACTS = os.path.join(REPO, "artifacts")
FEATURES_DIR = os.path.join(ARTIFACTS, "features")
HEADS_DIR = os.path.join(ARTIFACTS, "heads")
REPORTS_DIR = os.path.join(REPO, "evaluation", "vision")
EMOTION_HEAD_PATH = os.path.join(HEADS_DIR, "emotion_head_v1.npz")
SCENE_CALIB_PATH = os.path.join(HEADS_DIR, "scene_calibration_v1.json")
MODEL_CARD_PATH = os.path.join(ARTIFACTS, "model_card_v1.json")

MODEL_ID = "poetry-vision-net"
CLIP_ARCH = "ViT-B-32-quickgelu"
CLIP_PRETRAINED = "openai"
CLIP_LIBRARY_VERSION = "4.2.2"
HF_REPO = "timm/vit_base_patch32_clip_224.openai"
HF_REVISION = "a6f597a30f7b82c51704746581f9a4e41421e878"
WEIGHTS_FILE = "open_clip_model.safetensors"
WEIGHTS_SHA256 = "e6d1bd7789aa45192b3bf90570a789b478bae1b74ebcce7eddd908e83a2b7c31"
EMBEDDING_DIM = 512
IMAGE_SIZE = 224
MEAN = (0.48145466, 0.4578275, 0.40821073)
STD = (0.26862954, 0.26130258, 0.27577711)
MIN_IMAGE_SIDE = 32

# Reused heads from the previous visual module (read-only).
OLD_SCENE_HEAD = os.path.join(OLD_WEIGHTS, "scene_head_clip.npz")
OLD_TAG_HEAD = os.path.join(OLD_WEIGHTS, "tag_heads.npz")
OLD_CALIBRATION = os.path.join(OLD_WEIGHTS, "calibration.json")
OLD_SCENE_HEAD_SHA256 = "f39e083cfa639616563a0cd53f62fa9139558c991b9a0f44b6f0cef1c45cd376"
OLD_TAG_HEAD_SHA256 = "a94f7d145af7f4789383c9ba5583d382842ec53142fdbf457573118a9be5384a"
OLD_CALIBRATION_SHA256 = "873497a35cbae6486988c7781e7ca6a4350dd239948d4c4cdbc01a521978d1df"
OLD_SCENE_OTHER = "__other__"

EMOTION_AMBIGUITY_MARGIN = 0.15
SCENE_UNCERTAIN_MARGIN = 0.10
SEED = 42


def weights_path():
    folder = "models--" + HF_REPO.replace("/", "--")
    return os.path.join(HF_CACHE, folder, "snapshots", HF_REVISION, WEIGHTS_FILE)


def offline_env():
    """Environment for loading CLIP without any network access. Must be applied before importing open_clip."""
    os.environ["HF_HUB_CACHE"] = HF_CACHE
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
