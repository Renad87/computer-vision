"""Step 3 — Independent evaluation on the held-out test split.

The test subsample comes from EmoSet's official test split and is never used
for training, model selection or temperature calibration.

Produces in results/:
  metrics.json, RESULTS.md (tables generated from the actual numbers)
  model_comparison.png, per_class_f1.png, confusion_*.png,
  reliability_deployed.png, ambiguity_margin.png, ambiguous_examples.png,
  attributes_by_emotion.png, confused_pairs.csv

Usage:
    python ml/emotion/evaluate.py
    python ml/emotion/evaluate.py --skip_finetuned      # CPU-only / no fine-tuned model
"""
from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402
from head import Head, softmax  # noqa: E402
from metrics import (bootstrap_ci, classification_metrics, macro_f1_fn,  # noqa: E402
                     normalized_entropy, reliability_bins, top2_margin)
from policy import is_ambiguous_batch, suggest_indices  # noqa: E402
from train import load_split, load_text, zero_shot_proba  # noqa: E402

C = config.TRAINED_CLASSES
PRETTY = {
    "zero_shot_clip": "CLIP zero-shot (no training)",
    "attributes_only": "Colour/light attributes only + LR",
    "resnet_linear": "ResNet50 frozen + LR",
    "clip_linear": "CLIP frozen + LR",
    "clip_mlp": "CLIP frozen + MLP",
    "clip_finetuned": "CLIP fine-tuned (partial unfreeze)",
}


def _plt():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


# ----------------------------------------------------------------- models
def collect_predictions(args, tr, te, text):
    preds = {}  # name -> dict(prob=calibrated, prob_raw=uncalibrated)
    zs = zero_shot_proba(te["clip"], text["class_text"], text["logit_scale"])
    preds["zero_shot_clip"] = {"prob": zs, "prob_raw": zs}

    # attribute-only classifier: how much do colour & light alone explain?
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    sc = StandardScaler().fit(tr["attributes"])
    lr = LogisticRegression(max_iter=3000, class_weight="balanced").fit(sc.transform(tr["attributes"]), tr["labels"])
    p = lr.predict_proba(sc.transform(te["attributes"]))
    preds["attributes_only"] = {"prob": p, "prob_raw": p}

    for path in sorted(glob.glob(os.path.join(args.artifacts_dir, config.HEADS_SUBDIR, "*.npz"))):
        head, _ = Head.load(path)
        feats = te[head.meta["features"]]
        name = head.meta["candidate"]
        preds[name] = {"prob": head.proba(feats, True), "prob_raw": head.proba(feats, False)}

    ft_dir = os.path.join(args.artifacts_dir, config.FINETUNED_SUBDIR)
    if not args.skip_finetuned and os.path.exists(os.path.join(ft_dir, config.FT_STATE_FILENAME)):
        import finetune
        model, head, meta, device = finetune.load_finetuned(ft_dir)
        loader = finetune.eval_loader(args.cache_dir, te["paths"], te["labels"])
        logits, y = finetune.predict_logits(model, head, loader, device)
        assert np.array_equal(y, te["labels"])
        preds["clip_finetuned"] = {"prob": softmax(logits / meta["temperature"]), "prob_raw": softmax(logits)}
    return preds


