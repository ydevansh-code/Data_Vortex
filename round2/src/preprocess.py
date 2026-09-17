"""
preprocess.py — Round 2 NLP Pipeline
Data Vortex A'26 | Team: Event Horizon

Handles: text cleaning, EDA visualizations, stratified train/test split.
No leakage: all transformations fitted on train set only.
"""

import re
import os
import time
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split

RANDOM_STATE = 42
DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
FIGURES_DIR = os.path.join(os.path.dirname(__file__), "..", "reports", "figures")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

# ──────────────────────────────────────────────
# Text Cleaning
# ──────────────────────────────────────────────

_URL_RE = re.compile(r"https?://\S+|www\.\S+")
_HTML_RE = re.compile(r"<[^>]+>|&amp;|&lt;|&gt;|&nbsp;|&quot;")
_MENTION_RE = re.compile(r"@\w+")
_HASHTAG_RE = re.compile(r"#(\w+)")
_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
    "\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF"
    "\u2600-\u26FF\u2700-\u27BF]+",
    flags=re.UNICODE,
)
_PUNCT_RE = re.compile(r'[^\w\s]')
_MULTI_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = _HTML_RE.sub(" ", text)
    text = _URL_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    text = _HASHTAG_RE.sub(r" \1 ", text)
    text = _EMOJI_RE.sub(" ", text)
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = _MULTI_SPACE_RE.sub(" ", text).strip()
    return text


# ──────────────────────────────────────────────
# Load & Audit Dataset
# ──────────────────────────────────────────────

def load_and_audit(path: str) -> tuple[pd.DataFrame, dict]:
    df = pd.read_csv(path, encoding="utf-8")
    audit = {}

    audit["raw_rows"] = len(df)
    audit["columns"] = list(df.columns)
    audit["label_counts"] = df["sentiment_label"].value_counts().to_dict()
    audit["topic_counts"] = df["topic_category"].value_counts().to_dict()

    missing_text = df["post_text"].isna().sum()
    audit["missing_text_rows"] = int(missing_text)
    df = df.dropna(subset=["post_text"])

    empty_after_strip = (df["post_text"].str.strip() == "").sum()
    audit["empty_text_rows"] = int(empty_after_strip)
    df = df[df["post_text"].str.strip() != ""]

    before_dedup = len(df)
    df = df.drop_duplicates(subset=["post_text"])
    audit["duplicate_rows_removed"] = before_dedup - len(df)

    audit["clean_rows"] = len(df)
    return df, audit


# ──────────────────────────────────────────────
# Apply Cleaning
# ──────────────────────────────────────────────

