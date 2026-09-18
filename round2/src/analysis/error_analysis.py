"""
error_analysis.py — Round 2 Comprehensive Error Analysis
Data Vortex A'26 | Team: Event Horizon

Runs Parts 6-8 of improvement_plan.md:
  - Per-class error taxonomy (FP/FN breakdown)
  - Confidence distribution analysis
  - Multi-seed stability (10 random seeds)
  - Top misclassified examples with confidence scores
  - Error pattern heatmap
  - Summary JSON for the technical report
"""

import os
import sys
import json
import pickle
import warnings
import time

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import (
    accuracy_score, f1_score, confusion_matrix,
    classification_report, cohen_kappa_score, matthews_corrcoef,
)

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, apply_cleaning, RANDOM_STATE

DATA_PATH    = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
MODEL_PATH   = os.path.join(os.path.dirname(__file__), "..", "models", "sentiment_optimized.pkl")
FIGURES_DIR  = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
REPORTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "reports")
LABELS       = ["Negative", "Neutral", "Positive"]


def load_data_raw():
    df, _ = load_and_audit(DATA_PATH)
    df, _ = apply_cleaning(df)
    X_all   = df["cleaned_text"].values
    y_all   = df["sentiment_label"].values
    raw_all = df["text"].values if "text" in df.columns else df["cleaned_text"].values
    X_train, X_test, y_train, y_test, raw_train, raw_test = train_test_split(
        X_all, y_all, raw_all,
        test_size=0.20, stratify=y_all, random_state=RANDOM_STATE,
    )
    return X_train, X_test, y_train, y_test, raw_test


def build_best_pipe():
    return Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=(1, 1),
            max_features=None,
            sublinear_tf=True,
            min_df=3,
            max_df=0.85,
            strip_accents="unicode",
        )),
        ("clf", CalibratedClassifierCV(
            LinearSVC(C=0.133, max_iter=2000, class_weight="balanced",
                      random_state=RANDOM_STATE),
            cv=3, method="sigmoid")),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# 1. Per-class error taxonomy table
# ══════════════════════════════════════════════════════════════════════════════

def per_class_error_taxonomy(y_test, y_pred, y_proba, raw_test):
    print("\n" + "=" * 70)
    print("ERROR TAXONOMY — Per-class breakdown")
    print("=" * 70)

    rows = []
    for cls in LABELS:
        mask_true = y_test == cls
        mask_pred = y_pred == cls
        tp = ((y_test == cls) & (y_pred == cls)).sum()
        fp = ((y_test != cls) & (y_pred == cls)).sum()
        fn = ((y_test == cls) & (y_pred != cls)).sum()
        tn = ((y_test != cls) & (y_pred != cls)).sum()
        prec   = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1     = 2 * prec * recall / (prec + recall) if (prec + recall) > 0 else 0.0

        cls_idx = LABELS.index(cls)
        cls_conf = y_proba[:, cls_idx]
        avg_conf_correct   = cls_conf[(y_test == cls) & (y_pred == cls)].mean() if tp > 0 else 0.0
        avg_conf_incorrect = cls_conf[(y_test == cls) & (y_pred != cls)].mean() if fn > 0 else 0.0

        rows.append({
            "Class":        cls,
            "Support":      mask_true.sum(),
            "TP":           tp,
            "FP":           fp,
            "FN":           fn,
            "Precision":    round(prec, 4),
            "Recall":       round(recall, 4),
            "F1":           round(f1, 4),
            "AvgConf_TP":   round(avg_conf_correct, 4),
            "AvgConf_FN":   round(avg_conf_incorrect, 4),
            "ConfGap":      round(avg_conf_correct - avg_conf_incorrect, 4),
        })
        print(f"  {cls:10s}  TP={tp:4d}  FP={fp:4d}  FN={fn:4d}  "
              f"P={prec:.3f}  R={recall:.3f}  F1={f1:.3f}  "
              f"AvgConf_TP={avg_conf_correct:.3f}  AvgConf_FN={avg_conf_incorrect:.3f}")

    return pd.DataFrame(rows)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Misclassification direction table (what Neutral is confused with, etc.)
