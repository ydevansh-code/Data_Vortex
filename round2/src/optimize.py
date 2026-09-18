"""
optimize.py — Round 2 NLP Staged Optimization
Data Vortex A'26 | Team: Event Horizon

Implements plan from round2_improvement_plan.md (Hours 0-2):
  Step 1 — CalibratedClassifierCV wrapper (unblocks ROC/PR/calibration)
  Step 2 — Negation scope tagging in preprocessing
  Step 3 — Char n-gram FeatureUnion (word + char_wb)
  Step 4 — RandomizedSearchCV (joint vectorizer + classifier)
  Step 5 — balanced vs unbalanced class_weight CV test

All tuning and comparison done on TRAIN data via 5-fold CV.
Test set is touched ONCE at the very end for the final reported number.
"""

import os
import sys
import re
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

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import (
    StratifiedKFold, cross_validate, RandomizedSearchCV, train_test_split
)
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score,
    classification_report, confusion_matrix,
    roc_auc_score, average_precision_score,
    roc_curve, precision_recall_curve,
    cohen_kappa_score, matthews_corrcoef,
)
from sklearn.preprocessing import label_binarize
from scipy.stats import loguniform

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, apply_cleaning, RANDOM_STATE

DATA_PATH    = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
MODELS_DIR   = os.path.join(os.path.dirname(__file__), "..", "models")
FIGURES_DIR  = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
REPORTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

LABELS = ["Negative", "Neutral", "Positive"]

# ══════════════════════════════════════════════════════════════════════════════
# NEGATION TAGGING  (Part 2.4 of plan)
# Source: Pang et al. 2002 "Thumbs up? Sentiment Classification using ML"
# ══════════════════════════════════════════════════════════════════════════════

NEGATION_CUES = {
    "not", "no", "never", "neither", "nor", "nobody", "nothing",
    "nowhere", "hardly", "barely", "scarcely", "n't", "nt",
    "without", "cannot", "cant", "wont", "dont", "doesnt",
    "didnt", "isnt", "wasnt", "shouldnt", "wouldnt", "couldnt",
}
_SENT_END = re.compile(r"[.!?,;:]")


def apply_negation_scope(text: str) -> str:
    tokens = text.split()
    result = []
    negating = False
    for tok in tokens:
        if tok.lower() in NEGATION_CUES:
            negating = True
            result.append(tok)
        elif _SENT_END.search(tok):
            negating = False
            result.append(tok)
        elif negating:
            result.append("NEGATED_" + tok)
        else:
            result.append(tok)
    return " ".join(result)


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _tfidf(**overrides):
    base = dict(
        ngram_range=(1, 2),
        max_features=50_000,
        sublinear_tf=True,
        min_df=2,
        max_df=0.90,
        strip_accents="unicode",
    )
    base.update(overrides)
    return TfidfVectorizer(**base)


def make_baseline_svm(class_weight="balanced") -> Pipeline:
    return Pipeline([
        ("tfidf", _tfidf()),
        ("clf", LinearSVC(C=1.0, max_iter=2000,
                          class_weight=class_weight, random_state=RANDOM_STATE)),
    ])


def make_calibrated_svm(class_weight="balanced") -> Pipeline:
    return Pipeline([
        ("tfidf", _tfidf()),
        ("clf", CalibratedClassifierCV(
            LinearSVC(C=1.0, max_iter=2000,
                      class_weight=class_weight, random_state=RANDOM_STATE),
            cv=3, method="sigmoid")),
    ])


def make_char_union_svm(class_weight="balanced") -> Pipeline:
    return Pipeline([
        ("features", FeatureUnion([
            ("word", _tfidf()),
            ("char", _tfidf(
                analyzer="char_wb",
                ngram_range=(3, 5),
                max_features=30_000,
                sublinear_tf=True,
                min_df=3,
                max_df=0.95,
                strip_accents=None,
            )),
        ])),
        ("clf", LinearSVC(C=1.0, max_iter=2000,
                          class_weight=class_weight, random_state=RANDOM_STATE)),
    ])


