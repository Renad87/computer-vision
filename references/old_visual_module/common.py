"""Shared helpers: paths, taxonomy, CLIP backbone (shared with the emotion module), feature cache."""
import csv
import json
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path

import numpy as np
import torch
from PIL import Image

# Stop ultralytics from pip-installing packages at runtime (it silently upgraded Pillow once).
os.environ.setdefault("YOLO_AUTOINSTALL", "false")

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
WEIGHTS = ROOT / "weights"
RESULTS = ROOT / "results"
FEATURES = DATA / "features"

CLIP_ARCH = "ViT-B-32-quickgelu"  # OpenAI weights were trained with QuickGELU
CLIP_PRETRAINED = "openai"          # the original OpenAI CLIP weights (github.com/openai/CLIP)
YOLO_WEIGHTS = "yolov8n.pt"         # COCO-80 detector, same as course notebook CV_5
MODEL_VERSION = "visual-1.0.0+clip-vitb32-openai+scene16bg+tags34+yolov8n"

TEMPLATES = ["a photo of {}.", "a picture of {}.", "an image of {}.", "a photograph showing {}."]

torch.set_num_threads(max(1, os.cpu_count() or 1))


def load_taxonomy():
    return json.loads((ROOT / "taxonomy.json").read_text(encoding="utf-8"))


def read_csv(path):
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------- CLIP
@lru_cache(maxsize=1)
def get_clip():
    import open_clip
    model, _, preprocess = open_clip.create_model_and_transforms(CLIP_ARCH, pretrained=CLIP_PRETRAINED)
    model.eval()
    tokenizer = open_clip.get_tokenizer(CLIP_ARCH)
    return model, preprocess, tokenizer


def _l2(x):
    return x / np.linalg.norm(x, axis=-1, keepdims=True).clip(min=1e-8)


@torch.no_grad()
def clip_encode_images(images, batch_size=64):
    """images: list of PIL images -> (N, 512) L2-normalised float32."""
    model, preprocess, _ = get_clip()
    out = []
    for i in range(0, len(images), batch_size):
        x = torch.stack([preprocess(im.convert("RGB")) for im in images[i:i + batch_size]])
        out.append(model.encode_image(x).float().numpy())
    return _l2(np.concatenate(out)) if out else np.zeros((0, 512), np.float32)


@torch.no_grad()
def clip_encode_text_ensemble(phrases, templates=TEMPLATES):
    """Average the embeddings of every phrase x template, then re-normalise -> (512,)."""
    model, _, tokenizer = get_clip()
    texts = [t.format(p) for p in phrases for t in templates]
    e = _l2(model.encode_text(tokenizer(texts)).float().numpy())
    return _l2(e.mean(0))


def embed_image(img):
    """Public helper for teammates: one PIL image -> 512-d CLIP embedding (shared backbone)."""
    return clip_encode_images([img])[0]


# ---------------------------------------------------------------- MobileNetV2 (course baseline)
@lru_cache(maxsize=1)
def get_mnv2():
    import torchvision
    w = torchvision.models.MobileNet_V2_Weights.IMAGENET1K_V2
    m = torchvision.models.mobilenet_v2(weights=w)
    m.classifier = torch.nn.Identity()
    m.eval()
    return m, w.transforms()


@torch.no_grad()
def mnv2_encode_images(images, batch_size=64):
    m, tf = get_mnv2()
    out = []
    for i in range(0, len(images), batch_size):
        x = torch.stack([tf(im.convert("RGB")) for im in images[i:i + batch_size]])
        out.append(m(x).numpy())
    return np.concatenate(out).astype(np.float32)


# ---------------------------------------------------------------- YOLOv8 object detector
@lru_cache(maxsize=1)
def get_yolo():
    from ultralytics import YOLO
    WEIGHTS.mkdir(parents=True, exist_ok=True)
    return YOLO(str(WEIGHTS / YOLO_WEIGHTS))


def yolo_detect(images, conf=0.1):
    """images: list of PIL -> list (per image) of detections with normalised xyxy boxes."""
    model = get_yolo()
    out = []
    for im in images:
        im = im.convert("RGB")
        w, h = im.size
        r = model.predict(np.asarray(im)[:, :, ::-1], conf=conf, verbose=False)[0]  # BGR like cv2
        dets = []
        for b in r.boxes:
            x1, y1, x2, y2 = b.xyxy[0].tolist()
            dets.append({"name": r.names[int(b.cls[0])], "conf": round(float(b.conf[0]), 4),
                         "box": [round(x1 / w, 4), round(y1 / h, 4), round(x2 / w, 4), round(y2 / h, 4)]})
        out.append(dets)
    return out


def cached_yolo(name, paths):
    FEATURES.mkdir(parents=True, exist_ok=True)
    f = FEATURES / f"{name}_yolo.json"
    if f.exists():
        d = json.loads(f.read_text())
        if d["paths"] == list(paths):
            return d["dets"]
    dets = []
    for i in range(0, len(paths), 64):
        dets += yolo_detect([_load(p) for p in paths[i:i + 64]])
        print(f"  [yolo] {name}: {min(i + 64, len(paths))}/{len(paths)}", flush=True)
    f.write_text(json.dumps({"paths": list(paths), "dets": dets}))
    return dets


# ---------------------------------------------------------------- feature cache
def _load(path):
    return Image.open(ROOT / path).convert("RGB")


def cached_features(name, paths, backbone="clip", chunk=256):
    """Compute (or load) features for a list of relative image paths."""
    FEATURES.mkdir(parents=True, exist_ok=True)
    f = FEATURES / f"{name}_{backbone}.npz"
    feats, start = [], 0
    if f.exists():
        z = np.load(f, allow_pickle=False)
        old = list(z["paths"])
        if old == list(paths):
            return z["feats"]
        if old == list(paths[:len(old)]):  # manifest was extended: reuse the cached prefix
            feats, start = [z["feats"]], len(old)
    enc = clip_encode_images if backbone == "clip" else mnv2_encode_images
    with ThreadPoolExecutor(8) as ex:
        for i in range(start, len(paths), chunk):
            imgs = list(ex.map(_load, paths[i:i + chunk]))
            feats.append(enc(imgs))
            print(f"  [{backbone}] {name}: {min(i + chunk, len(paths))}/{len(paths)}", flush=True)
    feats = np.concatenate(feats)
    np.savez_compressed(f, feats=feats, paths=np.array(paths))
    return feats


def softmax(z, axis=-1):
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)