# ----------------------------------------------------------------- plots
def plot_model_comparison(summary, path):
    plt = _plt()
    names = list(summary)
    f1 = [summary[n]["macro_f1"] for n in names]
    lo = [summary[n]["macro_f1"] - summary[n]["macro_f1_ci"][0] for n in names]
    hi = [summary[n]["macro_f1_ci"][1] - summary[n]["macro_f1"] for n in names]
    acc = [summary[n]["accuracy"] for n in names]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    x = np.arange(len(names))
    ax.bar(x, f1, yerr=[lo, hi], capsize=4, color="#4C72B0", label="macro-F1 (95% bootstrap CI)")
    ax.scatter(x, acc, color="#DD8452", zorder=3, label="accuracy")
    ax.axhline(1 / len(C), ls=":", color="grey", label="chance (1/8)")
    for xi, v in zip(x, f1):
        ax.text(xi, v + 0.01, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_xticks(x, [PRETTY.get(n, n) for n in names], rotation=25, ha="right", fontsize=8)
    ax.set_ylabel("score on held-out test")
    ax.set_title("Test-set comparison: before training vs. transfer learning")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_per_class(metrics, names, path):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(11, 4.5))
    w = 0.8 / len(names)
    x = np.arange(len(C))
    for i, n in enumerate(names):
        ax.bar(x + i * w - 0.4 + w / 2, [metrics[n]["per_class"][c]["f1"] for c in C], w, label=PRETTY.get(n, n))
    ax.set_xticks(x, C, rotation=30)
    ax.set_ylabel("F1 (test)")
    ax.set_title("Per-emotion F1")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_confusion(cm, title, path):
    plt = _plt()
    cm = np.asarray(cm, float)
    cmn = cm / np.maximum(cm.sum(axis=1, keepdims=True), 1)
    fig, ax = plt.subplots(figsize=(6.5, 5.5))
    im = ax.imshow(cmn, cmap="Blues", vmin=0, vmax=1)
    for i in range(len(C)):
        for j in range(len(C)):
            ax.text(j, i, f"{cmn[i, j]:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if cmn[i, j] > 0.5 else "black")
    ax.set_xticks(range(len(C)), C, rotation=45, ha="right")
    ax.set_yticks(range(len(C)), C)
    ax.set_xlabel("predicted"); ax.set_ylabel("true")
    ax.set_title(title, fontsize=10)
    fig.colorbar(im, fraction=0.046)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_reliability(y, prob_raw, prob_cal, path):
    plt = _plt()
    fig, ax = plt.subplots(figsize=(5.5, 5))
    for prob, lab, col in [(prob_raw, "before temperature scaling", "#C44E52"),
                           (prob_cal, "after temperature scaling", "#4C72B0")]:
        c, a, n = reliability_bins(y, prob)
        m = n > 0
        ax.plot(c[m], a[m], "o-", label=lab, color=col)
    ax.plot([0, 1], [0, 1], ":", color="grey", label="perfect calibration")
    ax.set_xlabel("confidence"); ax.set_ylabel("accuracy")
    ax.set_title("Reliability diagram (deployed model)")
    ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def plot_ambiguity(y, prob, path):
    plt = _plt()
    margin = top2_margin(prob)
    ent = normalized_entropy(prob)
    correct = prob.argmax(1) == y
    edges = [0, 0.1, 0.2, 0.3, 0.5, 1.0001]
    accs, counts, labels = [], [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (margin >= lo) & (margin < hi)
        accs.append(correct[m].mean() if m.any() else np.nan)
        counts.append(int(m.sum()))
        labels.append(f"{lo:.1f}-{min(hi, 1):.1f}")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    b = axes[0].bar(labels, accs, color="#4C72B0")
    for bi, n in zip(b, counts):
        axes[0].text(bi.get_x() + bi.get_width() / 2, (bi.get_height() or 0) + 0.01, f"n={n}", ha="center", fontsize=8)
    axes[0].set_xlabel("margin between top-1 and top-2 probability")
    axes[0].set_ylabel("top-1 accuracy")
    axes[0].set_title("Low margin = image carries more than one emotion")
    axes[1].hist(ent[correct], bins=20, alpha=0.6, label="correct", density=True)
    axes[1].hist(ent[~correct], bins=20, alpha=0.6, label="wrong", density=True)
    axes[1].axvline(config.AMBIGUOUS_ENTROPY, ls=":", color="k", label="ambiguity threshold")
    axes[1].set_xlabel("normalised entropy"); axes[1].legend(fontsize=8)
    axes[1].set_title("Uncertainty of correct vs wrong predictions")
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)
    return {"margin_bins": labels, "accuracy_per_bin": [None if np.isnan(a) else float(a) for a in accs],
            "count_per_bin": counts}


def plot_ambiguous_examples(cache_dir, paths, y, prob, path, n=12):
    from PIL import Image
    plt = _plt()
    order = np.argsort(top2_margin(prob))[:n]
    if not all(os.path.exists(os.path.join(cache_dir, str(paths[i]))) for i in order):
        return False
    cols = 4
    fig, axes = plt.subplots(int(np.ceil(n / cols)), cols, figsize=(cols * 3.2, 3.6 * np.ceil(n / cols)))
    for ax, i in zip(axes.ravel(), order):
        ax.imshow(Image.open(os.path.join(cache_dir, str(paths[i]))).convert("RGB"))
        top = np.argsort(prob[i])[::-1][:2]
        ax.set_title(f"true: {C[y[i]]}\n{C[top[0]]} {prob[i, top[0]]:.2f} | {C[top[1]]} {prob[i, top[1]]:.2f}",
                     fontsize=8)
        ax.axis("off")
    for ax in axes.ravel()[len(order):]:
        ax.axis("off")
    fig.suptitle("Most ambiguous test images (smallest top-1/top-2 margin)")
    fig.tight_layout(); fig.savefig(path, dpi=130); plt.close(fig)
    return True


def attribute_study(te, path):
    from scipy.stats import kruskal
    plt = _plt()
    cols = {k: te["attributes"][:, i] for i, k in enumerate(config.ATTRIBUTE_KEYS)}
    cols["emoset_brightness"] = te["ds_brightness"]
    cols["emoset_colorfulness"] = te["ds_colorfulness"]
    y = te["labels"]
    stats = {}
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))
    for ax, (name, v) in zip(axes.ravel(), cols.items()):
        groups = [v[(y == k) & ~np.isnan(v)] for k in range(len(C))]
        valid = [g for g in groups if len(g) > 1]
        entry = {"mean_per_class": {C[k]: (float(g.mean()) if len(g) else None) for k, g in enumerate(groups)}}
        if len(valid) >= 2:
            H, p = kruskal(*valid)
            n_tot, k_ = sum(len(g) for g in valid), len(valid)
            entry.update({"kruskal_H": float(H), "p_value": float(p),
                          "epsilon_squared": float((H - k_ + 1) / (n_tot - k_))})
        stats[name] = entry
        ax.boxplot([g if len(g) else [np.nan] for g in groups], showfliers=False)
        ax.set_xticks(range(1, len(C) + 1), C, rotation=45, fontsize=8)
        title = name
        if "epsilon_squared" in entry:
            title += f"\nε²={entry['epsilon_squared']:.3f}, p={entry['p_value']:.1e}"
        ax.set_title(title, fontsize=9)
    axes.ravel()[-1].axis("off")
    fig.suptitle("Colour & light attributes by emotion (test split)")
    fig.tight_layout(); fig.savefig(path, dpi=140); plt.close(fig)
    return stats