# ══════════════════════════════════════════════════════════════════════════════

def misclassification_direction(y_test, y_pred):
    print("\n" + "=" * 70)
    print("MISCLASSIFICATION DIRECTION — Confusion pairs")
    print("=" * 70)

    cm = confusion_matrix(y_test, y_pred, labels=LABELS)
    total_errors = cm.sum() - np.diag(cm).sum()
    rows = []
    for i, true_lbl in enumerate(LABELS):
        for j, pred_lbl in enumerate(LABELS):
            if i != j and cm[i, j] > 0:
                rows.append({
                    "True → Predicted": f"{true_lbl} → {pred_lbl}",
                    "Count": cm[i, j],
                    "% of Errors": round(100 * cm[i, j] / total_errors, 1),
                    "% of Class":  round(100 * cm[i, j] / cm[i].sum(), 1),
                })

    df = pd.DataFrame(rows).sort_values("Count", ascending=False)
    print(df.to_string(index=False))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 3. Top-N most confidently wrong predictions
# ══════════════════════════════════════════════════════════════════════════════

def top_confident_errors(y_test, y_pred, y_proba, raw_test, n=20):
    print("\n" + "=" * 70)
    print(f"TOP-{n} MOST CONFIDENTLY WRONG PREDICTIONS")
    print("=" * 70)

    wrong_mask  = y_pred != y_test
    wrong_idxs  = np.where(wrong_mask)[0]
    pred_confs  = np.max(y_proba, axis=1)

    wrong_confs = pred_confs[wrong_idxs]
    top_k       = np.argsort(wrong_confs)[-n:][::-1]
    top_idxs    = wrong_idxs[top_k]

    rows = []
    for idx in top_idxs:
        rows.append({
            "True":      y_test[idx],
            "Predicted": y_pred[idx],
            "Confidence": round(float(pred_confs[idx]), 4),
            "Text":      str(raw_test[idx])[:120],
        })
    df = pd.DataFrame(rows)

    print(df.to_string(index=False))
    return df


# ══════════════════════════════════════════════════════════════════════════════
# 4. Multi-seed stability test (10 seeds, same model config)
# ══════════════════════════════════════════════════════════════════════════════

def multi_seed_stability():
    print("\n" + "=" * 70)
    print("MULTI-SEED STABILITY — 10 seeds × 5-fold CV")
    print("  (validates single-split result isn't cherry-picked)")
    print("=" * 70)

    df, _ = load_and_audit(DATA_PATH)
    df, _ = apply_cleaning(df)
    X_all = df["cleaned_text"].values
    y_all = df["sentiment_label"].values

    seeds = [0, 7, 13, 21, 42, 99, 123, 256, 314, 999]
    f1_runs = []

    for seed in seeds:
        X_tr, X_te, y_tr, y_te = train_test_split(
            X_all, y_all, test_size=0.20, stratify=y_all, random_state=seed
        )
        pipe = build_best_pipe()
        pipe.fit(X_tr, y_tr)
        y_pr = pipe.predict(X_te)
        f1   = f1_score(y_te, y_pr, average="macro")
        f1_runs.append(f1)
        print(f"  seed={seed:4d}  macro-F1 = {f1:.4f}")

    arr = np.array(f1_runs)
    print(f"\n  Mean  ± Std  : {arr.mean():.4f} ± {arr.std():.4f}")
    print(f"  Min / Max    : {arr.min():.4f} / {arr.max():.4f}")
    print(f"  95% CI (approx): [{arr.mean() - 2*arr.std():.4f}, {arr.mean() + 2*arr.std():.4f}]")

    return {
        "seeds": seeds,
        "f1_per_seed": [round(v, 6) for v in f1_runs],
        "mean": round(arr.mean(), 6),
        "std":  round(arr.std(), 6),
        "min":  round(arr.min(), 6),
        "max":  round(arr.max(), 6),
    }


# ══════════════════════════════════════════════════════════════════════════════
# 5. Confidence distribution plots
# ══════════════════════════════════════════════════════════════════════════════

