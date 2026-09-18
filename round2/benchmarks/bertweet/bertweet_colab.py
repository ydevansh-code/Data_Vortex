"""
bertweet_colab.py — Self-contained Colab Script
Data Vortex A'26 | Team: Event Horizon

Run this as a single cell in Google Colab.
No local imports required.
Steps:
  1. Upload Labeled_Social_NLP_Training_Data.csv
  2. Dedup + clean 70/10/20 split
  3. Fine-tune BERTweet
  4. Evaluate on held-out test set
  5. Download predictions CSV + benchmark JSON
"""

import os
import json
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, accuracy_score, classification_report, cohen_kappa_score, confusion_matrix
from transformers import (
    AutoTokenizer, AutoModelForSequenceClassification,
    Trainer, TrainingArguments, EarlyStoppingCallback,
)
from datasets import Dataset
from google.colab import files as colab_files

RANDOM_STATE = 42
LABEL_MAP = {"Negative": 0, "Neutral": 1, "Positive": 2}
LABEL_NAMES = ["Negative", "Neutral", "Positive"]
MODEL_NAME = "vinai/bertweet-base"
MAX_LENGTH = 128

print("Upload Labeled_Social_NLP_Training_Data.csv")
uploaded = colab_files.upload()
data_path = list(uploaded.keys())[0]

df = pd.read_csv(data_path, encoding="utf-8")
df = df.dropna(subset=["post_text"])
df = df[df["post_text"].str.strip() != ""]
before = len(df)
df = df.drop_duplicates(subset=["post_text"])
print(f"Rows after dedup: {len(df):,}  (removed {before - len(df)} duplicates)")

df["label"] = df["sentiment_label"].map(LABEL_MAP)
df = df.dropna(subset=["label"])

X = df["post_text"].values
y = df["label"].values

X_trainval, X_test, y_trainval, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=RANDOM_STATE
)
X_train, X_val, y_train, y_val = train_test_split(
    X_trainval, y_trainval, test_size=0.125, stratify=y_trainval, random_state=RANDOM_STATE
)

train_overlap = set(X_train).intersection(set(X_test))
val_overlap   = set(X_val).intersection(set(X_test))
assert len(train_overlap) == 0, f"LEAKAGE: {len(train_overlap)} train/test overlaps!"
assert len(val_overlap)   == 0, f"LEAKAGE: {len(val_overlap)} val/test overlaps!"
print(f"AUDIT PASSED: Train={len(X_train)} | Val={len(X_val)} | Test={len(X_test)} | Zero overlap")

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, normalization=True)

def tokenize(texts, labels):
    ds = Dataset.from_dict({"text": list(texts), "label": list(labels)})
    return ds.map(
        lambda b: tokenizer(b["text"], padding="max_length", truncation=True, max_length=MAX_LENGTH),
        batched=True,
    )

train_tok = tokenize(X_train, y_train)
val_tok   = tokenize(X_val,   y_val)
test_tok  = tokenize(X_test,  y_test)

model = AutoModelForSequenceClassification.from_pretrained(
    MODEL_NAME, num_labels=3, ignore_mismatched_sizes=True
)

def compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=-1)
    return {
        "macro_f1": f1_score(labels, preds, average="macro"),
        "accuracy": accuracy_score(labels, preds),
    }

args = TrainingArguments(
    output_dir="./results_bertweet_clean",
    eval_strategy="epoch",
    save_strategy="epoch",
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=32,
    num_train_epochs=5,
    weight_decay=0.01,
    load_best_model_at_end=True,
    metric_for_best_model="macro_f1",
    greater_is_better=True,
    fp16=True,
    seed=RANDOM_STATE,
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=train_tok,
    eval_dataset=val_tok,
    compute_metrics=compute_metrics,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)

trainer.train()

test_out = trainer.predict(test_tok)
logits   = test_out.predictions
y_pred   = np.argmax(logits, axis=-1)
probs    = torch.softmax(torch.tensor(logits, dtype=torch.float32), dim=-1).numpy()

macro_f1 = f1_score(y_test, y_pred, average="macro")
acc      = accuracy_score(y_test, y_pred)
kappa    = cohen_kappa_score(y_test, y_pred)

print(f"\nMacro-F1 : {macro_f1:.4f}")
print(f"Accuracy  : {acc:.4f}")
print(f"Kappa     : {kappa:.4f}")
print(classification_report(y_test, y_pred, target_names=LABEL_NAMES))
print("Confusion Matrix:\n", confusion_matrix(y_test, y_pred))

preds_df = pd.DataFrame({
    "text":         X_test,
    "y_true":       y_test,
    "y_pred":       y_pred,
    "prob_Negative": probs[:, 0],
    "prob_Neutral":  probs[:, 1],
    "prob_Positive": probs[:, 2],
})
preds_df.to_csv("bertweet_predictions.csv", index=False)

summary = {
    "model": MODEL_NAME,
    "split": "70_10_20_clean_dedup",
    "macro_f1": round(float(macro_f1), 6),
    "accuracy": round(float(acc), 6),
    "kappa": round(float(kappa), 6),
    "test_size": int(len(X_test)),
    "train_size": int(len(X_train)),
    "val_size": int(len(X_val)),
}
with open("bertweet_benchmark.json", "w") as f:
    json.dump(summary, f, indent=2)

colab_files.download("bertweet_predictions.csv")
colab_files.download("bertweet_benchmark.json")
print("\nDONE. Save both files to round2/reports/ on your local machine.")
