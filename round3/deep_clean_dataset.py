"""
deep_clean_dataset.py
Profiles and cleans the processed CSVs for Round 3 submission.
Focuses on: whatsapp_privacy_2021_merged_final.csv and the scored variant.
"""

import os
import re
import pandas as pd
import numpy as np
from datetime import datetime

BASE = os.path.join(os.path.dirname(__file__), "data", "processed")
REPORT_PATH = os.path.join(os.path.dirname(__file__), "reports", "data_quality_report.md")


def load_df(name):
    path = os.path.join(BASE, name)
    if not os.path.exists(path):
        print(f"  [SKIP] Not found: {path}")
        return None, path
    df = pd.read_csv(path, low_memory=False)
    print(f"  Loaded {name}: {len(df):,} rows x {df.shape[1]} cols")
    return df, path


def profile(df, name):
    issues = []
    rows_before = len(df)

    # 1. Exact duplicates on post_id
    if "post_id" in df.columns:
        dups = df.duplicated(subset=["post_id"]).sum()
        if dups:
            issues.append(f"  - Duplicate post_id: {dups:,} rows")
            df = df.drop_duplicates(subset=["post_id"], keep="first")

    # 2. Empty / null text
    if "text" in df.columns:
        null_text = df["text"].isna() | (df["text"].astype(str).str.strip() == "")
        n_null = null_text.sum()
        if n_null:
            issues.append(f"  - Empty text: {n_null:,} rows → dropped")
            df = df[~null_text].copy()

    # 3. Timestamp normalization — ensure all are ISO-8601 UTC
    if "timestamp" in df.columns:
        raw_ts = df["timestamp"].copy()
        parsed = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        bad_ts = parsed.isna().sum()
        if bad_ts:
            issues.append(f"  - Unparseable timestamps: {bad_ts:,} rows → set NaT")
        df["timestamp"] = parsed.dt.strftime("%Y-%m-%dT%H:%M:%SZ").where(parsed.notna(), other=None)

    # 4. Sentiment label / score mismatch
    if "sentiment_label" in df.columns and "sentiment_score" in df.columns:
        df["sentiment_score"] = pd.to_numeric(df["sentiment_score"], errors="coerce")
        pos_neg = ((df["sentiment_label"] == "Positive") & (df["sentiment_score"] < -0.3)).sum()
        neg_pos = ((df["sentiment_label"] == "Negative") & (df["sentiment_score"] > 0.5)).sum()
        total_mismatch = pos_neg + neg_pos
        if total_mismatch:
            issues.append(f"  - Sentiment label/score hard conflicts: {total_mismatch:,} (kept, flagged below)")
            df["sentiment_conflict"] = (
                ((df["sentiment_label"] == "Positive") & (df["sentiment_score"] < -0.3)) |
                ((df["sentiment_label"] == "Negative") & (df["sentiment_score"] > 0.5))
            ).astype(int)

    # 5. Source name normalization
    if "source_name" in df.columns:
        old_vals = df["source_name"].value_counts().to_dict()
        df["source_name"] = df["source_name"].replace({
            "whatsapp_playstore": "whatsapp",
            "kaggle_whatsapp": "whatsapp",
            "kaggle_telegram": "telegram",
        })
        new_vals = df["source_name"].value_counts().to_dict()
        changed = sum(old_vals.get(k, 0) != new_vals.get(k, 0) for k in old_vals)
        if changed:
            issues.append(f"  - source_name normalized ({changed} mappings updated)")

    # 6. Drop columns that are entirely null
    all_null_cols = [c for c in df.columns if df[c].isna().all()]
    if all_null_cols:
        df = df.drop(columns=all_null_cols)
        issues.append(f"  - Dropped {len(all_null_cols)} all-null columns: {all_null_cols}")

    # 7. Engagement metric clip — remove negatives
    if "engagement_metric" in df.columns:
        df["engagement_metric"] = pd.to_numeric(df["engagement_metric"], errors="coerce").fillna(0.0)
        neg_eng = (df["engagement_metric"] < 0).sum()
        if neg_eng:
            df["engagement_metric"] = df["engagement_metric"].clip(lower=0)
            issues.append(f"  - Negative engagement_metric: {neg_eng:,} → clipped to 0")

    rows_after = len(df)
    return df, issues, rows_before - rows_after


def write_report(results):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Data Quality Report — Round 3 Processed Datasets\n",
        f"Generated: {now}\n\n",
        "---\n",
    ]
    for name, issues, dropped in results:
        lines.append(f"## {name}\n")
        lines.append(f"- **Rows dropped:** {dropped:,}\n")
        if issues:
            lines.append("- **Issues found & fixed:**\n")
            for iss in issues:
                lines.append(f"{iss}\n")
        else:
            lines.append("- No issues found ✓\n")
        lines.append("\n")
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)
    print(f"  [OK] Quality report -> {REPORT_PATH}")


def run():
    print("=== Deep Clean — Round 3 Processed Datasets ===")
    targets = [
        "whatsapp_privacy_2021_merged_final.csv",
        "telegram_migration_clean.csv",
        "whatsapp_backlash_clean.csv",
    ]

    # Also grab the latest scored file
    import glob
    scored_files = sorted(glob.glob(os.path.join(BASE, "whatsapp_privacy_2021_scored_*.csv")))
    if scored_files:
        targets.append(os.path.basename(scored_files[-1]))

    results = []
    for name in targets:
        print(f"\n--- {name}")
        df, path = load_df(name)
        if df is None:
            continue
        df_clean, issues, dropped = profile(df, name)
        print(f"  Rows: {len(df_clean):,} (dropped {dropped})")
        for iss in issues:
            print(iss)
        # Save cleaned version back (overwrite)
        df_clean.to_csv(path, index=False)
        print(f"  [SAVED] -> {path}")
        results.append((name, issues, dropped))

    write_report(results)
    print("\n=== Done ===")


if __name__ == "__main__":
    run()
