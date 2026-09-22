"""
preprocess.py - Multi-Source Data Merger & Cleaner
Data Vortex A'26 | Team: Event Horizon

Merges all raw CSVs from data/raw/ into one unified schema,
deduplicates, drops empty/non-text rows, normalizes timestamps to UTC ISO8601.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re
import glob
import pandas as pd
from datetime import datetime, timezone
from config import DATA_RAW_DIR, DATA_PROC_DIR, TOPIC_SLUG, DATE_START, DATE_END

REQUIRED_COLS = ["post_id", "source", "text", "timestamp", "engagement_metric"]

def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"#(\w+)", r"\1", text)
    text = re.sub(r"[^\x00-\x7F]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def normalize_timestamp(ts_raw) -> str:
    if pd.isna(ts_raw) or ts_raw == "":
        return ""
    try:
        parsed = pd.to_datetime(ts_raw, utc=True)
        return parsed.isoformat()
    except Exception:
        return ""

def load_raw_csvs() -> pd.DataFrame:
    csv_files = glob.glob(os.path.join(DATA_RAW_DIR, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {DATA_RAW_DIR}. Run collectors first.")

    frames = []
    for f in csv_files:
        try:
            df = pd.read_csv(f, low_memory=False)
            for col in REQUIRED_COLS:
                if col not in df.columns:
                    df[col] = ""
            frames.append(df[REQUIRED_COLS + [c for c in df.columns if c not in REQUIRED_COLS]])
            print(f"  Loaded {len(df):,} rows from {os.path.basename(f)}")
        except Exception as e:
            print(f"  SKIP {os.path.basename(f)}: {e}")

    if not frames:
        raise ValueError("All CSV files failed to load.")

    return pd.concat(frames, ignore_index=True)

def preprocess() -> pd.DataFrame:
    os.makedirs(DATA_PROC_DIR, exist_ok=True)
    print("[Preprocess] Loading raw CSVs ...")
    df = load_raw_csvs()
    print(f"  Total raw rows: {len(df):,}")

    df["text"] = df["text"].apply(clean_text)
    df = df[df["text"].str.len() >= 10].copy()
    print(f"  After text filter (>=10 chars): {len(df):,}")

    df["timestamp"] = df["timestamp"].apply(normalize_timestamp)
    df = df[df["timestamp"] != ""].copy()
    print(f"  After timestamp filter: {len(df):,}")

    df["ts_parsed"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    date_start_dt = pd.Timestamp(DATE_START, tz="UTC")
    date_end_dt   = pd.Timestamp(DATE_END,   tz="UTC") + pd.Timedelta(days=1)
    df = df[(df["ts_parsed"] >= date_start_dt) & (df["ts_parsed"] <= date_end_dt)].copy()
    print(f"  After date range filter ({DATE_START} - {DATE_END}): {len(df):,}")

    df.drop_duplicates(subset=["post_id"], inplace=True)
    print(f"  After dedup (post_id): {len(df):,}")

    df["engagement_metric"] = pd.to_numeric(df["engagement_metric"], errors="coerce").fillna(0.0)

    df.sort_values("ts_parsed", inplace=True)
    df.reset_index(drop=True, inplace=True)

    ts_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_merged_{ts_label}.csv")
    df.drop(columns=["ts_parsed"]).to_csv(out_path, index=False)
    print(f"[Preprocess] Saved {len(df):,} rows -> {out_path}")
    return df

if __name__ == "__main__":
    print("=== Preprocessor ===")
    df = preprocess()
    print(df["source"].value_counts())
