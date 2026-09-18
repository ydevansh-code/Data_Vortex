"""
train.py — Round 2 NLP Model Training & Comparison
Data Vortex A'26 | Team: Event Horizon

Trains Majority-Class Baseline, MNB, Logistic Regression, and Linear SVM.
Selects winner by Macro-F1. Persists best model as .pkl.
No data leakage: TF-IDF fitted on training split only.
"""

import os
import time
import json
import pickle
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline
from sklearn.dummy import DummyClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.model_selection import GridSearchCV, StratifiedKFold, cross_validate
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score,
)

warnings.filterwarnings("ignore")

RANDOM_STATE = 42
MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# Candidate Pipelines
# ──────────────────────────────────────────────

def build_candidates() -> dict:
    tfidf_base = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=50_000,
        sublinear_tf=True,
        min_df=2,
        strip_accents="unicode",
    )

    return {
        "Majority-Class Baseline": Pipeline([
            ("tfidf", TfidfVectorizer(max_features=1)),
            ("clf", DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)),
        ]),
        "Multinomial Naive Bayes": Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2), max_features=50_000,
                sublinear_tf=False, min_df=2, strip_accents="unicode")),
            ("clf", MultinomialNB(alpha=0.5)),
        ]),
        "Logistic Regression": Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2), max_features=50_000,
                sublinear_tf=True, min_df=2, strip_accents="unicode")),
            ("clf", LogisticRegression(
                C=1.0, max_iter=1000, solver="lbfgs",
                class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1)),
        ]),
        "Linear SVM": Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2), max_features=50_000,
                sublinear_tf=True, min_df=2, strip_accents="unicode")),
            ("clf", LinearSVC(
                C=1.0, max_iter=2000,
                class_weight="balanced", random_state=RANDOM_STATE)),
        ]),
    }


# ──────────────────────────────────────────────
# Model Comparison
# ──────────────────────────────────────────────

def run_model_comparison(X_train, y_train) -> tuple[pd.DataFrame, str]:
    candidates = build_candidates()
    results = []

    print("\n" + "=" * 60)
    print("  STAGE 5: MODEL CANDIDATE COMPARISON (5-Fold CV on Train)")
    print("=" * 60)

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

    for name, pipeline in candidates.items():
        t0 = time.time()
        
        scores = cross_validate(
            pipeline, X_train, y_train, cv=skf, 
            scoring=('accuracy', 'f1_macro', 'f1_weighted', 'precision_macro', 'recall_macro'),
            n_jobs=-1
        )
        train_time = time.time() - t0

        acc = scores['test_accuracy'].mean()
        macro_f1 = scores['test_f1_macro'].mean()
        weighted_f1 = scores['test_f1_weighted'].mean()
        macro_prec = scores['test_precision_macro'].mean()
        macro_rec = scores['test_recall_macro'].mean()

        results.append({
            "Model": name,
            "Accuracy": round(acc, 4),
            "Macro-F1": round(macro_f1, 4),
            "Weighted-F1": round(weighted_f1, 4),
            "Macro-Precision": round(macro_prec, 4),
            "Macro-Recall": round(macro_rec, 4),
            "Train Time (s)": round(train_time, 2),
        })

        marker = " ← BASELINE" if name == "Majority-Class Baseline" else ""
        print(f"  {name:<30} Acc={acc:.4f}  MacroF1={macro_f1:.4f}  t={train_time:.2f}s{marker}")

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("Macro-F1", ascending=False).reset_index(drop=True)

    baseline_f1 = df_results[df_results["Model"] == "Majority-Class Baseline"]["Macro-F1"].values[0]
    baseline_acc = df_results[df_results["Model"] == "Majority-Class Baseline"]["Accuracy"].values[0]

    non_baseline = df_results[df_results["Model"] != "Majority-Class Baseline"]
    winner_name = non_baseline.iloc[0]["Model"]
    winner_f1 = non_baseline.iloc[0]["Macro-F1"]
    winner_acc = non_baseline.iloc[0]["Accuracy"]

    print(f"\n  Winner by Macro-F1: [{winner_name}]")
    print(f"  Lift over baseline: MacroF1 {winner_f1:.4f} vs {baseline_f1:.4f} "
          f"| Acc {winner_acc:.4f} vs {baseline_acc:.4f}")

    out_csv = os.path.join(REPORTS_DIR, "model_comparison.csv")
    df_results.to_csv(out_csv, index=False)
    print(f"  Comparison table saved: {out_csv}")

    return df_results, winner_name, candidates


