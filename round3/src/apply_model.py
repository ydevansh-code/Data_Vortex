"""
apply_model.py - Round 2 Champion Model Scorer
Data Vortex A'26 | Team: Event Horizon

Loads round2/models/sentiment_linear_svm.pkl (TF-IDF + LinearSVC pipeline)
and scores every row in the processed dataset. Does NOT retrain.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pickle
import glob
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from config import DATA_PROC_DIR, MODEL_PATH, TOPIC_SLUG, SENTIMENT_MAP

def load_model():
    model_path = os.path.abspath(MODEL_PATH)
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model not found at: {model_path}\n"
            f"Ensure round2/models/sentiment_linear_svm.pkl exists."
        )
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    print(f"  [Model] Loaded: {os.path.basename(model_path)}")
    print(f"  [Model] Classes: {list(model.classes_)}")
    return model

def get_latest_processed_csv() -> str:
    files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_merged_*.csv")))
    if not files:
        raise FileNotFoundError(
            f"No processed CSV found in {DATA_PROC_DIR}. Run preprocess.py first."
        )
    return files[-1]

def apply_model(input_csv: str = None) -> pd.DataFrame:
    model = load_model()

    input_csv = input_csv or get_latest_processed_csv()
    print(f"  [Model] Scoring: {os.path.basename(input_csv)}")
    df = pd.read_csv(input_csv, low_memory=False)
    print(f"  [Model] {len(df):,} rows loaded")

    texts = df["text"].fillna("").astype(str).tolist()

    batch_size = 5000
    labels_all = []
    scores_all = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        preds = model.predict(batch)
        labels_all.extend(preds)

        try:
            decision_scores = model.decision_function(batch)
            if decision_scores.ndim == 1:
                scores_all.extend(decision_scores.tolist())
            else:
                max_scores = decision_scores.max(axis=1).tolist()
                scores_all.extend(max_scores)
        except Exception:
            scores_all.extend([0.0] * len(batch))

        if (i // batch_size) % 10 == 0:
            print(f"    Scored {min(i + batch_size, len(texts)):,}/{len(texts):,}")

    df["sentiment_label"] = labels_all
    df["sentiment_score"] = scores_all
    df["sentiment_numeric"] = df["sentiment_label"].map(SENTIMENT_MAP).fillna(0.5)

    dist = df["sentiment_label"].value_counts(normalize=True).to_dict()
    print(f"  [Model] Distribution: {dist}")

    ts_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_scored_{ts_label}.csv")
    df.to_csv(out_path, index=False)
    print(f"  [Model] Saved scored dataset -> {out_path}")
    return df

if __name__ == "__main__":
    print("=== Apply Round 2 Model ===")
    df = apply_model()
    print(df[["text", "sentiment_label", "sentiment_numeric"]].head(5))