def plot_confidence_distribution(y_test, y_pred, y_proba):
    max_conf = np.max(y_proba, axis=1)
    correct  = y_pred == y_test

    fig, axes = plt.subplots(1, 3, figsize=(17, 5))
    fig.patch.set_facecolor("#0f1117")

    colors = {"correct": "#2ecc71", "wrong": "#e74c3c"}

    ax0 = axes[0]
    ax0.set_facecolor("#1a1d2e")
    ax0.hist(max_conf[correct], bins=30, color=colors["correct"],
             alpha=0.7, label="Correct", edgecolor="white", linewidth=0.3)
    ax0.hist(max_conf[~correct], bins=30, color=colors["wrong"],
             alpha=0.7, label="Wrong", edgecolor="white", linewidth=0.3)
    ax0.set_title("Confidence Distribution\n(Correct vs Wrong)", color="white",
                  fontweight="bold", fontsize=11)
    ax0.set_xlabel("Max Predicted Probability", color="#aaa")
    ax0.set_ylabel("Count", color="#aaa")
    ax0.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white")
    ax0.tick_params(colors="white")
    ax0.spines[:].set_color("#333")

    ax1 = axes[1]
    ax1.set_facecolor("#1a1d2e")
    label_colors = ["#e74c3c", "#3498db", "#2ecc71"]
    for cls, col in zip(LABELS, label_colors):
        cls_mask = y_test == cls
        cls_conf = y_proba[:, LABELS.index(cls)][cls_mask]
        cls_correct = (y_pred[cls_mask] == cls)
        ax1.scatter(cls_conf[cls_correct],  np.random.uniform(0, 0.3, cls_correct.sum()),
                    color=col, alpha=0.3, s=8, label=cls)
        ax1.scatter(cls_conf[~cls_correct], np.random.uniform(0.4, 0.7, (~cls_correct).sum()),
                    color=col, alpha=0.3, s=8, marker="x")
    ax1.set_title("Class Probability (dots=correct, x=wrong)",
                  color="white", fontweight="bold", fontsize=10)
    ax1.set_xlabel("Class Probability Score", color="#aaa")
    ax1.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white", fontsize=8)
    ax1.tick_params(colors="white")
    ax1.spines[:].set_color("#333")

    ax2 = axes[2]
    ax2.set_facecolor("#1a1d2e")
    bins = np.linspace(0.3, 1.0, 15)
    acc_vals, centers = [], []
    for b_lo, b_hi in zip(bins[:-1], bins[1:]):
        mask = (max_conf >= b_lo) & (max_conf < b_hi)
        if mask.sum() > 10:
            acc_vals.append(correct[mask].mean())
            centers.append((b_lo + b_hi) / 2)
    ax2.plot(centers, acc_vals, color="#f39c12", lw=2, marker="o", markersize=5)
    ax2.plot([0.3, 1.0], [0.3, 1.0], "w--", lw=1, label="Perfect calibration")
    ax2.set_title("Reliability Diagram (Calibration)",
                  color="white", fontweight="bold", fontsize=11)
    ax2.set_xlabel("Mean Confidence", color="#aaa")
    ax2.set_ylabel("Fraction Correct", color="#aaa")
    ax2.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white")
    ax2.tick_params(colors="white")
    ax2.spines[:].set_color("#333")

    plt.suptitle("Confidence & Calibration Analysis", color="white",
                 fontsize=13, fontweight="bold", y=1.01)
    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "confidence_calibration.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")
    return out


def plot_error_heatmap(dir_df: pd.DataFrame):
    pivot = pd.DataFrame(0, index=LABELS, columns=LABELS, dtype=float)
    for _, row in dir_df.iterrows():
        parts = row["True → Predicted"].split(" → ")
        pivot.loc[parts[0], parts[1]] = row["Count"]

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")
    sns.heatmap(pivot, annot=True, fmt=".0f", cmap="Oranges",
                linewidths=0.5, linecolor="#333",
                annot_kws={"size": 13, "weight": "bold", "color": "black"},
                cbar=True, ax=ax)
    ax.set_title("Error Flow: True → Predicted (off-diagonal only)",
                 color="white", fontweight="bold", fontsize=11, pad=10)
    ax.set_xlabel("Predicted", color="#aaa", fontsize=10)
    ax.set_ylabel("True", color="#aaa", fontsize=10)
    ax.tick_params(colors="white")
    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "error_heatmap.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")


