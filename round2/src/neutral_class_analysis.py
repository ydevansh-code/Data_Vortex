"""
neutral_class_analysis.py — Round 2
Data Vortex A'26 | Team: Event Horizon

Phase 4: Neutral Class Problem
- Threshold optimization for the Neutral class.
- Topic-confounding Mutual Information test.
"""

import os
import sys
import numpy as np
import pandas as pd
import json

from sklearn.metrics import f1_score, accuracy_score
from sklearn.metrics import mutual_info_score

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, RANDOM_STATE
from optimize import LABELS

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
PREDS_PATH = os.path.join(REPORTS_DIR, "test_predictions.npz")

def optimize_thresholds(y_true, y_proba):
    print("\n" + "=" * 70)
    print("THRESHOLD OPTIMIZATION")
    print("=" * 70)
    
    # We will vary the threshold for the Neutral class (index 1)
    neutral_idx = LABELS.index("Neutral")
    
    best_thresh = 0.5
    best_macro_f1 = 0.0
    best_neutral_f1 = 0.0
    best_preds = None
    
    # Standard argmax prediction (default)
    y_pred_default = np.array([LABELS[i] for i in np.argmax(y_proba, axis=1)])
    default_macro_f1 = f1_score(y_true, y_pred_default, average="macro")
    
    print(f"  Default Macro-F1 (argmax): {default_macro_f1:.4f}")
    
    thresholds = np.linspace(0.2, 0.6, 41)
    
    for t in thresholds:
        preds = []
        for prob in y_proba:
            if prob[neutral_idx] >= t:
                preds.append("Neutral")
            else:
                # If not neutral, pick the max of the remaining
                if prob[0] > prob[2]:
                    preds.append("Negative")
                else:
                    preds.append("Positive")
        
        preds = np.array(preds)
        macro_f1 = f1_score(y_true, preds, average="macro")
        
        # Calculate specific F1 for Neutral
        tp = np.sum((preds == "Neutral") & (y_true == "Neutral"))
        fp = np.sum((preds == "Neutral") & (y_true != "Neutral"))
        fn = np.sum((preds != "Neutral") & (y_true == "Neutral"))
        prec = tp / (tp + fp) if tp + fp > 0 else 0
        rec = tp / (tp + fn) if tp + fn > 0 else 0
        neutral_f1 = 2 * prec * rec / (prec + rec) if prec + rec > 0 else 0
        
        if macro_f1 > best_macro_f1:
            best_macro_f1 = macro_f1
            best_thresh = t
            best_neutral_f1 = neutral_f1
            best_preds = preds
            
    print(f"\n  Optimized Threshold for Neutral: {best_thresh:.3f}")
    print(f"  Optimized Macro-F1             : {best_macro_f1:.4f} (Delta: {best_macro_f1 - default_macro_f1:+.4f})")
    print(f"  Optimized Neutral F1           : {best_neutral_f1:.4f}")
    
    return best_thresh, best_macro_f1, best_macro_f1 - default_macro_f1

def topic_confounding_test(y_true, y_pred_default):
    print("\n" + "=" * 70)
    print("TOPIC CONFOUNDING MUTUAL INFORMATION TEST")
    print("=" * 70)
    
    # Load dataset to get topics for the test set
    df, _ = load_and_audit(DATA_PATH)
    from sklearn.model_selection import train_test_split
    _, df_test = train_test_split(df, test_size=0.20, stratify=df["sentiment_label"], random_state=RANDOM_STATE)
    
    topics = df_test["topic_category"].values
    
    # Define error flag
    is_error = (y_true != y_pred_default).astype(int)
    
    # MI between topic and error
    mi = mutual_info_score(topics, is_error)
    print(f"  Mutual Information (Topic vs Error) : {mi:.4f}")
    
    # Error rate per topic
    print("\n  Error Rate by Topic:")
    rows = []
    for topic in np.unique(topics):
        mask = (topics == topic)
        err_rate = np.mean(is_error[mask])
        print(f"    {topic:<25}: {err_rate:.2%}")
        rows.append({"topic": topic, "error_rate": err_rate})
        
    return mi, rows

def main():
    if not os.path.exists(PREDS_PATH):
        print(f"Error: {PREDS_PATH} not found. Run optimize.py first.")
        sys.exit(1)
        
    preds = np.load(PREDS_PATH, allow_pickle=True)
    y_true = preds["y_true"]
    y_pred = preds["y_pred"]
    y_proba = preds["y_proba"]
    
    thresh, best_macro_f1, delta_f1 = optimize_thresholds(y_true, y_proba)
    mi, err_rates = topic_confounding_test(y_true, y_pred)
    
    results = {
        "neutral_threshold_opt": {
            "best_threshold": round(thresh, 3),
            "best_macro_f1": round(best_macro_f1, 4),
            "delta_macro_f1": round(delta_f1, 4)
        },
        "topic_confounding": {
            "mutual_information": round(mi, 4),
            "error_rates": err_rates
        }
    }
    
    out = os.path.join(REPORTS_DIR, "neutral_class_analysis.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved analysis results to {out}")

if __name__ == "__main__":
    main()
