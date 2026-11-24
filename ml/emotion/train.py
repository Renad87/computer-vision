"""Step 2 — Training.

Follows the two transfer-learning strategies of Unit 7 Part 3, in order:

  0. Zero-shot baseline     : CLIP with text prompts, no training at all
  1. Feature extraction     : backbone frozen, only a new classifier head trained
       - CLIP  + Logistic Regression   (linear head)
       - CLIP  + MLP                   (1 hidden layer, ReLU)
       - ResNet50 (ImageNet) + Logistic Regression   (classic CNN comparison)
  2. Fine-tuning (--finetune): unfreeze the last CLIP blocks with a low LR,
       head initialised from step 1 ("always freeze first").

Model selection uses the validation split only. The test split is never read
here (evaluate.py is the only script that touches it).

Usage:
    python ml/emotion/train.py                 # steps 0-1
    python ml/emotion/train.py --finetune      # steps 0-2
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from head import Head, fit_temperature, softmax  # noqa: E402
from metrics import classification_metrics  # noqa: E402

LR_GRID = [0.01, 0.1, 1.0]
MLP_ALPHA_GRID = [1e-4, 1e-3]


def load_split(features_dir, split):
    path = os.path.join(features_dir, f"{split}.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found — run prepare_features.py first")
    return dict(np.load(path, allow_pickle=False))


def load_text(features_dir):
    return dict(np.load(os.path.join(features_dir, config.TEXT_EMB_FILENAME), allow_pickle=False))


def zero_shot_proba(clip_feats, class_text, logit_scale):
    return softmax(float(logit_scale) * clip_feats @ class_text.T)


def fit_candidates(name, Xtr, ytr, Xva, yva, kind, seed):
    """Grid-search one head type on the validation split. Returns (best, trials)."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.neural_network import MLPClassifier
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler().fit(Xtr)
    Xtr_s, Xva_s = scaler.transform(Xtr), scaler.transform(Xva)
    trials, best = [], None
    grid = LR_GRID if kind == "linear" else MLP_ALPHA_GRID
    for hp in grid:
        t0 = time.time()
        if kind == "linear":
            model = LogisticRegression(C=hp, max_iter=3000, class_weight="balanced")
            hp_desc = {"C": hp}
        else:
            model = MLPClassifier(hidden_layer_sizes=(512,), alpha=hp, batch_size=256,
                                  learning_rate_init=1e-3, max_iter=200, early_stopping=True,
                                  n_iter_no_change=10, random_state=seed)
            hp_desc = {"alpha": hp, "hidden": 512}
        model.fit(Xtr_s, ytr)
        head = Head.from_sklearn(model, scaler)
        m = classification_metrics(yva, head.proba(Xva, calibrated=False), config.TRAINED_CLASSES)
        trial = {"candidate": name, **hp_desc, "val_macro_f1": m["macro_f1"],
                 "val_accuracy": m["accuracy"], "fit_seconds": round(time.time() - t0, 1)}
        trials.append(trial)
        print(f"  {name} {hp_desc}: val macro-F1={m['macro_f1']:.4f} acc={m['accuracy']:.4f}", flush=True)
        if best is None or m["macro_f1"] > best["trial"]["val_macro_f1"]:
            best = {"head": head, "model": model, "trial": trial}
    # temperature scaling on validation logits
    best["head"].temperature = fit_temperature(best["head"].logits(Xva), yva)
    best["val_metrics"] = classification_metrics(yva, best["head"].proba(Xva), config.TRAINED_CLASSES)
    return best, trials