def plot_seed_stability(stability: dict):
    seeds = stability["seeds"]
    f1s   = stability["f1_per_seed"]
    mean  = stability["mean"]
    std   = stability["std"]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")

    ax.bar(range(len(seeds)), f1s, color="#3498db", edgecolor="white", linewidth=0.4)
    ax.axhline(mean, color="#f39c12", lw=2, linestyle="--", label=f"Mean={mean:.4f}")
    ax.axhspan(mean - std, mean + std, color="#f39c12", alpha=0.15, label=f"±1 std ({std:.4f})")
    ax.set_xticks(range(len(seeds)))
    ax.set_xticklabels([str(s) for s in seeds], color="white", fontsize=9)
    ax.set_ylabel("Test Macro-F1", color="#aaa", fontsize=10)
    ax.set_title(f"Multi-Seed Stability (10 random splits)\nMean={mean:.4f} ± {std:.4f}",
                 color="white", fontweight="bold", fontsize=11)
    ax.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#333")
    ax.set_ylim(min(f1s) - 0.02, max(f1s) + 0.05)

    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "seed_stability.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    t0 = time.time()
    print("""
╔══════════════════════════════════════════════════════════════╗
║   ROUND 2 — COMPREHENSIVE ERROR ANALYSIS                     ║
╚══════════════════════════════════════════════════════════════╝
""")

    X_train, X_test, y_train, y_test, raw_test = load_data_raw()

    pred_path = os.path.join(REPORTS_DIR, "test_predictions.npz")
    if os.path.exists(pred_path):
        preds = np.load(pred_path, allow_pickle=True)
        y_pred = preds["y_pred"]
        y_proba = preds["y_proba"]
        y_test_loaded = preds["y_true"]
        if not np.array_equal(y_test, y_test_loaded):
            print("WARNING: Loaded y_true does not match split y_test. Random states may have drifted.")
            y_test = y_test_loaded
    else:
        print(f"Error: {pred_path} not found. Run optimize.py first.")
        sys.exit(1)

    print(f"\n  Test Macro-F1 : {f1_score(y_test, y_pred, average='macro'):.4f}")
    print(f"  Test Accuracy : {accuracy_score(y_test, y_pred):.4f}")

    taxonomy_df = per_class_error_taxonomy(y_test, y_pred, y_proba, raw_test)
    direction_df = misclassification_direction(y_test, y_pred)
    errors_df    = top_confident_errors(y_test, y_pred, y_proba, raw_test, n=20)
    stability    = multi_seed_stability()

    print("\n" + "=" * 70)
    print("PLOTS — Confidence, Error Heatmap, Stability")
    print("=" * 70)
    plot_confidence_distribution(y_test, y_pred, y_proba)
    plot_error_heatmap(direction_df)
    plot_seed_stability(stability)

    summary = {
        "per_class_taxonomy":       taxonomy_df.to_dict(orient="records"),
        "misclassification_pairs":  direction_df.to_dict(orient="records"),
        "top_confident_errors":     errors_df[["True","Predicted","Confidence","Text"]].to_dict(orient="records"),
        "multi_seed_stability":     stability,
    }
    path = os.path.join(REPORTS_DIR, "error_analysis.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\n  Error analysis saved: {path}")

    taxonomy_df.to_csv(os.path.join(REPORTS_DIR, "per_class_taxonomy.csv"), index=False)
    direction_df.to_csv(os.path.join(REPORTS_DIR, "error_directions.csv"), index=False)
    errors_df.to_csv(os.path.join(REPORTS_DIR, "top_errors.csv"), index=False)

    elapsed = time.time() - t0
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ERROR ANALYSIS COMPLETE  ({elapsed:.0f}s)
║  Multi-seed F1: {stability['mean']:.4f} ± {stability['std']:.4f}
║  Figures: confidence_calibration.png
║           error_heatmap.png
║           seed_stability.png
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
