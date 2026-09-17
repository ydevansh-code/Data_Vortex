"""
evaluate.py — Round 2 NLP Evaluation, Confusion Matrix, Error Analysis & LIME
Data Vortex A'26 | Team: Event Horizon
"""

import os
import json
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score,
)
from sklearn.dummy import DummyClassifier

warnings.filterwarnings("ignore")

RANDOM_STATE = 42
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(FIGURES_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# Full Evaluation Report
# ──────────────────────────────────────────────

def evaluate_model(model, X_test, y_test, winner_name: str, baseline_acc: float, baseline_f1: float) -> dict:
    print("\n" + "=" * 60)
    print(f"  STAGE 7: FINAL MODEL EVALUATION [{winner_name}]")
    print("=" * 60)

    y_pred = model.predict(X_test)
    labels = sorted(list(set(y_test)))

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    weighted_f1 = f1_score(y_test, y_pred, average="weighted", zero_division=0)
    macro_prec = precision_score(y_test, y_pred, average="macro", zero_division=0)
    macro_rec = recall_score(y_test, y_pred, average="macro", zero_division=0)

    print(f"  Accuracy         : {acc:.4f}  (baseline {baseline_acc:.4f}, lift +{acc-baseline_acc:.4f})")
    print(f"  Macro-F1         : {macro_f1:.4f}  (baseline {baseline_f1:.4f}, lift +{macro_f1-baseline_f1:.4f})")
    print(f"  Weighted-F1      : {weighted_f1:.4f}")
    print(f"  Macro-Precision  : {macro_prec:.4f}")
    print(f"  Macro-Recall     : {macro_rec:.4f}")
    print("\n" + classification_report(y_test, y_pred, zero_division=0))

    report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)

    return {
        "y_pred": y_pred,
        "labels": labels,
        "accuracy": acc,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
        "macro_precision": macro_prec,
        "macro_recall": macro_rec,
        "report_dict": report,
        "baseline_acc": baseline_acc,
        "baseline_f1": baseline_f1,
    }


# ──────────────────────────────────────────────
# Confusion Matrix Plot
# ──────────────────────────────────────────────

def plot_confusion_matrix(y_test, y_pred, labels: list, winner_name: str):
    cm = confusion_matrix(y_test, y_pred, labels=labels)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0f1117")
    for ax in axes:
        ax.set_facecolor("#1a1d2e")

    for ax, data, title, fmt in zip(
        axes,
        [cm, cm_norm],
        ["Confusion Matrix — Raw Counts", "Confusion Matrix — Normalized (Row %)"],
        ["d", ".2f"],
    ):
        sns.heatmap(
            data, annot=True, fmt=fmt, cmap="Blues",
            xticklabels=labels, yticklabels=labels,
            linewidths=0.5, linecolor="#333",
            ax=ax, cbar=True,
            annot_kws={"size": 11, "weight": "bold", "color": "black"},
        )
        ax.set_title(title, color="white", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Predicted Label", color="#aaa", fontsize=10)
        ax.set_ylabel("True Label", color="#aaa", fontsize=10)
        ax.tick_params(colors="white")

    plt.suptitle(f"Model: {winner_name}", color="#aaa", fontsize=10, y=1.02)
    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "confusion_matrix.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  [Plot] Saved: {out}")
    return out


# ──────────────────────────────────────────────
# Error Analysis
# ──────────────────────────────────────────────

ERROR_CATEGORIES = {
    ("Negative", "Positive"): "Missed negation / sarcasm",
    ("Positive", "Negative"): "Overly negative framing detected",
    ("Neutral",  "Positive"): "Weak positive signal misread as Neutral",
    ("Neutral",  "Negative"): "Weak negative signal misread as Neutral",
    ("Positive", "Neutral"):  "Ambiguous boundary (Positive ≈ Neutral)",
    ("Negative", "Neutral"):  "Ambiguous boundary (Negative ≈ Neutral)",
}

def _categorize(true_label, pred_label, text: str) -> str:
    rule = ERROR_CATEGORIES.get((true_label, pred_label), "Other / Label noise")
    words = text.split()
    if len(words) <= 4:
        return "Extremely short text"
    if any(w in text.lower() for w in ["not", "no ", "never", "n't", "isn't", "wasn't", "won't", "can't"]):
        return "Negation handling failure"
    return rule


def run_error_analysis(X_test_raw, y_test, y_pred, n_samples: int = 20) -> pd.DataFrame:
    print("\n" + "=" * 60)
    print("  STAGE 8: ERROR ANALYSIS")
    print("=" * 60)

    mask = y_test != y_pred
    err_texts = X_test_raw[mask]
    err_true = y_test[mask]
    err_pred = y_pred[mask]

    n = min(n_samples, len(err_texts))
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(err_texts), size=n, replace=False)
    idx = np.sort(idx)

    rows = []
    for i in idx:
        text = str(err_texts[i])
        snippet = text[:90] + ("..." if len(text) > 90 else "")
        cat = _categorize(err_true[i], err_pred[i], text)
        rows.append({
            "Text Snippet": snippet,
            "True Label": err_true[i],
            "Predicted": err_pred[i],
            "Error Category": cat,
        })

    df_errors = pd.DataFrame(rows)

    print(f"  Total misclassified: {mask.sum()} / {len(y_test)}")
    print(f"  Sampled for analysis: {n}")
    print("\n  Error Category Breakdown:")
    for cat, cnt in df_errors["Error Category"].value_counts().items():
        print(f"    {cat:<40} {cnt}")

    out = os.path.join(REPORTS_DIR, "error_analysis.csv")
    df_errors.to_csv(out, index=False)
    print(f"  Error table saved: {out}")
    return df_errors