def make_calibrated_char_union_svm(class_weight="balanced") -> Pipeline:
    return Pipeline([
        ("features", FeatureUnion([
            ("word", _tfidf()),
            ("char", _tfidf(
                analyzer="char_wb",
                ngram_range=(3, 5),
                max_features=30_000,
                sublinear_tf=True,
                min_df=3,
                max_df=0.95,
                strip_accents=None,
            )),
        ])),
        ("clf", CalibratedClassifierCV(
            LinearSVC(C=1.0, max_iter=2000,
                      class_weight=class_weight, random_state=RANDOM_STATE),
            cv=3, method="sigmoid")),
    ])


# ══════════════════════════════════════════════════════════════════════════════
# CV COMPARISON HELPER
# ══════════════════════════════════════════════════════════════════════════════

def cv_score(pipe, X, y, n_splits=5, label="") -> dict:
    skf = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    t0 = time.time()
    scores = cross_validate(
        pipe, X, y, cv=skf,
        scoring=["f1_macro", "f1_weighted", "accuracy"],
        n_jobs=-1, return_train_score=False,
    )
    elapsed = time.time() - t0
    res = {
        "label": label,
        "macro_f1_mean": scores["test_f1_macro"].mean(),
        "macro_f1_std":  scores["test_f1_macro"].std(),
        "accuracy_mean": scores["test_accuracy"].mean(),
        "accuracy_std":  scores["test_accuracy"].std(),
        "time_s":        elapsed,
    }
    print(f"  {label:<45}  macro-F1 = {res['macro_f1_mean']:.4f} ± {res['macro_f1_std']:.4f}"
          f"  acc = {res['accuracy_mean']:.4f}  ({elapsed:.1f}s)")
    return res


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Load & split data
# ══════════════════════════════════════════════════════════════════════════════

def load_data():
    print("\n" + "=" * 70)
    print("LOADING & SPLITTING DATA")
    print("=" * 70)
    df, audit = load_and_audit(DATA_PATH)
    df, _ = apply_cleaning(df)
    X_all = df["cleaned_text"].values
    y_all = df["sentiment_label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=0.20,
        stratify=y_all, random_state=RANDOM_STATE,
    )
    print(f"  Train: {len(X_train):,}   Test: {len(X_test):,}")
    print(f"  Label dist: {dict(zip(*np.unique(y_train, return_counts=True)))}")
    return X_train, X_test, y_train, y_test, df


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Balanced vs Unbalanced class_weight CV test
# ══════════════════════════════════════════════════════════════════════════════

def step_balanced_vs_unbalanced(X_train, y_train):
    print("\n" + "=" * 70)
    print("STEP 2 — class_weight: balanced vs None (5-fold CV)")
    print("=" * 70)
    results = []
    for cw, label in [("balanced", "LinearSVC balanced"), (None, "LinearSVC unbalanced")]:
        r = cv_score(make_baseline_svm(cw), X_train, y_train, label=label)
        results.append(r)

    winner_cw = "balanced" if results[0]["macro_f1_mean"] >= results[1]["macro_f1_mean"] else None
    delta = abs(results[0]["macro_f1_mean"] - results[1]["macro_f1_mean"])
    print(f"\n  Winner: class_weight={winner_cw!r}  (delta = {delta*100:.2f} macro-F1 pts)")
    return winner_cw, results


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — Negation tagging
# ══════════════════════════════════════════════════════════════════════════════

def step_negation(X_train, y_train, winner_cw):
    print("\n" + "=" * 70)
    print("STEP 3 — Negation scope tagging (5-fold CV)")
    print("=" * 70)

    X_train_neg = np.array([apply_negation_scope(t) for t in X_train])

    r_base = cv_score(make_baseline_svm(winner_cw), X_train, y_train,
                      label="LinearSVC (no negation tagging)")
    r_neg  = cv_score(make_baseline_svm(winner_cw), X_train_neg, y_train,
                      label="LinearSVC + negation tagging")

    delta = r_neg["macro_f1_mean"] - r_base["macro_f1_mean"]
    print(f"\n  Delta from negation tagging: {delta*100:+.2f} macro-F1 pts")
    use_negation = delta > 0.003  # keep if > 0.3 points
    print(f"  Decision: {'KEEP negation tagging ✅' if use_negation else 'DISCARD — not helpful enough ❌'}")
    return use_negation, X_train_neg


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Char n-gram FeatureUnion
# ══════════════════════════════════════════════════════════════════════════════

