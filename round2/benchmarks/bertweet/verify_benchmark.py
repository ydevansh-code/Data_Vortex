"""
verify_benchmark.py - BERTweet Benchmark Local Verifier
Data Vortex A'26 | Team: Event Horizon

PURPOSE: Allows a judge to verify the committed BERTweet benchmark numbers
         WITHOUT needing a GPU, Colab, or downloading any model weights.
         Simply recomputes classification metrics from the committed predictions CSV.

USAGE:   python verify_benchmark.py
"""

import os
import json
import sys

try:
    import pandas as pd
    from sklearn.metrics import f1_score, accuracy_score, cohen_kappa_score, classification_report
except ImportError:
    print("Install: pip install pandas scikit-learn")
    sys.exit(1)

DIR = os.path.dirname(os.path.abspath(__file__))
PREDS_CSV = os.path.join(DIR, "bertweet_predictions.csv")
JSON_FILE = os.path.join(DIR, "bertweet_benchmark.json")
LABEL_NAMES = ["Negative", "Neutral", "Positive"]

print("=" * 60)
print("  BERTweet Benchmark Local Verifier")
print("  Data Vortex A'26 - Team: Event Horizon")
print("=" * 60)

if not os.path.exists(PREDS_CSV):
    print(f"\nERROR: {PREDS_CSV} not found.")
    sys.exit(1)
if not os.path.exists(JSON_FILE):
    print(f"\nERROR: {JSON_FILE} not found.")
    sys.exit(1)

df = pd.read_csv(PREDS_CSV)
print(f"\n  Predictions file : {os.path.basename(PREDS_CSV)}")
print(f"  Rows             : {len(df):,}")

y_true = df["y_true"].values
y_pred = df["y_pred"].values

macro_f1 = f1_score(y_true, y_pred, average="macro")
accuracy  = accuracy_score(y_true, y_pred)
kappa     = cohen_kappa_score(y_true, y_pred)

print(f"\n  --- Recomputed Metrics ---")
print(f"  Macro-F1  : {macro_f1:.6f}")
print(f"  Accuracy  : {accuracy:.6f}")
print(f"  Kappa     : {kappa:.6f}")

with open(JSON_FILE, "r") as f:
    committed = json.load(f)

print(f"\n  --- Committed JSON Values ---")
print(f"  Macro-F1  : {committed['macro_f1']}")
print(f"  Accuracy  : {committed['accuracy']}")
print(f"  Kappa     : {committed['kappa']}")

tol = 1e-4
match = (
    abs(macro_f1 - committed["macro_f1"]) < tol and
    abs(accuracy  - committed["accuracy"])  < tol and
    abs(kappa     - committed["kappa"])     < tol
)

print(f"\n  JSON matches CSV  : {'TRUE - VERIFIED' if match else 'FALSE - MISMATCH DETECTED'}")

print(f"\n  --- Per-Class Breakdown ---")
print(classification_report(y_true, y_pred, target_names=LABEL_NAMES))

print("=" * 60)
if not match:
    sys.exit(1)
