"""Strategy 2 — Fine-tuning by partial unfreezing (Unit 7 Part 3).

* Start from the feature-extraction linear head (freeze first, then unfreeze).
* Unfreeze only the last N transformer blocks of the CLIP vision tower,
  the final LayerNorm and the projection; everything else stays frozen.
* Low learning rate for the backbone (1e-5), higher for the head (1e-4).
* Augmentation: random resized crop + horizontal flip ONLY. No colour jitter,
  no brightness/contrast change: colour and light carry emotional meaning, so
  changing them could change the correct label.
* Only the unfrozen parameters are saved (~60 MB for 2 ViT-B/32 blocks), the rest is re-loaded
  from the public CLIP checkpoint at inference.
"""
from __future__ import annotations

import copy
import json
import os
import time

import numpy as np

try:
    from . import config
    from .head import fit_temperature, softmax
    from .metrics import classification_metrics
except ImportError:
    import config
    from head import fit_temperature, softmax
    from metrics import classification_metrics


def _transforms(train: bool):
    from torchvision import transforms as T
    norm = T.Normalize(config.CLIP_MEAN, config.CLIP_STD)
    if train:
        return T.Compose([
            T.RandomResizedCrop(224, scale=(0.7, 1.0), ratio=(0.9, 1.1),
                                interpolation=T.InterpolationMode.BICUBIC),
            T.RandomHorizontalFlip(),
            T.ToTensor(), norm])
    return T.Compose([T.Resize(224, interpolation=T.InterpolationMode.BICUBIC),
                      T.CenterCrop(224), T.ToTensor(), norm])


class _CachedImages:
    def __init__(self, cache_dir, paths, labels, transform):
        self.cache_dir, self.paths, self.labels, self.transform = cache_dir, paths, labels, transform

    def __len__(self):
        return len(self.paths)

    def __getitem__(self, i):
        from PIL import Image
        im = Image.open(os.path.join(self.cache_dir, str(self.paths[i]))).convert("RGB")
        return self.transform(im), int(self.labels[i])


def build_model(model_name, unfreeze_layers, n_classes, device):
    import torch
    from transformers import CLIPVisionModelWithProjection

    model = CLIPVisionModelWithProjection.from_pretrained(model_name)
    for p in model.parameters():
        p.requires_grad = False
    trainable = list(model.vision_model.encoder.layers[-unfreeze_layers:]) + [
        model.vision_model.post_layernorm, model.visual_projection]
    for m in trainable:
        for p in m.parameters():
            p.requires_grad = True
    head = torch.nn.Linear(model.config.projection_dim, n_classes)
    return model.to(device), head.to(device)


def forward_logits(model, head, pixels):
    import torch
    emb = model(pixel_values=pixels).image_embeds
    emb = torch.nn.functional.normalize(emb.float(), dim=-1)
    return head(emb)


def predict_logits(model, head, loader, device):
    import torch
    model.eval(); head.eval()
    out, ys = [], []
    with torch.no_grad(), torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
        for x, y in loader:
            out.append(forward_logits(model, head, x.to(device, non_blocking=True)).float().cpu().numpy())
            ys.append(y.numpy())
    return np.concatenate(out), np.concatenate(ys)