def plot_selection(trials, zs_f1, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["CLIP zero-shot"] + [
        f"{t['candidate']}\n" + ",".join(f"{k}={v}" for k, v in t.items()
                                         if k in ("C", "alpha")) for t in trials]
    vals = [zs_f1] + [t["val_macro_f1"] for t in trials]
    fig, ax = plt.subplots(figsize=(max(8, len(vals) * 1.1), 4.5))
    bars = ax.bar(range(len(vals)), vals, color=["#999999"] + ["#4C72B0"] * len(trials))
    ax.set_xticks(range(len(vals)), labels, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("validation macro-F1")
    ax.set_title("Model selection on the validation split")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.3f}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def plot_mlp_curve(model, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax1 = plt.subplots(figsize=(7, 4))
    ax1.plot(model.loss_curve_, label="train loss", color="#C44E52")
    ax1.set_xlabel("epoch")
    ax1.set_ylabel("train loss")
    if getattr(model, "validation_scores_", None):
        ax2 = ax1.twinx()
        ax2.plot(model.validation_scores_, label="internal val accuracy", color="#4C72B0")
        ax2.set_ylabel("internal validation accuracy")
    ax1.set_title("CLIP + MLP head — training curve")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features_dir", default=config.DEFAULT_FEATURES_DIR)
    ap.add_argument("--cache_dir", default=config.DEFAULT_CACHE_DIR)
    ap.add_argument("--artifacts_dir", default=config.DEFAULT_ARTIFACTS_DIR)
    ap.add_argument("--results_dir", default=config.DEFAULT_RESULTS_DIR)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--finetune", action="store_true", help="also run Strategy 2 (partial unfreezing)")
    ap.add_argument("--ft_epochs", type=int, default=config.FT_EPOCHS)
    ap.add_argument("--ft_unfreeze_layers", type=int, default=config.FT_UNFREEZE_LAYERS)
    ap.add_argument("--ft_batch", type=int, default=config.FT_BATCH)
    args = ap.parse_args()

    np.random.seed(args.seed)
    heads_dir = os.path.join(args.artifacts_dir, config.HEADS_SUBDIR)
    for d in (args.artifacts_dir, heads_dir, args.results_dir):
        os.makedirs(d, exist_ok=True)

    tr, va = load_split(args.features_dir, "train"), load_split(args.features_dir, "val")
    text = load_text(args.features_dir)
    model_name = str(text["model_name"])
    ytr, yva = tr["labels"], va["labels"]
    print(f"train={len(ytr):,}  val={len(yva):,}  backbone={model_name}", flush=True)

    report = {
        "created": dt.datetime.now().isoformat(timespec="seconds"),
        "seed": args.seed,
        "clip_model": model_name,
        "classes": config.TRAINED_CLASSES,
        "n_train": int(len(ytr)), "n_val": int(len(yva)),
        "train_per_class": np.bincount(ytr, minlength=8).tolist(),
        "val_per_class": np.bincount(yva, minlength=8).tolist(),
    }

    # ---- Step 0: zero-shot baseline ------------------------------------
    zs = classification_metrics(yva, zero_shot_proba(va["clip"], text["class_text"], text["logit_scale"]),
                                config.TRAINED_CLASSES)
    report["zero_shot_val"] = zs
    print(f"Zero-shot CLIP: val macro-F1={zs['macro_f1']:.4f} acc={zs['accuracy']:.4f}", flush=True)

    # ---- Step 1: feature extraction (frozen backbones) -----------------
    all_trials, bests = [], {}
    for name, feat_key, kind in [("clip_linear", "clip", "linear"),
                                 ("clip_mlp", "clip", "mlp"),
                                 ("resnet_linear", "resnet", "linear")]:
        if feat_key not in tr:
            print(f"  (skipping {name}: no '{feat_key}' features)")
            continue
        best, trials = fit_candidates(name, tr[feat_key], ytr, va[feat_key], yva, kind, args.seed)
        best["head"].meta = {"candidate": name, "backbone": model_name if feat_key == "clip" else "resnet50-imagenet",
                             "features": feat_key, **{k: v for k, v in best["trial"].items() if k in ("C", "alpha", "hidden")}}
        best["head"].save(os.path.join(heads_dir, f"{name}.npz"))
        bests[name] = best
        all_trials += trials
        report[f"{name}_val"] = best["val_metrics"]
        report[f"{name}_temperature"] = best["head"].temperature

    report["selection_trials"] = all_trials
    plot_selection(all_trials, zs["macro_f1"], os.path.join(args.results_dir, "val_model_selection.png"))
    if "clip_mlp" in bests:
        plot_mlp_curve(bests["clip_mlp"]["model"], os.path.join(args.results_dir, "mlp_training_curve.png"))

    # Deployed head: best CLIP feature-extraction head (shareable encoder)
    clip_names = [n for n in ("clip_linear", "clip_mlp") if n in bests]
    deploy = max(clip_names, key=lambda n: bests[n]["val_metrics"]["macro_f1"])
    short = model_name.split("/")[-1]
    version = f"emotion-emoset8-{deploy}-{short}-{dt.date.today():%Y%m%d}"
    head = bests[deploy]["head"]
    head.meta.update({"model_version": version, "mode": "shared",
                      "val_macro_f1": bests[deploy]["val_metrics"]["macro_f1"],
                      "trained_classes": config.TRAINED_CLASSES, "seed": args.seed})
    head.save(os.path.join(args.artifacts_dir, config.HEAD_FILENAME), extra_arrays={
        "class_text": text["class_text"], "derived_text": text["derived_text"],
        "logit_scale": text["logit_scale"], "model_name": np.array(model_name)})
    report["deployed_head"] = {"candidate": deploy, "model_version": version}
    print(f"Deployed head: {deploy} → {version}", flush=True)

    # ---- Step 2: fine-tuning (partial unfreezing) ----------------------
    if args.finetune:
        import finetune
        report["finetune"] = finetune.run(
            model_name=model_name, train=tr, val=va, init_head=bests["clip_linear"]["head"],
            cache_dir=args.cache_dir, out_dir=os.path.join(args.artifacts_dir, config.FINETUNED_SUBDIR),
            results_dir=args.results_dir, epochs=args.ft_epochs,
            unfreeze_layers=args.ft_unfreeze_layers, batch_size=args.ft_batch, seed=args.seed)

    with open(os.path.join(args.artifacts_dir, config.TRAIN_REPORT_FILENAME), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    with open(os.path.join(args.results_dir, config.TRAIN_REPORT_FILENAME), "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print("Training done. Artifacts in", args.artifacts_dir)


if __name__ == "__main__":
    main()