def apply_cleaning(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["cleaned_text"] = df["post_text"].apply(clean_text)
    df["word_count"] = df["cleaned_text"].apply(lambda x: len(x.split()))
    df["char_count"] = df["cleaned_text"].apply(len)
    empty_after_clean = (df["cleaned_text"].str.strip() == "").sum()
    df = df[df["cleaned_text"].str.strip() != ""]
    return df, empty_after_clean


# ──────────────────────────────────────────────
# EDA Visualizations
# ──────────────────────────────────────────────

PALETTE = {"Positive": "#2ecc71", "Negative": "#e74c3c", "Neutral": "#3498db"}
TOPIC_PALETTE = sns.color_palette("husl", 8)


def plot_class_distribution(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0f1117")
    for ax in axes:
        ax.set_facecolor("#1a1d2e")

    sent_counts = df["sentiment_label"].value_counts()
    colors = [PALETTE.get(l, "#888") for l in sent_counts.index]
    bars = axes[0].bar(sent_counts.index, sent_counts.values, color=colors, edgecolor="white", linewidth=0.4)
    for bar, val in zip(bars, sent_counts.values):
        axes[0].text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 30,
                     f"{val:,}", ha="center", va="bottom", color="white", fontsize=10, fontweight="bold")
    axes[0].set_title("Sentiment Label Distribution", color="white", fontsize=13, fontweight="bold", pad=12)
    axes[0].set_xlabel("Sentiment", color="#aaa", fontsize=10)
    axes[0].set_ylabel("Count", color="#aaa", fontsize=10)
    axes[0].tick_params(colors="white")
    axes[0].spines[:].set_color("#333")

    topic_counts = df["topic_category"].value_counts()
    bars2 = axes[1].barh(topic_counts.index, topic_counts.values,
                          color=TOPIC_PALETTE[:len(topic_counts)], edgecolor="white", linewidth=0.4)
    for bar, val in zip(bars2, topic_counts.values):
        axes[1].text(bar.get_width() + 20, bar.get_y() + bar.get_height() / 2,
                     f"{val:,}", va="center", color="white", fontsize=9, fontweight="bold")
    axes[1].set_title("Topic Category Distribution", color="white", fontsize=13, fontweight="bold", pad=12)
    axes[1].set_xlabel("Count", color="#aaa", fontsize=10)
    axes[1].tick_params(colors="white")
    axes[1].spines[:].set_color("#333")

    plt.tight_layout(pad=2.5)
    out = os.path.join(FIGURES_DIR, "class_distribution.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  [EDA] Saved: {out}")


def plot_text_length(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor("#0f1117")
    for ax in axes:
        ax.set_facecolor("#1a1d2e")

    for label, grp in df.groupby("sentiment_label"):
        color = PALETTE.get(label, "#888")
        axes[0].hist(grp["word_count"].clip(upper=80), bins=40, alpha=0.65,
                     label=label, color=color, edgecolor="none")
        axes[1].hist(grp["char_count"].clip(upper=400), bins=40, alpha=0.65,
                     label=label, color=color, edgecolor="none")

    for ax, title, xlabel in zip(
        axes,
        ["Word Count Distribution by Sentiment", "Character Count Distribution by Sentiment"],
        ["Word Count (clipped at 80)", "Character Count (clipped at 400)"],
    ):
        ax.set_title(title, color="white", fontsize=12, fontweight="bold", pad=10)
        ax.set_xlabel(xlabel, color="#aaa", fontsize=10)
        ax.set_ylabel("Frequency", color="#aaa", fontsize=10)
        ax.tick_params(colors="white")
        ax.spines[:].set_color("#333")
        ax.legend(facecolor="#1a1d2e", edgecolor="#555", labelcolor="white", fontsize=9)

    plt.tight_layout(pad=2.5)
    out = os.path.join(FIGURES_DIR, "text_length_hist.png")
    plt.savefig(out, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"  [EDA] Saved: {out}")


# ──────────────────────────────────────────────
# Train/Test Split
# ──────────────────────────────────────────────

def split_data(df: pd.DataFrame) -> tuple:
    X = df["cleaned_text"].values
    y_sent = df["sentiment_label"].values
    y_topic = df["topic_category"].values
    ids = df["text_id"].values
    raw_text = df["post_text"].values

    X_train, X_test, y_train, y_test, ids_train, ids_test, raw_train, raw_test = train_test_split(
        X, y_sent, ids, raw_text,
        test_size=0.20,
        stratify=y_sent,
        random_state=RANDOM_STATE,
    )
    return X_train, X_test, y_train, y_test, ids_train, ids_test, raw_train, raw_test


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def run_preprocessing() -> dict:
    print("\n" + "=" * 60)
    print("  STAGE 1: LOADING & AUDITING DATASET")
    print("=" * 60)
    df, audit = load_and_audit(DATA_PATH)
    print(f"  Raw rows        : {audit['raw_rows']:,}")
    print(f"  Missing text    : {audit['missing_text_rows']}")
    print(f"  Empty text      : {audit['empty_text_rows']}")
    print(f"  Duplicates rmvd : {audit['duplicate_rows_removed']}")
    print(f"  Clean rows      : {audit['clean_rows']:,}")
    print(f"  Sentiment dist  : {audit['label_counts']}")
    print(f"  Topic dist      : {audit['topic_counts']}")

    print("\n" + "=" * 60)
    print("  STAGE 2: TEXT CLEANING")
    print("=" * 60)
    df, empty_post_clean = apply_cleaning(df)
    print(f"  Empty after clean: {empty_post_clean}")
    print(f"  Final rows       : {len(df):,}")
    print(f"  Avg word count   : {df['word_count'].mean():.1f}")
    print(f"  Avg char count   : {df['char_count'].mean():.1f}")

    print("\n" + "=" * 60)
    print("  STAGE 3: EDA VISUALIZATIONS")
    print("=" * 60)
    plot_class_distribution(df)
    plot_text_length(df)

    print("\n" + "=" * 60)
    print("  STAGE 4: TRAIN / TEST SPLIT (80/20 stratified, seed=42)")
    print("=" * 60)
    X_train, X_test, y_train, y_test, ids_train, ids_test, raw_train, raw_test = split_data(df)
    print(f"  Train size : {len(X_train):,}")
    print(f"  Test size  : {len(X_test):,}")
    unique, counts = np.unique(y_train, return_counts=True)
    print("  Train label distribution:")
    for u, c in zip(unique, counts):
        print(f"    {u}: {c} ({c / len(y_train) * 100:.1f}%)")

    return {
        "df": df,
        "audit": audit,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "ids_test": ids_test,
        "raw_test": raw_test,
    }


if __name__ == "__main__":
    result = run_preprocessing()