def step_char_ngrams(X_train, y_train, winner_cw):
    print("\n" + "=" * 70)
    print("STEP 4 — Word + Char n-gram FeatureUnion (5-fold CV)")
    print("=" * 70)

    r_word = cv_score(make_baseline_svm(winner_cw), X_train, y_train,
                      label="LinearSVC word only")
    r_char = cv_score(make_char_union_svm(winner_cw), X_train, y_train,
                      label="LinearSVC word + char_wb(3-5)")

    delta = r_char["macro_f1_mean"] - r_word["macro_f1_mean"]
    print(f"\n  Delta from char n-grams: {delta*100:+.2f} macro-F1 pts")
    use_char = delta > 0.003
    print(f"  Decision: {'KEEP char n-grams ✅' if use_char else 'DISCARD ❌'}")
    return use_char


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — RandomizedSearchCV (joint TF-IDF + classifier)
# ══════════════════════════════════════════════════════════════════════════════

def step_random_search(X_train, y_train, use_char, winner_cw):
    print("\n" + "=" * 70)
    print("STEP 5 — RandomizedSearchCV  (n_iter=40, 5-fold CV, ~5-8 min)")
    print("=" * 70)

    if use_char:
        pipe = Pipeline([
            ("features", FeatureUnion([
                ("word", TfidfVectorizer(strip_accents="unicode", sublinear_tf=True)),
                ("char", TfidfVectorizer(analyzer="char_wb", sublinear_tf=True, strip_accents=None)),
            ])),
            ("clf", LinearSVC(max_iter=2000, class_weight=winner_cw, random_state=RANDOM_STATE)),
        ])
        param_dist = {
            "features__word__ngram_range": [(1, 1), (1, 2), (1, 3)],
            "features__word__max_features": [30_000, 50_000, None],
            "features__word__min_df": [1, 2, 3],
            "features__word__max_df": [0.85, 0.90, 0.95],
            "features__char__ngram_range": [(3, 4), (3, 5), (2, 5)],
            "features__char__max_features": [20_000, 30_000, 50_000],
            "features__char__min_df": [2, 3, 5],
            "clf__C": loguniform(0.01, 10),
        }
    else:
        pipe = Pipeline([
            ("tfidf", TfidfVectorizer(strip_accents="unicode", sublinear_tf=True)),
            ("clf",   LinearSVC(max_iter=2000, class_weight=winner_cw, random_state=RANDOM_STATE)),
        ])
        param_dist = {
            "tfidf__ngram_range":   [(1, 1), (1, 2), (1, 3)],
            "tfidf__max_features":  [30_000, 50_000, None],
            "tfidf__min_df":        [1, 2, 3],
            "tfidf__max_df":        [0.85, 0.90, 0.95],
            "clf__C":               loguniform(0.01, 10),
        }

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    search = RandomizedSearchCV(
        pipe, param_dist,
        n_iter=40,
        scoring="f1_macro",
        cv=skf,
        n_jobs=-1,
        random_state=RANDOM_STATE,
        verbose=1,
        refit=True,
    )
    t0 = time.time()
    search.fit(X_train, y_train)
    elapsed = time.time() - t0

    print(f"\n  Search complete in {elapsed:.1f}s")
    print(f"  Best CV macro-F1 : {search.best_score_:.4f}")
    print(f"  Best params      : {search.best_params_}")
    return search


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Full model comparison (all candidates, same 5 CV folds)
# ══════════════════════════════════════════════════════════════════════════════

