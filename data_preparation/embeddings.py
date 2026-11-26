"""CLIP image embeddings for the near-duplicate search (method 6.2), with the project backbone.

Backbone: open_clip `ViT-B-32-quickgelu` / `openai`, evaluation transform, L2-normalized, fp32, CPU.
Runs offline (HF_HUB_OFFLINE=1): it only uses weights already in the local cache and never downloads.

    python -m data_preparation.embeddings --workdir <W>          # EmoSet from emoset.zip; Places365 from S3
Output: <W>/datasets/cache/clip_embeddings.npz with `feats` (N x 512 float32) and `paths` (= manifest image_path).
These embeddings only nominate candidate pairs; they never create a label.
"""
import argparse
import io
import os
import sys
import zipfile

ARCH, PRETRAINED = "ViT-B-32-quickgelu", "openai"


def load_model():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import open_clip
    import torch
    model, _, preprocess = open_clip.create_model_and_transforms(ARCH, pretrained=PRETRAINED)
    model.eval()
    return model, preprocess, torch


def encode(images_bytes, model, preprocess, torch, batch=64):
    from PIL import Image
    import numpy as np
    out = []
    for i in range(0, len(images_bytes), batch):
        ims = [Image.open(io.BytesIO(b)).convert("RGB") for b in images_bytes[i:i + batch]]
        with torch.no_grad():
            v = model.encode_image(torch.stack([preprocess(im) for im in ims])).float().numpy()
        out.append(v / np.linalg.norm(v, axis=1, keepdims=True))
        if (i // batch) % 20 == 0:
            print(f"  encoded {min(i + batch, len(images_bytes))}/{len(images_bytes)}", flush=True)
    return np.concatenate(out).astype(np.float32)


def emoset_paths_and_bytes(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        names = sorted(n for n in z.namelist() if n.startswith("emoset/") and n.lower().endswith(".jpg"))
        return [("datasets/images/" + n, z.read(n)) for n in names]


def places_from_s3(places_dir):
    """Re-use S3 (same backbone) after checking shape, norms and paths against S1."""
    import numpy as np
    from .common import read_csv
    z = np.load(os.path.join(places_dir, "data", "features", "places_clip.npz"))
    rows = read_csv(os.path.join(places_dir, "data", "places_manifest.csv"))
    if list(z["paths"]) != [r["path"] for r in rows]:
        raise SystemExit("STOP: places_clip.npz paths differ from places_manifest.csv")
    norms = np.linalg.norm(z["feats"], axis=1)
    if z["feats"].shape[1] != 512 or abs(norms - 1).max() > 1e-3:
        raise SystemExit("STOP: places_clip.npz is not 512-d and L2-normalized")
    paths = ["datasets/images/" + r["path"].replace("\\", "/")[len("data/"):] for r in rows]
    return paths, z["feats"].astype(np.float32)


def main(argv=None):
    import numpy as np
    from .common import PACKAGE_ROOT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workdir", default=PACKAGE_ROOT)
    ap.add_argument("--emoset-zip", default=None)
    ap.add_argument("--places-dir", default=None)
    a = ap.parse_args(argv)
    w = os.path.abspath(a.workdir)
    emoset_zip = a.emoset_zip or os.path.join(w, "external", "renad", "emoset.zip")
    places_dir = a.places_dir or os.path.join(w, "external", "shaden_visual")
    out = os.path.join(w, "datasets", "cache", "clip_embeddings.npz")
    paths, feats = [], []
    if os.path.isdir(places_dir):
        p, f = places_from_s3(places_dir)
        paths += p
        feats.append(f)
        print(f"places365: {len(p)} embeddings from S3")
    if os.path.exists(emoset_zip):
        items = emoset_paths_and_bytes(emoset_zip)
        model, preprocess, torch = load_model()
        feats.append(encode([b for _, b in items], model, preprocess, torch))
        paths += [p for p, _ in items]
        print(f"emoset: {len(items)} embeddings computed")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez(out, feats=np.concatenate(feats), paths=np.array(paths))
    print("saved", os.path.relpath(out, w).replace(os.sep, "/"), len(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