# ──────────────────────────────────────────────
# Hyperparameter Grid Search on Winner
# ──────────────────────────────────────────────

def tune_winner(winner_name: str, X_train, y_train) -> Pipeline:
    print("\n" + "=" * 60)
    print(f"  STAGE 6: HYPERPARAMETER TUNING [{winner_name}]")
    print("=" * 60)

    if winner_name == "Logistic Regression":
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                sublinear_tf=True, strip_accents="unicode", min_df=2)),
            ("clf", LogisticRegression(
                max_iter=1000, solver="lbfgs",
                class_weight="balanced", random_state=RANDOM_STATE, n_jobs=-1)),
        ])
        param_grid = {
            "tfidf__ngram_range": [(1, 1), (1, 2)],
            "tfidf__max_features": [30_000, 50_000],
            "clf__C": [0.1, 1.0, 5.0, 10.0],
        }

    elif winner_name == "Linear SVM":
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                sublinear_tf=True, strip_accents="unicode", min_df=2)),
            ("clf", LinearSVC(
                max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
        ])
        param_grid = {
            "tfidf__ngram_range": [(1, 1), (1, 2)],
            "tfidf__max_features": [30_000, 50_000],
            "clf__C": [0.1, 0.5, 1.0, 5.0],
        }

    else:
        pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2), max_features=50_000,
                sublinear_tf=True, min_df=2, strip_accents="unicode")),
            ("clf", MultinomialNB()),
        ])
        param_grid = {"clf__alpha": [0.1, 0.5, 1.0, 2.0]}

    gs = GridSearchCV(
        pipeline, param_grid,
        scoring="f1_macro",
        cv=3,
        n_jobs=-1,
        verbose=0,
        refit=True,
    )
    gs.fit(X_train, y_train)

    print(f"  Best params : {gs.best_params_}")
    print(f"  CV Macro-F1 : {gs.best_score_:.4f}")
    return gs.best_estimator_


# ──────────────────────────────────────────────
# Persist Model
# ──────────────────────────────────────────────

def save_model(model: Pipeline, name: str) -> str:
    safe_name = name.lower().replace(" ", "_").replace("-", "")
    path = os.path.join(MODELS_DIR, f"sentiment_{safe_name}.pkl")
    with open(path, "wb") as f:
        pickle.dump(model, f)
    print(f"  Model saved: {path}")
    return path


# ──────────────────────────────────────────────
# Plot Model Comparison Bar Chart
# ──────────────────────────────────────────────

def plot_model_comparison(df_results: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")

    models = df_results["Model"].tolist()
    macro_f1 = df_results["Macro-F1"].tolist()
    accuracies = df_results["Accuracy"].tolist()

    x = np.arange(len(models))
    w = 0.35
    bars1 = ax.bar(x - w / 2, macro_f1, w, label="Macro-F1", color="#3498db", edgecolor="white", linewidth=0.4)
    bars2 = ax.bar(x + w / 2, accuracies, w, label="Accuracy", color="#2ecc71", edgecolor="white", linewidth=0.4)

    for bars in [bars1, bars2]:
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.005,
                    f"{bar.get_height():.3f}", ha="center", va="bottom",
                    color="white", fontsize=8, fontweight="bold")

    ax.axhline(y=df_results[df_results["Model"] == "Majority-Class Baseline"]["Macro-F1"].values[0],
               color="#e74c3c", linestyle="--", linewidth=1.2, label="Baseline Macro-F1")

    ax.set_xticks(x)
    ax.set_xticklabels(models, color="white", fontsize=9, rotation=10, ha="right")
    ax.set_ylabel("Score", color="#aaa", fontsize=10)
    ax.set_title("Model Candidate Comparison (5-Fold CV on Train)", color="white", fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#333")
    ax.set_ylim(0, 1.0)
    ax.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white", fontsize=9)

    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "model_comparison.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  [Plot] Saved: {out}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def run_training(X_train, y_train) -> dict:
    df_results, winner_name, trained_candidates = run_model_comparison(
        X_train, y_train
    )
    plot_model_comparison(df_results)

    best_model = tune_winner(winner_name, X_train, y_train)
    model_path = save_model(best_model, winner_name)

    return {
        "comparison_df": df_results,
        "winner_name": winner_name,
        "best_model": best_model,
        "model_path": model_path,
        "trained_candidates": trained_candidates,
    }
