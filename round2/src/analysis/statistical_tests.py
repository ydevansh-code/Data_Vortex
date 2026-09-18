"""
statistical_tests.py — Round 2
Data Vortex A'26 | Team: Event Horizon

Implements Phase 2: Methodological Flaws
- McNemar's Test for significance between two models on the same test set.
- 5x2cv Paired t-test for unbiased generalization estimation.
"""

import os
import sys
import numpy as np
import pandas as pd
from scipy import stats
import json

from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.metrics import f1_score
from sklearn.base import clone

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, apply_cleaning, RANDOM_STATE
from optimize import make_calibrated_svm, LABELS

DATA_PATH    = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
REPORTS_DIR  = os.path.join(os.path.dirname(__file__), "..", "reports")

def mcnemars_test(y_true, y_pred1, y_pred2, alpha=0.05):
    """
    McNemar's test with Edwards continuity correction.
    Checks if model 1 and model 2 have a statistically significant difference in errors.
    """
    # Create contingency table
    # n00: both correct
    # n01: m1 correct, m2 wrong
    # n10: m1 wrong, m2 correct
    # n11: both wrong
    
    m1_correct = (y_pred1 == y_true)
    m2_correct = (y_pred2 == y_true)
    
    n01 = np.sum(m1_correct & ~m2_correct)
    n10 = np.sum(~m1_correct & m2_correct)
    
    print("\n" + "=" * 70)
    print("MCNEMAR'S TEST")
    print("=" * 70)
    print(f"  Model 1 only correct : {n01}")
    print(f"  Model 2 only correct : {n10}")
    
    if n01 + n10 == 0:
        print("  Models have identical errors. Cannot compute McNemar's.")
        return 1.0, False
        
    # Edwards continuity correction
    chi2 = (abs(n01 - n10) - 1)**2 / (n01 + n10)
    p_value = stats.chi2.sf(chi2, 1)
    
    print(f"  Chi-squared : {chi2:.4f}")
    print(f"  p-value     : {p_value:.6f}")
    
    significant = p_value < alpha
    print(f"  Result      : {'Significant Difference ✅' if significant else 'No Significant Difference ❌'} (alpha={alpha})")
    
    return p_value, significant

def paired_ttest_5x2cv(estimator1, estimator2, X, y, scoring, random_seed=None):
    """
    5x2cv Paired t-test proposed by Dietterich (1998).
    """
    rng = np.random.RandomState(random_seed)
    
    variance_sum = 0.0
    first_diff = None
    
    print("\n" + "=" * 70)
    print("5x2cv PAIRED T-TEST")
    print("=" * 70)
    
    diffs_all = []
    
    for i in range(5):
        # 2-fold CV
        idx = np.arange(len(X))
        rng.shuffle(idx)
        split = len(X) // 2
        
        idx_A, idx_B = idx[:split], idx[split:]
        
        # Fold 1
        est1_A = clone(estimator1).fit(X[idx_A], y[idx_A])
        est2_A = clone(estimator2).fit(X[idx_A], y[idx_A])
        score1_B = scoring(y[idx_B], est1_A.predict(X[idx_B]))
        score2_B = scoring(y[idx_B], est2_A.predict(X[idx_B]))
        diff_B = score1_B - score2_B
        
        # Fold 2
        est1_B = clone(estimator1).fit(X[idx_B], y[idx_B])
        est2_B = clone(estimator2).fit(X[idx_B], y[idx_B])
        score1_A = scoring(y[idx_A], est1_B.predict(X[idx_A]))
        score2_A = scoring(y[idx_A], est2_B.predict(X[idx_A]))
        diff_A = score1_A - score2_A
        
        diff_mean = (diff_A + diff_B) / 2.0
        diff_var = (diff_A - diff_mean)**2 + (diff_B - diff_mean)**2
        variance_sum += diff_var
        
        diffs_all.extend([diff_A, diff_B])
        
        if i == 0:
            first_diff = diff_A
            
        print(f"  Iteration {i+1} - Diff Fold 1: {diff_B:.4f}, Diff Fold 2: {diff_A:.4f}")
            
    numerator = first_diff
    denominator = np.sqrt(variance_sum / 5.0)
    
    if denominator == 0:
        t_stat = 0.0
        p_value = 1.0
    else:
        t_stat = numerator / denominator
        p_value = stats.t.sf(np.abs(t_stat), 5) * 2.0
        
    print(f"\n  Mean Difference : {np.mean(diffs_all):.4f}")
    print(f"  t-statistic     : {t_stat:.4f}")
    print(f"  p-value         : {p_value:.6f}")
    
    significant = p_value < 0.05
    print(f"  Result          : {'Significant Difference ✅' if significant else 'No Significant Difference ❌'}")
    
    return p_value, significant

def main():
    df, _ = load_and_audit(DATA_PATH)
    df, _ = apply_cleaning(df)
    X_all = df["cleaned_text"].values
    y_all = df["sentiment_label"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X_all, y_all, test_size=0.20, stratify=y_all, random_state=RANDOM_STATE
    )

    from optimize import make_baseline_svm
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline
    from optimize import _tfidf
    
    print("Fitting models for McNemar's test...")
    # Model 1: CalibratedSVC (Our champion)
    model1 = make_calibrated_svm("balanced")
    model1.fit(X_train, y_train)
    y_pred1 = model1.predict(X_test)
    
    # Model 2: Logistic Regression (Close second in CV)
    model2 = Pipeline([
        ("tfidf", _tfidf()),
        ("clf", LogisticRegression(C=1.0, max_iter=1000, solver="lbfgs",
                                   class_weight="balanced",
                                   random_state=RANDOM_STATE, n_jobs=-1)),
    ])
    model2.fit(X_train, y_train)
    y_pred2 = model2.predict(X_test)
    
    p_mcnemar, sig_mcnemar = mcnemars_test(y_test, y_pred1, y_pred2)
    
    # 5x2cv paired t-test
    def scorer(y_t, y_p):
        return f1_score(y_t, y_p, average="macro")
        
    p_5x2cv, sig_5x2cv = paired_ttest_5x2cv(
        model1, model2, X_train, y_train, scorer, random_seed=RANDOM_STATE
    )
    
    results = {
        "mcnemar_p_value": p_mcnemar,
        "mcnemar_significant": bool(sig_mcnemar),
        "5x2cv_p_value": p_5x2cv,
        "5x2cv_significant": bool(sig_5x2cv)
    }
    
    out = os.path.join(REPORTS_DIR, "statistical_tests.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved statistical test results to {out}")

if __name__ == "__main__":
    main()