def step_full_model_comparison(X_train, y_train, winner_cw):
    print("\n" + "=" * 70)
    print("STEP 6 — Full Model Benchmark (5-fold CV, same folds)")
    print("=" * 70)

    candidates = {
        "Majority-Class Baseline": Pipeline([
            ("tfidf", _tfidf(max_features=1)),
            ("clf",   __import__("sklearn.dummy", fromlist=["DummyClassifier"])
                      .DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)),
        ]),
        "LinearSVC (current)": make_baseline_svm(winner_cw),
        "LogisticRegression": Pipeline([
            ("tfidf", _tfidf()),
            ("clf", LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs",
                                       class_weight=winner_cw,
                                       random_state=RANDOM_STATE, n_jobs=-1)),
        ]),
        "ComplementNB": Pipeline([
            ("tfidf", _tfidf(sublinear_tf=False)),
            ("clf", ComplementNB(alpha=0.3)),
        ]),
        "LinearSVC + char_wb": make_char_union_svm(winner_cw),
        "CalibratedSVC": make_calibrated_svm(winner_cw),
    }

    rows = []
    for name, pipe in candidates.items():
        r = cv_score(pipe, X_train, y_train, label=name)
        rows.append({
            "Model": name,
            "CV Macro-F1": f"{r['macro_f1_mean']:.4f} ± {r['macro_f1_std']:.4f}",
            "CV Accuracy": f"{r['accuracy_mean']:.4f} ± {r['accuracy_std']:.4f}",
            "_f1": r["macro_f1_mean"],
        })

    df_cmp = pd.DataFrame(rows).sort_values("_f1", ascending=False).drop(columns="_f1")
    print("\n" + df_cmp.to_string(index=False))
    return df_cmp


# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Final evaluation on test set (ONE TIME ONLY)
# ══════════════════════════════════════════════════════════════════════════════

def step_final_test_eval(best_pipe, X_train, y_train, X_test, y_test,
                         model_name: str, use_negation: bool):
    print("\n" + "=" * 70)
    print(f"STEP 7 — FINAL TEST SET EVALUATION  [{model_name}]")
    print("⚠️  Test set touched ONCE — this is the number you report.")
    print("=" * 70)

    best_pipe.fit(X_train, y_train)

    if use_negation:
        X_test_eval = np.array([apply_negation_scope(t) for t in X_test])
    else:
        X_test_eval = X_test

    y_pred = best_pipe.predict(X_test_eval)
    y_proba = best_pipe.predict_proba(X_test_eval) if hasattr(best_pipe, "predict_proba") else None

    acc      = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro")
    weighted_f1 = f1_score(y_test, y_pred, average="weighted")
    kappa    = cohen_kappa_score(y_test, y_pred)
    mcc      = matthews_corrcoef(y_test, y_pred)

    print(f"\n  Accuracy      : {acc:.4f}")
    print(f"  Macro-F1      : {macro_f1:.4f}")
    print(f"  Weighted-F1   : {weighted_f1:.4f}")
    print(f"  Cohen's Kappa : {kappa:.4f}")
    print(f"  MCC           : {mcc:.4f}")
    print(f"\n{classification_report(y_test, y_pred, labels=LABELS, zero_division=0)}")

    return y_pred, y_proba, {
        "accuracy": acc, "macro_f1": macro_f1, "weighted_f1": weighted_f1,
        "kappa": kappa, "mcc": mcc,
    }


# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — Plots (confusion matrix, per-class ROC/PR, feature importance)
# ══════════════════════════════════════════════════════════════════════════════

def plot_confusion_matrix_dual(y_test, y_pred, model_name: str):
    cm = confusion_matrix(y_test, y_pred, labels=LABELS)
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
        sns.heatmap(data, annot=True, fmt=fmt, cmap="Blues",
                    xticklabels=LABELS, yticklabels=LABELS,
                    linewidths=0.5, linecolor="#333", ax=ax, cbar=True,
                    annot_kws={"size": 11, "weight": "bold", "color": "black"})
        ax.set_title(title, color="white", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel("Predicted Label", color="#aaa", fontsize=10)
        ax.set_ylabel("True Label", color="#aaa", fontsize=10)
        ax.tick_params(colors="white")

    plt.suptitle(f"Model: {model_name}", color="#aaa", fontsize=10, y=1.02)
    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "confusion_matrix_v2.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")
    return out


