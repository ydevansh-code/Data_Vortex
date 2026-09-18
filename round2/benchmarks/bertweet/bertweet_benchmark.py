"""
bertweet_benchmark.py — Round 2
Data Vortex A'26 | Team: Event Horizon

Phase 5: Transformer Benchmarking (CLEAN VERSION)
- Uses same dedup pipeline as preprocess.py (fixes 308-row leakage root cause)
- Proper 70 / 10 / 20 three-way split: val used ONLY for early stopping
- Test set is truly held out and never seen during training or model selection
- Designed for Google Colab T4 / V100
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import torch

from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    f1_score, accuracy_score, classification_report,
    cohen_kappa_score, confusion_matrix,
)

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForSequenceClassification,
        Trainer,
        TrainingArguments,
        EarlyStoppingCallback,
    )
    from datasets import Dataset
except ImportError:
    print("Install: pip install transformers datasets")
    sys.exit(1)

RANDOM_STATE = 42
LABEL_MAP = {"Negative": 0, "Neutral": 1, "Positive": 2}
LABEL_NAMES = ["Negative", "Neutral", "Positive"]
MODEL_NAME = "vinai/bertweet-base"
MAX_LENGTH = 128


def load_and_dedup(data_path: str) -> pd.DataFrame:
    """Mirrors preprocess.load_and_audit: drop NaN, empty, and exact duplicates."""
    df = pd.read_csv(data_path, encoding="utf-8")
    df = df.dropna(subset=["post_text"])
    df = df[df["post_text"].str.strip() != ""]
    before = len(df)
    df = df.drop_duplicates(subset=["post_text"])
    print(f"  Rows after dedup: {len(df):,}  (removed {before - len(df)} exact duplicates)")
    return df


def make_splits(df: pd.DataFrame):
    """70% train / 10% val (early stopping only) / 20% test (final eval)."""
    X = df["post_text"].values
    y = df["label"].values

    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval,
        test_size=0.125,
        stratify=y_trainval,
        random_state=RANDOM_STATE,
    )

    print(f"  Train : {len(X_train):,}  |  Val : {len(X_val):,}  |  Test : {len(X_test):,}")

    train_overlap = set(X_train).intersection(set(X_test))
    val_overlap   = set(X_val).intersection(set(X_test))
    assert len(train_overlap) == 0, f"LEAKAGE: {len(train_overlap)} train/test overlaps!"
    assert len(val_overlap)   == 0, f"LEAKAGE: {len(val_overlap)} val/test overlaps!"
    print("  AUDIT PASSED: Zero text overlap across all three splits.")

    return X_train, X_val, X_test, y_train, y_val, y_test


def tokenize_dataset(texts, labels, tokenizer):
    ds = Dataset.from_dict({"text": texts, "label": labels})
    return ds.map(
        lambda batch: tokenizer(
            batch["text"],
            padding="max_length",
            truncation=True,
            max_length=MAX_LENGTH,
        ),
        batched=True,
    )


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "macro_f1": f1_score(labels, preds, average="macro"),
        "accuracy": accuracy_score(labels, preds),
    }


def main():
    print("=" * 70)
    print("BERTWEET CLEAN BENCHMARK — Data Vortex A'26 Round 2")
    print("=" * 70)

    data_path = "../Data/Labeled_Social_NLP_Training_Data.csv"
    if not os.path.exists(data_path):
        data_path = input("Path to Labeled_Social_NLP_Training_Data.csv: ").strip()

    print("\n[1] Loading & deduplicating...")
    df = load_and_dedup(data_path)
    df["label"] = df["sentiment_label"].map(LABEL_MAP)
    df = df.dropna(subset=["label"])

    print("\n[2] Creating clean 70/10/20 splits...")
    X_train, X_val, X_test, y_train, y_val, y_test = make_splits(df)

    print(f"\n[3] Loading tokenizer: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, normalization=True)

    print("[4] Tokenizing...")
    train_tok = tokenize_dataset(list(X_train), list(y_train), tokenizer)
    val_tok   = tokenize_dataset(list(X_val),   list(y_val),   tokenizer)
    test_tok  = tokenize_dataset(list(X_test),  list(y_test),  tokenizer)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"\n[5] Device: {device}")

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=3, ignore_mismatched_sizes=True
    )

    batch_size = 16
    training_args = TrainingArguments(
        output_dir="./results_bertweet_clean",
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=32,
        num_train_epochs=5,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="macro_f1",
        greater_is_better=True,
        logging_dir="./logs_bertweet",
        fp16=(device == "cuda"),
        seed=RANDOM_STATE,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_tok,
        eval_dataset=val_tok,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )

    print("\n[6] Training...")
    trainer.train()

    print("\n[7] Final evaluation on HELD-OUT test set...")
    test_preds_out = trainer.predict(test_tok)
    logits = test_preds_out.predictions
    y_pred = np.argmax(logits, axis=-1)

    probs = torch.softmax(torch.tensor(logits, dtype=torch.float32), dim=-1).numpy()

    macro_f1 = f1_score(y_test, y_pred, average="macro")
    acc      = accuracy_score(y_test, y_pred)
    kappa    = cohen_kappa_score(y_test, y_pred)

    print("\n" + "=" * 70)
    print("BERTWEET CLEAN TEST SET RESULTS")
    print("=" * 70)
    print(f"  Macro-F1  : {macro_f1:.4f}")
    print(f"  Accuracy  : {acc:.4f}")
    print(f"  Kappa     : {kappa:.4f}")
    print("\n" + classification_report(y_test, y_pred, target_names=LABEL_NAMES))
    print("Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    os.makedirs("../reports", exist_ok=True)
    preds_df = pd.DataFrame({
        "text":   X_test,
        "y_true": y_test,
        "y_pred": y_pred,
        "prob_Negative": probs[:, 0],
        "prob_Neutral":  probs[:, 1],
        "prob_Positive": probs[:, 2],
    })
    preds_csv = "../reports/bertweet_predictions.csv"
    preds_df.to_csv(preds_csv, index=False)
    print(f"\n  Predictions saved: {preds_csv}")

    summary = {
        "model": MODEL_NAME,
        "split": "70_10_20_clean_dedup",
        "macro_f1": round(macro_f1, 6),
        "accuracy": round(acc, 6),
        "kappa": round(kappa, 6),
        "test_size": len(X_test),
        "train_size": len(X_train),
        "val_size": len(X_val),
    }
    with open("../reports/bertweet_benchmark.json", "w") as f:
        json.dump(summary, f, indent=2)
    print(f"  Benchmark JSON saved: ../reports/bertweet_benchmark.json")

    try:
        from google.colab import files
        files.download(preds_csv)
        files.download("../reports/bertweet_benchmark.json")
        print("\n  Files downloading to your local machine...")
    except ImportError:
        print("\n  [Local run] Download files manually from the paths above.")

    print("\n  DONE. Share bertweet_predictions.csv to regenerate the full report.")


if __name__ == "__main__":
    main()
