"""
ablation_study.py — Round 2 (v3 DEFINITIVE)
Data Vortex A'26 | Team: Event Horizon

KEY BUGS FIXED FROM v1:
1. TfidfVectorizer had strip_accents='unicode' which re-normalised text AFTER caller
   preprocessing, making all configs produce identical feature matrices.
   Fix: lowercase=False, strip_accents=None — vectorizer trusts caller's text.
2. Emoji ablation was dead (0 emojis in corpus after stripping). Replaced with
   punctuation, hashtag (correctly decoupled from punct), mention retention, and bigrams.
3. Hashtag split is only meaningful when punctuation is KEPT (# is stripped by
   remove_punct regardless). Config design accounts for this interaction.
4. Degenerate guard: RAISES if any two configs produce identical text hashes.

DIMENSIONS TESTED (5 meaningfully-distinct configs):
  A: Champion pipeline (punct removed, hashtags split+stripped, mentions stripped)
  B: Keep punctuation  [? ! ... signals — sarcasm/emotion hypothesis]
  C: Keep hashtag symbol with punct retained [#Windows10Fail as one token]
  D: Retain @user token (mention density as signal)
  E: Bigrams only ngram=(2,2)  [unigram contribution]
"""

import os
import sys
import re
import hashlib
import json
import numpy as np
import pandas as pd

from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.model_selection import StratifiedKFold, cross_validate, train_test_split

sys.path.insert(0, os.path.dirname(__file__))
from preprocess import load_and_audit, RANDOM_STATE

DATA_PATH   = os.path.join(os.path.dirname(__file__), "..", "Data", "Labeled_Social_NLP_Training_Data.csv")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")

_URL_RE      = re.compile(r"https?://\S+|www\.\S+")
_HTML_RE     = re.compile(r"<[^>]+>|&amp;|&lt;|&gt;|&nbsp;|&quot;")
_MENTION_RE  = re.compile(r"@\w+")
_HASHTAG_RE  = re.compile(r"#(\w+)")
_PUNCT_RE    = re.compile(r"[^\w\s]")
_SPACE_RE    = re.compile(r"\s+")


def preprocess(text: str,
               remove_punct: bool = True,
               split_hashtags: bool = True,
               strip_mentions: bool = True) -> str:
    if not isinstance(text, str):
        return ""
    text = _HTML_RE.sub(" ", text)
    text = _URL_RE.sub(" URL ", text)
    if strip_mentions:
        text = _MENTION_RE.sub(" ", text)
    if split_hashtags:
        text = _HASHTAG_RE.sub(r" \1 ", text)
    else:
        text = _HASHTAG_RE.sub(r" #\1 ", text)
    text = text.lower()
    if remove_punct:
        text = _PUNCT_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def text_hash(texts):
    h = hashlib.md5()
    for t in texts:
        h.update(t.encode("utf-8", errors="replace"))
    return h.hexdigest()


def vocab_size(X_texts, min_df=3):
    vec = TfidfVectorizer(
        ngram_range=(1, 1), min_df=min_df, max_df=0.85,
        lowercase=False, strip_accents=None,
    )
    vec.fit(X_texts)
    return len(vec.vocabulary_)


def cv_score(X_texts, y, label, ngram_range=(1, 1), min_df=3):
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(
            ngram_range=ngram_range,
            min_df=min_df,
            max_df=0.85,
            sublinear_tf=True,
            lowercase=False,
            strip_accents=None,
        )),
        ("clf", LinearSVC(C=0.133, class_weight="balanced", max_iter=2000, random_state=RANDOM_STATE)),
    ])
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_validate(pipe, X_texts, y, cv=skf, scoring="f1_macro", n_jobs=-1)
    mean_f1 = scores["test_score"].mean()
    std_f1  = scores["test_score"].std()
    print(f"  macro-F1 = {mean_f1:.4f} ± {std_f1:.4f}  | {label}")
    return mean_f1, std_f1


def main():
    print("\n" + "=" * 70)
    print("ABLATION STUDY v3 (DEFINITIVE)")
    print("=" * 70)
    print("NOTE: corpus contains 0 emojis after basic stripping — emoji")
    print("      ablation removed; replaced with 4 informative dimensions.\n")

    df, _ = load_and_audit(DATA_PATH)
    y_all = df["sentiment_label"].values
    df_train, _, y_train, _ = train_test_split(
        df, y_all, test_size=0.20, stratify=y_all, random_state=RANDOM_STATE
    )
    raw_train = df_train["post_text"]

    configs = [
        {
            "label": "A: Champion pipeline (remove punct, split hashtags, strip mentions)",
            "remove_punct": True, "split_hashtags": True, "strip_mentions": True,
            "ngram": (1, 1), "min_df": 3, "text_varies": True,
        },
        {
            "label": "B: Keep punctuation",
            "remove_punct": False, "split_hashtags": True, "strip_mentions": True,
            "ngram": (1, 1), "min_df": 3, "text_varies": True,
        },
        {
            "label": "C: Keep hashtag symbol + keep punct (no split, # survives)",
            "remove_punct": False, "split_hashtags": False, "strip_mentions": True,
            "ngram": (1, 1), "min_df": 3, "text_varies": True,
        },
        {
            "label": "D: Retain mention token (@user)",
            "remove_punct": True, "split_hashtags": True, "strip_mentions": False,
            "ngram": (1, 1), "min_df": 3, "text_varies": True,
        },
        {
            "label": "E: Bigrams only (ngram=(2,2)) — same text as A, model variant",
            "remove_punct": True, "split_hashtags": True, "strip_mentions": True,
            "ngram": (2, 2), "min_df": 3, "text_varies": False,  # text == A intentionally
        },
    ]

    results      = []
    seen_hashes  = {}

    for cfg in configs:
        X = raw_train.apply(
            lambda t: preprocess(
                t,
                remove_punct=cfg["remove_punct"],
                split_hashtags=cfg["split_hashtags"],
                strip_mentions=cfg["strip_mentions"],
            )
        ).values

        th = text_hash(X)
        vs = vocab_size(X, min_df=cfg["min_df"])

        print(f"  [{cfg['label']}]")
        print(f"    text_hash={th[:16]}...  vocab_size={vs}")

        if cfg.get("text_varies", True):
            if th in seen_hashes:
                raise RuntimeError(
                    f"DEGENERATE ABLATION: '{cfg['label']}' == '{seen_hashes[th]}'. "
                    "Flags are not reaching the preprocessor. ABORT."
                )
            seen_hashes[th] = cfg["label"]

        mean_f1, std_f1 = cv_score(X, y_train, cfg["label"], ngram_range=cfg["ngram"], min_df=cfg["min_df"])
        results.append({
            "config_id": cfg["label"][0],
            "label":  cfg["label"],
            "text_hash_prefix": th[:16],
            "vocab_size": vs,
            "macro_f1_mean": round(mean_f1, 4),
            "macro_f1_std":  round(std_f1, 4),
        })
        print()

    vsizes = [r["vocab_size"] for r in results]
    if len(set(vsizes)) < 2:
        raise RuntimeError("VOCAB SIZES ALL IDENTICAL — vectorizer re-normalising text. Check lowercase/strip_accents.")

    baseline_f1 = results[0]["macro_f1_mean"]
    print("=" * 70)
    print("DELTA vs CHAMPION (config A):")
    for r in results[1:]:
        delta = r["macro_f1_mean"] - baseline_f1
        print(f"  {r['config_id']}: {delta:+.4f}")

    out = os.path.join(REPORTS_DIR, "ablation_results.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved: {out}")
    return results


if __name__ == "__main__":
    main()
