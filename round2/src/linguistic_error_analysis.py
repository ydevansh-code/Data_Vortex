"""
linguistic_error_analysis.py — Round 2
Data Vortex A'26 | Team: Event Horizon

Phase 7: Error Analysis Depth
- Linguistic rule-based error categorization
- Manual 50-sample label-noise audit generator
"""

import os
import sys
import numpy as np
import pandas as pd
import json
import re

from sklearn.model_selection import train_test_split

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, RANDOM_STATE
from optimize import LABELS

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
PREDS_PATH = os.path.join(REPORTS_DIR, "test_predictions.npz")

# Rules for Linguistic Categories
NEGATION_WORDS = {"not", "no", "never", "none", "nobody", "nowhere", "neither", "barely", "hardly", "scarcely", "without", "isn't", "aren't", "wasn't", "weren't", "haven't", "hasn't", "hadn't", "won't", "wouldn't", "don't", "doesn't", "didn't", "can't", "couldn't", "shouldn't", "mightn't", "mustn't"}
MODALITY_WORDS = {"would", "could", "should", "might", "may", "if", "wish", "hope", "wonder", "perhaps", "maybe", "probably"}
CONTRAST_WORDS = {"but", "however", "although", "though", "even though", "despite", "in spite of", "yet", "still"}

def categorize_error(text):
    text_lower = str(text).lower()
    words = set(re.findall(r'\b\w+\b', text_lower))
    
    categories = []
    
    if len(words.intersection(NEGATION_WORDS)) > 0:
        categories.append("Explicit Negation")
        
    if len(words.intersection(MODALITY_WORDS)) > 0:
        categories.append("Modality/Hypothetical")
        
    if len(words.intersection(CONTRAST_WORDS)) > 0:
        categories.append("Contrast/Shift")
        
    if "?" in text or "!" in text or "..." in text:
        categories.append("Punctuation Intensive (Possible Sarcasm/Emotion)")
        
    if len(categories) == 0:
        categories.append("No Distinct Linguistic Pattern")
        
    return categories

def main():
    print("=" * 70)
    print("LINGUISTIC ERROR CATEGORIZATION (Phase 7)")
    print("=" * 70)
    
    if not os.path.exists(PREDS_PATH):
        print(f"Error: {PREDS_PATH} not found. Run optimize.py first.")
        sys.exit(1)
        
    preds = np.load(PREDS_PATH, allow_pickle=True)
    y_true = preds["y_true"]
    y_pred = preds["y_pred"]
    
    # We need the original text
    df, _ = load_and_audit(DATA_PATH)
    _, df_test = train_test_split(
        df, test_size=0.20, stratify=df["sentiment_label"], random_state=RANDOM_STATE
    )
    
    # Make sure they align
    assert len(df_test) == len(y_true), "Data length mismatch!"
    
    # Get Errors
    error_mask = (y_true != y_pred)
    df_errors = df_test[error_mask].copy()
    df_errors["predicted_label"] = y_pred[error_mask]
    
    print(f"Total Errors Found: {len(df_errors)}")
    
    # Categorize
    all_categories = []
    for text in df_errors["post_text"]:
        cats = categorize_error(text)
        all_categories.extend(cats)
        
    from collections import Counter
    cat_counts = Counter(all_categories)
    
    print("\nLinguistic Rule-Based Error Categorization:")
    results = {}
    for cat, count in cat_counts.most_common():
        pct = count / len(df_errors)
        print(f"  {cat:<45} : {count} ({pct:.1%})")
        results[cat] = {"count": count, "percentage": round(pct, 4)}
        
    out_json = os.path.join(REPORTS_DIR, "linguistic_error_analysis.json")
    with open(out_json, "w") as f:
        json.dump(results, f, indent=2)
        
    # Generate 50-sample label noise audit
    print("\nGenerating 50-sample manual audit CSV...")
    if len(df_errors) > 50:
        audit_sample = df_errors.sample(n=50, random_state=RANDOM_STATE)
    else:
        audit_sample = df_errors
        
    audit_sample = audit_sample[["post_text", "sentiment_label", "predicted_label", "topic_category"]]
    audit_sample["manual_audit_correct_label"] = ""
    audit_sample["notes"] = ""
    
    out_csv = os.path.join(REPORTS_DIR, "label_noise_audit_50.csv")
    audit_sample.to_csv(out_csv, index=False)
    
    print(f"Saved: {out_json}")
    print(f"Saved: {out_csv}")

if __name__ == "__main__":
    main()