def plot_roc_pr(best_pipe, X_test_eval, y_test):
    if not hasattr(best_pipe, "predict_proba"):
        print("  Model has no predict_proba — skipping ROC/PR curves.")
        return
    y_proba = best_pipe.predict_proba(X_test_eval)
    y_bin   = label_binarize(y_test, classes=LABELS)
    colors  = ["#e74c3c", "#3498db", "#2ecc71"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0f1117")
    for ax in axes:
        ax.set_facecolor("#1a1d2e")

    for i, (lbl, col) in enumerate(zip(LABELS, colors)):
        fpr, tpr, _ = roc_curve(y_bin[:, i], y_proba[:, i])
        auc = roc_auc_score(y_bin[:, i], y_proba[:, i])
        axes[0].plot(fpr, tpr, label=f"{lbl} (AUC={auc:.3f})", color=col, lw=2)

        prec, rec, _ = precision_recall_curve(y_bin[:, i], y_proba[:, i])
        ap = average_precision_score(y_bin[:, i], y_proba[:, i])
        axes[1].plot(rec, prec, label=f"{lbl} (AP={ap:.3f})", color=col, lw=2)

    axes[0].plot([0, 1], [0, 1], "w--", lw=1)
    for ax, title, xlabel, ylabel in zip(
        axes,
        ["Per-Class ROC Curves (One-vs-Rest)", "Per-Class Precision-Recall Curves"],
        ["False Positive Rate", "Recall"],
        ["True Positive Rate", "Precision"],
    ):
        ax.set_title(title, color="white", fontsize=11, fontweight="bold")
        ax.set_xlabel(xlabel, color="#aaa")
        ax.set_ylabel(ylabel, color="#aaa")
        ax.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white", fontsize=9)
        ax.tick_params(colors="white")
        ax.spines[:].set_color("#333")

    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "roc_pr_curves.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")


def plot_feature_importance(best_pipe, top_n=15):
    try:
        if "features" in best_pipe.named_steps:
            tfidf = best_pipe.named_steps["features"].transformer_list[0][1]
        else:
            tfidf = best_pipe.named_steps["tfidf"]

        clf = best_pipe.named_steps["clf"]
        if hasattr(clf, "calibrated_classifiers_"):
            coef = clf.calibrated_classifiers_[0].estimator.coef_
        elif hasattr(clf, "coef_"):
            coef = clf.coef_
        else:
            print("  Cannot extract linear coefficients from this model."); return
    except Exception as e:
        print(f"  Feature importance plot skipped: {e}"); return

    try:
        vocab = tfidf.get_feature_names_out()
    except Exception:
        print("  Vocabulary not available for feature importance plot."); return

    colors_neg, color_pos = "#e74c3c", "#2ecc71"
    fig, axes = plt.subplots(1, len(LABELS), figsize=(18, 6))
    fig.patch.set_facecolor("#0f1117")

    for i, (label, ax) in enumerate(zip(LABELS, axes)):
        ax.set_facecolor("#1a1d2e")
        if len(coef) == 1:
            weights = coef[0] if i == 2 else -coef[0]
        else:
            weights = coef[i]

        top_pos_idx = np.argsort(weights)[-top_n:][::-1]
        top_neg_idx = np.argsort(weights)[:top_n]
        half = top_n // 2
        idxs = list(top_neg_idx[:half]) + list(top_pos_idx[:half])
        feats = [vocab[j] for j in idxs]
        vals  = [weights[j] for j in idxs]
        c_bars = [colors_neg if v < 0 else color_pos for v in vals]

        ax.barh(feats, vals, color=c_bars, edgecolor="white", linewidth=0.3)
        ax.axvline(0, color="white", linewidth=0.8)
        ax.set_title(f"Top Features: {label}", color="white", fontweight="bold", fontsize=10)
        ax.tick_params(colors="white", labelsize=8)
        ax.spines[:].set_color("#333")

    plt.suptitle("Linear Classifier Feature Importance by Class",
                 color="white", fontsize=12, fontweight="bold")
    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "feature_importance.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")