def run(model_name, train, val, init_head, cache_dir, out_dir, results_dir,
        epochs, unfreeze_layers, batch_size, seed):
    import torch
    from torch.utils.data import DataLoader

    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    os.makedirs(out_dir, exist_ok=True)
    n_classes = len(config.TRAINED_CLASSES)

    model, head = build_model(model_name, unfreeze_layers, n_classes, device)
    # init head from the feature-extraction linear head (scaler folded into W, b)
    w, b = init_head.folded_linear()
    with torch.no_grad():
        head.weight.copy_(torch.from_numpy(w.T.copy()))
        head.bias.copy_(torch.from_numpy(b.copy()))

    tr_ds = _CachedImages(cache_dir, train["paths"], train["labels"], _transforms(True))
    va_ds = _CachedImages(cache_dir, val["paths"], val["labels"], _transforms(False))
    workers = min(4, os.cpu_count() or 2)
    tr_dl = DataLoader(tr_ds, batch_size=batch_size, shuffle=True, num_workers=workers,
                       pin_memory=True, drop_last=True)
    va_dl = DataLoader(va_ds, batch_size=batch_size * 2, shuffle=False, num_workers=workers, pin_memory=True)

    backbone_params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW([
        {"params": backbone_params, "lr": config.FT_LR_BACKBONE},
        {"params": head.parameters(), "lr": config.FT_LR_HEAD},
    ], weight_decay=config.FT_WEIGHT_DECAY)
    total = epochs * len(tr_dl)
    warm = max(1, int(0.05 * total))
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + np.cos(np.pi * min(s, total) / total)))
    scaler = torch.amp.GradScaler(enabled=device.type == "cuda")
    loss_fn = torch.nn.CrossEntropyLoss(label_smoothing=config.FT_LABEL_SMOOTHING)

    # epoch 0 = the frozen starting point, so the gain from unfreezing is visible
    logits, yv = predict_logits(model, head, va_dl, device)
    start_f1 = classification_metrics(yv, softmax(logits), config.TRAINED_CLASSES)["macro_f1"]
    history = [{"epoch": 0, "train_loss": None, "val_macro_f1": start_f1}]
    print(f"  [finetune] epoch 0 (frozen start) val macro-F1={start_f1:.4f}", flush=True)
    best_f1, best_state, best_epoch = start_f1, None, 0

    for ep in range(1, epochs + 1):
        model.train(); head.train()
        t0, losses = time.time(), []
        for x, y in tr_dl:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                loss = loss_fn(forward_logits(model, head, x), y)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            losses.append(loss.item())
        logits, yv = predict_logits(model, head, va_dl, device)
        f1 = classification_metrics(yv, softmax(logits), config.TRAINED_CLASSES)["macro_f1"]
        history.append({"epoch": ep, "train_loss": float(np.mean(losses)), "val_macro_f1": f1,
                        "seconds": round(time.time() - t0, 1)})
        print(f"  [finetune] epoch {ep} loss={np.mean(losses):.4f} val macro-F1={f1:.4f} "
              f"({time.time() - t0:.0f}s)", flush=True)
        if f1 > best_f1:
            best_f1, best_epoch = f1, ep
            best_state = {
                "backbone": {n: p.detach().cpu().clone() for n, p in model.named_parameters() if p.requires_grad},
                "head": copy.deepcopy({k: v.cpu() for k, v in head.state_dict().items()}),
            }

    result = {"history": history, "best_epoch": best_epoch, "unfreeze_layers": unfreeze_layers,
              "epochs": epochs, "lr_backbone": config.FT_LR_BACKBONE, "lr_head": config.FT_LR_HEAD,
              "augmentation": "RandomResizedCrop(0.7-1.0) + HorizontalFlip; no colour/brightness changes"}
    _plot_history(history, os.path.join(results_dir, "finetune_curve.png"))

    if best_state is None:
        print("  [finetune] no epoch beat the frozen start — fine-tuned model NOT saved", flush=True)
        result["saved"] = False
        return result

    # reload best weights, calibrate temperature on validation
    model.load_state_dict(best_state["backbone"], strict=False)
    head.load_state_dict(best_state["head"])
    logits, yv = predict_logits(model, head, va_dl, device)
    temperature = fit_temperature(logits, yv)
    val_metrics = classification_metrics(yv, softmax(logits / temperature), config.TRAINED_CLASSES)

    torch.save(best_state, os.path.join(out_dir, config.FT_STATE_FILENAME))
    meta = {"base_model": model_name, "unfreeze_layers": unfreeze_layers, "temperature": temperature,
            "best_epoch": best_epoch, "val_macro_f1": val_metrics["macro_f1"],
            "trained_classes": config.TRAINED_CLASSES, "seed": seed,
            "model_version": f"emotion-emoset8-clip_ft{unfreeze_layers}-{model_name.split('/')[-1]}"}
    with open(os.path.join(out_dir, config.FT_META_FILENAME), "w") as f:
        json.dump(meta, f, indent=2)
    result.update({"saved": True, "temperature": temperature, "val_metrics": val_metrics})
    return result


def load_finetuned(ft_dir, device=None):
    """Rebuild base CLIP + saved unfrozen weights. Returns (model, head, meta, device)."""
    import torch
    with open(os.path.join(ft_dir, config.FT_META_FILENAME)) as f:
        meta = json.load(f)
    device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
    model, head = build_model(meta["base_model"], meta["unfreeze_layers"],
                              len(meta["trained_classes"]), device)
    state = torch.load(os.path.join(ft_dir, config.FT_STATE_FILENAME), map_location="cpu")
    missing, unexpected = model.load_state_dict(state["backbone"], strict=False)
    if unexpected:
        raise RuntimeError(f"Unexpected keys in fine-tuned state: {unexpected[:5]}")
    head.load_state_dict(state["head"])
    model.eval(); head.eval()
    return model, head, meta, device


def eval_loader(cache_dir, paths, labels, batch_size=128):
    from torch.utils.data import DataLoader
    ds = _CachedImages(cache_dir, paths, labels, _transforms(False))
    return DataLoader(ds, batch_size=batch_size, shuffle=False, num_workers=min(4, os.cpu_count() or 2))


def eval_transform():
    return _transforms(False)


def _plot_history(history, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ep = [h["epoch"] for h in history]
    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(ep, [h["val_macro_f1"] for h in history], "o-", color="#4C72B0", label="val macro-F1")
    ax1.set_xlabel("epoch (0 = frozen feature-extraction start)")
    ax1.set_ylabel("validation macro-F1")
    ax2 = ax1.twinx()
    tl = [(h["epoch"], h["train_loss"]) for h in history if h["train_loss"] is not None]
    if tl:
        ax2.plot(*zip(*tl), "s--", color="#C44E52", label="train loss")
        ax2.set_ylabel("train loss")
    ax1.set_title("Fine-tuning (partial unfreezing)")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