# ──────────────────────────────────────────────
# LIME Explanations
# ──────────────────────────────────────────────

def run_lime_explanations(model, X_test_raw, y_test, y_pred, labels: list, n=2) -> list:
    print("\n" + "=" * 60)
    print("  STAGE 9: LIME INTERPRETABILITY")
    print("=" * 60)

    try:
        from lime.lime_text import LimeTextExplainer
    except ImportError:
        print("  [WARN] lime not installed — skipping LIME step. Run: pip install lime")
        return []

    explainer = LimeTextExplainer(class_names=labels, random_state=RANDOM_STATE)

    lime_results = []

    def predict_proba_fn(texts):
        if hasattr(model, "predict_proba"):
            return model.predict_proba(texts)
        decision = model.decision_function(texts)
        exp_d = np.exp(decision - decision.max(axis=1, keepdims=True))
        return exp_d / exp_d.sum(axis=1, keepdims=True)

    correct_mask = y_test == y_pred
    error_mask = ~correct_mask

    sample_sets = [
        ("Correctly Classified", X_test_raw[correct_mask], y_test[correct_mask], y_pred[correct_mask]),
        ("Misclassified", X_test_raw[error_mask], y_test[error_mask], y_pred[error_mask]),
    ]

    fig, axes = plt.subplots(1, 2, figsize=(16, 5))
    fig.patch.set_facecolor("#0f1117")

    for ax_idx, (label_tag, texts, true_lbls, pred_lbls) in enumerate(sample_sets):
        if len(texts) == 0:
            continue
        idx = 0
        text = str(texts[idx])
        print(f"\n  [{label_tag}]")
        print(f"  Text   : {text[:100]}...")
        print(f"  True   : {true_lbls[idx]}  | Predicted: {pred_lbls[idx]}")

        exp = explainer.explain_instance(
            text, predict_proba_fn,
            num_features=10,
            num_samples=200,
            labels=[labels.index(pred_lbls[idx])],
        )

        pred_label_idx = labels.index(pred_lbls[idx])
        feature_weights = exp.as_list(label=pred_label_idx)
        words = [fw[0] for fw in feature_weights]
        weights = [fw[1] for fw in feature_weights]

        colors = ["#2ecc71" if w > 0 else "#e74c3c" for w in weights]
        ax = axes[ax_idx]
        ax.set_facecolor("#1a1d2e")
        ax.barh(words, weights, color=colors, edgecolor="white", linewidth=0.3)
        ax.axvline(0, color="white", linewidth=0.8)
        ax.set_title(f"LIME: {label_tag}\nTrue={true_lbls[idx]} | Pred={pred_lbls[idx]}",
                     color="white", fontsize=10, fontweight="bold")
        ax.tick_params(colors="white", labelsize=9)
        ax.spines[:].set_color("#333")
        ax.set_xlabel("Feature Weight", color="#aaa", fontsize=9)

        lime_results.append({
            "type": label_tag,
            "text": text[:200],
            "true_label": true_lbls[idx],
            "predicted_label": pred_lbls[idx],
            "top_features": feature_weights[:5],
        })

        print(f"  Top features: {feature_weights[:5]}")

    plt.suptitle("LIME Token-Level Feature Importance", color="white", fontsize=12, fontweight="bold", y=1.01)
    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "lime_explanations.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\n  [Plot] Saved: {out}")

    return lime_results


# ──────────────────────────────────────────────
# Per-Class Metrics Bar Chart
# ──────────────────────────────────────────────

def plot_per_class_metrics(report_dict: dict, labels: list):
    metrics = ["precision", "recall", "f1-score"]
    data = {m: [report_dict[l][m] for l in labels] for m in metrics}

    x = np.arange(len(labels))
    w = 0.25
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")

    colors = ["#3498db", "#2ecc71", "#e67e22"]
    for i, (metric, color) in enumerate(zip(metrics, colors)):
        bars = ax.bar(x + i * w, data[metric], w, label=metric.capitalize(),
                      color=color, edgecolor="white", linewidth=0.4)
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                    f"{bar.get_height():.2f}", ha="center", va="bottom",
                    color="white", fontsize=8, fontweight="bold")

    ax.set_xticks(x + w)
    ax.set_xticklabels(labels, color="white", fontsize=10)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("Score", color="#aaa", fontsize=10)
    ax.set_title("Per-Class Precision / Recall / F1", color="white", fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#333")
    ax.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white", fontsize=9)

    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "per_class_metrics.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  [Plot] Saved: {out}")


# ──────────────────────────────────────────────
# Save All Metrics as JSON (for report generator)
# ──────────────────────────────────────────────

def save_metrics_json(eval_result: dict, winner_name: str, lime_results: list, df_errors: pd.DataFrame):
    out = {
        "model": winner_name,
        "accuracy": eval_result["accuracy"],
        "macro_f1": eval_result["macro_f1"],
        "weighted_f1": eval_result["weighted_f1"],
        "macro_precision": eval_result["macro_precision"],
        "macro_recall": eval_result["macro_recall"],
        "baseline_accuracy": eval_result["baseline_acc"],
        "baseline_macro_f1": eval_result["baseline_f1"],
        "lift_accuracy": round(eval_result["accuracy"] - eval_result["baseline_acc"], 4),
        "lift_macro_f1": round(eval_result["macro_f1"] - eval_result["baseline_f1"], 4),
        "per_class": eval_result["report_dict"],
        "lime_samples": lime_results,
        "error_analysis_sample": df_errors.to_dict(orient="records"),
    }
    path = os.path.join(REPORTS_DIR, "metrics.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"  Metrics JSON saved: {path}")
    return out