def plot_model_comparison_chart(df_cmp: pd.DataFrame):
    models   = df_cmp["Model"].tolist()
    f1_means = [float(v.split("±")[0].strip()) for v in df_cmp["CV Macro-F1"]]
    f1_stds  = [float(v.split("±")[1].strip()) for v in df_cmp["CV Macro-F1"]]

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0f1117")
    ax.set_facecolor("#1a1d2e")

    colors = ["#888888" if m == "Majority-Class Baseline" else "#3498db" for m in models]
    bars = ax.bar(models, f1_means, color=colors, edgecolor="white", linewidth=0.4,
                  yerr=f1_stds, capsize=4, error_kw={"ecolor": "white", "linewidth": 1.2})

    for bar, val, std in zip(bars, f1_means, f1_stds):
        ax.text(bar.get_x() + bar.get_width() / 2, val + std + 0.008,
                f"{val:.4f}", ha="center", va="bottom",
                color="white", fontsize=8, fontweight="bold")

    ax.set_xticks(range(len(models)))
    ax.set_xticklabels(models, color="white", fontsize=9, rotation=20, ha="right")
    ax.set_ylabel("CV Macro-F1 (mean ± std)", color="#aaa", fontsize=10)
    ax.set_title("Model Comparison — 5-Fold Stratified CV", color="white",
                 fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors="white")
    ax.spines[:].set_color("#333")
    ax.set_ylim(0, max(f1_means) + 0.12)

    plt.tight_layout(pad=2)
    out = os.path.join(FIGURES_DIR, "model_comparison_cv.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  Saved: {out}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 9 — Save everything for report
# ══════════════════════════════════════════════════════════════════════════════

def save_optimization_results(metrics: dict, search_best_params: dict,
                               df_cmp: pd.DataFrame, model_name: str,
                               use_negation: bool, use_char: bool,
                               winner_cw: str):
    out = {
        "model_name": model_name,
        "use_negation_tagging": use_negation,
        "use_char_ngrams": use_char,
        "class_weight": winner_cw,
        "best_search_params": search_best_params,
        "test_metrics": metrics,
        "model_comparison_cv": df_cmp.to_dict(orient="records"),
    }
    path = os.path.join(REPORTS_DIR, "optimization_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"  Optimization results saved: {path}")
    return path


# ══════════════════════════════════════════════════════════════════════════════
# MAIN  — supports --resume flag to skip already-completed Steps 2-5
# ══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true",
                        help="Skip Steps 2-5 (already ran). Use hardcoded best params.")
    args, _ = parser.parse_known_args()

    t_total = time.time()
    print("""
╔══════════════════════════════════════════════════════════════╗
║   DATA VORTEX A'26 — ROUND 2: OPTIMIZATION PIPELINE         ║
║   Team: Event Horizon  |  Hours 0-6 of Improvement Plan     ║
╚══════════════════════════════════════════════════════════════╝
""")

    X_train, X_test, y_train, y_test, df = load_data()

    if args.resume:
        # ── Results already confirmed from first run ──
        # Step 2: balanced wins (delta=0.01 pts)
        # Step 3: negation tagging HURTS (-1.24 pts) — skip
        # Step 4: char n-grams neutral (0.00 pts) — skip
        # Step 5: best params from RandomizedSearch:
        #   C=0.133, max_df=0.85, max_features=None, min_df=3, ngram_range=(1,1)
        #   Best CV macro-F1 = 0.5863
        winner_cw    = "balanced"
        use_negation = False
        use_char     = False
        X_train_active = X_train

        print("  [RESUME] Skipping Steps 2-5 — using confirmed best params.")
        print(f"  class_weight   : {winner_cw}")
        print(f"  negation_tag   : OFF (hurt by -1.24 macro-F1 pts)")
        print(f"  char_ngrams    : OFF (0.00 delta)")
        print(f"  Best search    : C=0.133, ngram=(1,1), min_df=3, max_df=0.85, max_features=None")

        best_pipe = Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 1),
                max_features=None,
                sublinear_tf=True,
                min_df=3,
                max_df=0.85,
                strip_accents="unicode",
            )),
            ("clf", CalibratedClassifierCV(
                LinearSVC(C=0.133, max_iter=2000,
                          class_weight="balanced", random_state=RANDOM_STATE),
                cv=3, method="sigmoid")),
        ])
        search_params = {
            "clf__C": 0.133, "tfidf__max_df": 0.85,
            "tfidf__max_features": None, "tfidf__min_df": 3,
            "tfidf__ngram_range": "(1, 1)",
        }

    else:
        winner_cw, _ = step_balanced_vs_unbalanced(X_train, y_train)

        use_negation, X_train_neg = step_negation(X_train, y_train, winner_cw)
        X_train_active = X_train_neg if use_negation else X_train

        use_char = step_char_ngrams(X_train_active, y_train, winner_cw)

        search = step_random_search(X_train_active, y_train, use_char, winner_cw)
        best_pipe = search.best_estimator_
        search_params = {str(k): str(v) for k, v in search.best_params_.items()}

        # Wrap best estimator in CalibratedClassifierCV if not already
        if use_char:
            best_pipe_cal = Pipeline([
                ("features", best_pipe.named_steps["features"]),
                ("clf", CalibratedClassifierCV(
                    best_pipe.named_steps["clf"], cv=3, method="sigmoid")),
            ])
        else:
            best_pipe_cal = Pipeline([
                ("tfidf", best_pipe.named_steps["tfidf"]),
                ("clf", CalibratedClassifierCV(
                    best_pipe.named_steps["clf"], cv=3, method="sigmoid")),
            ])
        best_pipe = best_pipe_cal

    best_model_name = "Tuned LinearSVC (Calibrated, ngram=(1,1), C=0.133)"

    df_cmp = step_full_model_comparison(X_train_active, y_train, winner_cw)

    print("\n" + "=" * 70)
    print("PLOTS — Model Comparison Chart")
    print("=" * 70)
    plot_model_comparison_chart(df_cmp)

    y_pred, y_proba, test_metrics = step_final_test_eval(
        best_pipe, X_train_active, y_train,
        X_test, y_test, best_model_name, use_negation
    )

    X_test_eval = X_test  # negation is OFF

    print("\n" + "=" * 70)
    print("PLOTS — Confusion Matrix, ROC/PR, Feature Importance")
    print("=" * 70)
    plot_confusion_matrix_dual(y_test, y_pred, best_model_name)
    plot_roc_pr(best_pipe, X_test_eval, y_test)
    plot_feature_importance(best_pipe, top_n=12)

    save_optimization_results(
        test_metrics, search_params, df_cmp,
        best_model_name, use_negation, use_char, str(winner_cw),
    )
    
    predictions_path = os.path.join(REPORTS_DIR, "test_predictions.npz")
    np.savez(predictions_path, y_true=y_test, y_pred=y_pred, y_proba=y_proba)
    print(f"  Test predictions saved: {predictions_path}")

    model_path = os.path.join(MODELS_DIR, "sentiment_optimized.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(best_pipe, f)
    print(f"\n  Best model saved: {model_path}")

    elapsed = time.time() - t_total
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║  OPTIMIZATION COMPLETE  ({elapsed:.0f}s)
║  Negation tagging : {'ON ✅' if use_negation else 'OFF (hurts) ❌'}
║  Char n-grams     : {'ON ✅' if use_char else 'OFF (neutral) ❌'}
║  class_weight     : {winner_cw}
║  Test Macro-F1    : {test_metrics['macro_f1']:.4f}
║  Test Accuracy    : {test_metrics['accuracy']:.4f}
║  Cohen's Kappa    : {test_metrics['kappa']:.4f}
╚══════════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
