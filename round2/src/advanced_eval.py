"""
advanced_eval.py — Round 2
Data Vortex A'26 | Team: Event Horizon

Phase 6: Evaluation Gaps
- Bootstrap CIs (1,000 resamples) for F1 Score
- Expected Calibration Error (ECE) and Maximum Calibration Error (MCE)
- Learning Curves (using stratified splits)
"""

import os
import sys
import numpy as np
import pandas as pd
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.metrics import f1_score, accuracy_score
from sklearn.model_selection import learning_curve, StratifiedKFold

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, RANDOM_STATE
from optimize import LABELS

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")
PREDS_PATH = os.path.join(REPORTS_DIR, "test_predictions.npz")

def bootstrap_ci(y_true, y_pred, metric_func, n_resamples=1000, alpha=0.05):
    """Calculate Bootstrap Confidence Intervals for a given metric."""
    np.random.seed(RANDOM_STATE)
    n = len(y_true)
    scores = []
    
    for _ in range(n_resamples):
        indices = np.random.randint(0, n, n)
        score = metric_func(y_true[indices], y_pred[indices])
        scores.append(score)
        
    scores = np.sort(scores)
    lower = scores[int((alpha / 2.0) * n_resamples)]
    upper = scores[int((1 - alpha / 2.0) * n_resamples)]
    mean = np.mean(scores)
    
    return mean, lower, upper

def compute_calibration_errors(y_true, y_proba, n_bins=10):
    """Computes Expected Calibration Error (ECE) and Maximum Calibration Error (MCE)."""
    # Use max confidence for each prediction
    confidences = np.max(y_proba, axis=1)
    predictions = np.argmax(y_proba, axis=1)
    
    # Map string labels to indices for accuracy checking
    label_map = {lbl: i for i, lbl in enumerate(LABELS)}
    y_true_idx = np.array([label_map[lbl] for lbl in y_true])
    accuracies = (predictions == y_true_idx).astype(float)
    
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    
    for i in range(n_bins):
        bin_lower = bin_boundaries[i]
        bin_upper = bin_boundaries[i + 1]
        
        in_bin = (confidences > bin_lower) & (confidences <= bin_upper)
        prop_in_bin = np.mean(in_bin)
        
        if prop_in_bin > 0:
            acc_in_bin = np.mean(accuracies[in_bin])
            conf_in_bin = np.mean(confidences[in_bin])
            
            diff = np.abs(acc_in_bin - conf_in_bin)
            ece += prop_in_bin * diff
            mce = max(mce, diff)
            
    return ece, mce

def plot_learning_curve_custom(estimator, X, y):
    """Generates and saves a learning curve."""
    print("\n  Generating Learning Curve (this may take a minute)...")
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, cv=cv, scoring="f1_macro", n_jobs=-1,
        train_sizes=np.linspace(0.1, 1.0, 5), random_state=RANDOM_STATE
    )
    
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)
    
    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")
    
    ax.plot(train_sizes, train_mean, 'o-', color="#e74c3c", label="Training Score")
    ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color="#e74c3c")
    
    ax.plot(train_sizes, test_mean, 'o-', color="#2ecc71", label="Cross-validation Score")
    ax.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color="#2ecc71")
    
    ax.set_title("Learning Curve (Macro-F1)", color="white", fontsize=12, fontweight="bold")
    ax.set_xlabel("Training Examples", color="#aaa")
    ax.set_ylabel("Score", color="#aaa")
    ax.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white")
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#333")
    
    out = os.path.join(FIGURES_DIR, "learning_curve.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")

def main():
    print("=" * 70)
    print("ADVANCED EVALUATION METRICS (Phase 6)")
    print("=" * 70)
    
    if not os.path.exists(PREDS_PATH):
        print(f"Error: {PREDS_PATH} not found. Run optimize.py first.")
        sys.exit(1)
        
    preds = np.load(PREDS_PATH, allow_pickle=True)
    y_true = preds["y_true"]
    y_pred = preds["y_pred"]
    y_proba = preds["y_proba"]
    
    # 1. Bootstrap CIs
    print("\n[1] Bootstrap Confidence Intervals (1,000 resamples)")
    def macro_f1(y_t, y_p):
        return f1_score(y_t, y_p, average="macro")
        
    mean_f1, low_f1, high_f1 = bootstrap_ci(y_true, y_pred, macro_f1)
    print(f"  Macro-F1 95% CI : {mean_f1:.4f} [{low_f1:.4f}, {high_f1:.4f}]")
    
    # 2. ECE and MCE
    print("\n[2] Calibration Error (ECE / MCE)")
    ece, mce = compute_calibration_errors(y_true, y_proba)
    print(f"  Expected Calibration Error (ECE) : {ece:.4f}")
    print(f"  Maximum Calibration Error (MCE)  : {mce:.4f}")
    
    # 3. Learning Curves
    df, _ = load_and_audit(DATA_PATH)
    from sklearn.model_selection import train_test_split
    X_train, _, y_train, _ = train_test_split(
        df["post_text"].values, df["sentiment_label"].values, 
        test_size=0.20, stratify=df["sentiment_label"].values, random_state=RANDOM_STATE
    )
    
    from error_analysis import build_best_pipe
    pipe = build_best_pipe()
    
    plot_learning_curve_custom(pipe, X_train, y_train)
    
    results = {
        "bootstrap_ci": {
            "mean_macro_f1": round(mean_f1, 4),
            "lower_95": round(low_f1, 4),
            "upper_95": round(high_f1, 4)
        },
        "calibration": {
            "ece": round(ece, 4),
            "mce": round(mce, 4)
        }
    }
    
    out = os.path.join(REPORTS_DIR, "advanced_eval.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved advanced eval results to {out}")

if __name__ == "__main__":
    main()