# ----------------------------------------------------------------- report
def confused_pairs(cm, top=6):
    cm = np.asarray(cm)
    pairs = []
    for i in range(len(C)):
        for j in range(i + 1, len(C)):
            pairs.append((C[i], C[j], int(cm[i, j]), int(cm[j, i]), int(cm[i, j] + cm[j, i])))
    return sorted(pairs, key=lambda t: -t[-1])[:top]


def write_markdown(path, out):
    s, d = out["summary"], out["deployed"]
    L = ["# Visual Emotion Recognition — Test Results", "",
         "> Generated automatically by `evaluate.py` from the held-out test split. Do not edit numbers by hand.", "",
         f"- Test images: **{out['n_test']:,}** (class-balanced subsample of EmoSet-118K official test split)",
         f"- Deployed model: **{PRETTY.get(d, d)}** (`{out['deployed_version']}`)", "",
         "## 1. Model comparison", "",
         "| Model | Accuracy | Macro-P | Macro-R | Macro-F1 [95% CI] | Top-2 acc | ECE |",
         "|---|---|---|---|---|---|---|"]
    for n, m in s.items():
        L.append(f"| {PRETTY.get(n, n)} | {m['accuracy']:.3f} | {m['macro_precision']:.3f} | {m['macro_recall']:.3f} | "
                 f"{m['macro_f1']:.3f} [{m['macro_f1_ci'][0]:.3f}, {m['macro_f1_ci'][1]:.3f}] | "
                 f"{m['top2_accuracy']:.3f} | {m['ece']:.3f} |")
    if "zero_shot_clip" in s:
        gain = s[d]["macro_f1"] - s["zero_shot_clip"]["macro_f1"]
        L += ["", f"Gain of the deployed model over zero-shot: **{gain:+.3f} macro-F1**."]
    if "clip_finetuned" in s:
        g = s["clip_finetuned"]["macro_f1"] - s[d]["macro_f1"]
        L += [f"Fine-tuning vs deployed feature-extraction head: **{g:+.3f} macro-F1** "
              "(fine-tuning needs its own encoder; the frozen head can share Person 1's CLIP embedding)."]
    L += ["", "## 2. Per-emotion results (deployed model)", "",
          "| Emotion | Arabic | Precision | Recall | F1 | Support |", "|---|---|---|---|---|---|"]
    for c in C:
        pc = out["metrics"][d]["per_class"][c]
        L.append(f"| {c} | {config.ARABIC_NAMES[c]} | {pc['precision']:.3f} | {pc['recall']:.3f} | {pc['f1']:.3f} | {pc['support']} |")
    a = out["ambiguity"]
    L += ["", "## 3. Images with more than one emotional reading", "",
          f"- Flagged ambiguous (margin < {config.AMBIGUOUS_MARGIN} or entropy > {config.AMBIGUOUS_ENTROPY}): "
          f"**{a['fraction_ambiguous']:.1%}** of test images",
          f"- Top-1 accuracy: clear images **{a['accuracy_clear']:.3f}** vs ambiguous **{a['accuracy_ambiguous']:.3f}**",
          f"- Top-2 accuracy on ambiguous images: **{a['top2_accuracy_ambiguous']:.3f}**",
          f"- Suggestion set (what the app shows): contains the true label **{a['suggestion_hit_rate']:.3f}** "
          f"of the time, average size **{a['suggestion_mean_size']:.2f}** emotions", "",
          "Most confused pairs:", "", "| Pair | A→B | B→A | Total |", "|---|---|---|---|"]
    for p in out["confused_pairs"]:
        L.append(f"| {p[0]} ↔ {p[1]} | {p[2]} | {p[3]} | {p[4]} |")
    L += ["", "## 4. Colour & light study", "",
          f"- Attribute-only classifier (5 colour/light numbers): macro-F1 **{s['attributes_only']['macro_f1']:.3f}** "
          f"vs deployed CLIP model **{s[d]['macro_f1']:.3f}**", "",
          "| Attribute | Kruskal-Wallis p | ε² (effect size) | Highest-mean emotion | Lowest-mean emotion |",
          "|---|---|---|---|---|"]
    for name, st in out["attributes"].items():
        means = {k: v for k, v in st["mean_per_class"].items() if v is not None}
        if "p_value" in st and means:
            L.append(f"| {name} | {st['p_value']:.1e} | {st['epsilon_squared']:.3f} | "
                     f"{max(means, key=means.get)} | {min(means, key=means.get)} |")
    L += ["", "## 5. Figures", ""] + [f"- `{f}`" for f in out["figures"]]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--features_dir", default=config.DEFAULT_FEATURES_DIR)
    ap.add_argument("--cache_dir", default=config.DEFAULT_CACHE_DIR)
    ap.add_argument("--artifacts_dir", default=config.DEFAULT_ARTIFACTS_DIR)
    ap.add_argument("--results_dir", default=config.DEFAULT_RESULTS_DIR)
    ap.add_argument("--n_boot", type=int, default=1000)
    ap.add_argument("--skip_finetuned", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.results_dir, exist_ok=True)
    R = lambda f: os.path.join(args.results_dir, f)  # noqa: E731

    tr, te, text = load_split(args.features_dir, "train"), load_split(args.features_dir, "test"), load_text(args.features_dir)
    y = te["labels"]
    with open(os.path.join(args.artifacts_dir, config.TRAIN_REPORT_FILENAME)) as f:
        train_report = json.load(f)
    deployed = train_report["deployed_head"]["candidate"]

    preds = collect_predictions(args, tr, te, text)
    f1fn = macro_f1_fn(len(C))
    metrics, summary = {}, {}
    for n, p in preds.items():
        m = classification_metrics(y, p["prob"], C)
        m["macro_f1_ci"] = bootstrap_ci(y, p["prob"].argmax(1), f1fn, n_boot=args.n_boot)
        m["ece_before_temperature"] = classification_metrics(y, p["prob_raw"], C)["ece"]
        metrics[n] = m
        summary[n] = {k: m[k] for k in ("accuracy", "macro_precision", "macro_recall", "macro_f1",
                                        "macro_f1_ci", "weighted_f1", "top2_accuracy", "ece")}
        print(f"{PRETTY.get(n, n):40s} acc={m['accuracy']:.4f} macro-F1={m['macro_f1']:.4f} "
              f"[{m['macro_f1_ci'][0]:.3f}, {m['macro_f1_ci'][1]:.3f}] top2={m['top2_accuracy']:.4f}")

    figures = ["model_comparison.png", "per_class_f1.png"]
    plot_model_comparison(summary, R("model_comparison.png"))
    pc_models = [n for n in ("zero_shot_clip", "resnet_linear", deployed, "clip_finetuned") if n in metrics]
    plot_per_class(metrics, list(dict.fromkeys(pc_models)), R("per_class_f1.png"))
    for n in dict.fromkeys(["zero_shot_clip", deployed, "clip_finetuned"]):
        if n in metrics:
            plot_confusion(metrics[n]["confusion_matrix"], f"Confusion matrix — {PRETTY.get(n, n)}", R(f"confusion_{n}.png"))
            figures.append(f"confusion_{n}.png")

    pd = preds[deployed]
    plot_reliability(y, pd["prob_raw"], pd["prob"], R("reliability_deployed.png"))
    figures.append("reliability_deployed.png")

    prob = pd["prob"]
    amb = is_ambiguous_batch(prob)
    correct = prob.argmax(1) == y
    top2 = np.argsort(prob, axis=1)[:, -2:]
    sugg = [suggest_indices(p) for p in prob]
    ambiguity = {
        "fraction_ambiguous": float(amb.mean()),
        "accuracy_clear": float(correct[~amb].mean()) if (~amb).any() else float("nan"),
        "accuracy_ambiguous": float(correct[amb].mean()) if amb.any() else float("nan"),
        "top2_accuracy_ambiguous": float(np.mean([y[i] in top2[i] for i in np.where(amb)[0]])) if amb.any() else float("nan"),
        "suggestion_hit_rate": float(np.mean([yi in s for yi, s in zip(y, sugg)])),
        "suggestion_mean_size": float(np.mean([len(s) for s in sugg])),
        **plot_ambiguity(y, prob, R("ambiguity_margin.png")),
    }
    figures.append("ambiguity_margin.png")
    if plot_ambiguous_examples(args.cache_dir, te["paths"], y, prob, R("ambiguous_examples.png")):
        figures.append("ambiguous_examples.png")

    pairs = confused_pairs(metrics[deployed]["confusion_matrix"])
    with open(R("confused_pairs.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["emotion_a", "emotion_b", "a_predicted_as_b", "b_predicted_as_a", "total"])
        w.writerows(pairs)

    attr_stats = attribute_study(te, R("attributes_by_emotion.png"))
    figures.append("attributes_by_emotion.png")

    out = {"n_test": int(len(y)), "test_per_class": np.bincount(y, minlength=len(C)).tolist(),
           "deployed": deployed, "deployed_version": train_report["deployed_head"]["model_version"],
           "summary": summary, "metrics": metrics, "ambiguity": ambiguity,
           "confused_pairs": pairs, "attributes": attr_stats, "figures": figures}
    with open(R("metrics.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    write_markdown(R("RESULTS.md"), out)
    print("Evaluation done →", R("RESULTS.md"))


if __name__ == "__main__":
    main()
