"""
kaggle_collector.py - Ingest, Filter, Translate, and Harmonize Kaggle Play Store Datasets
Data Vortex A'26 | Team: Event Horizon

Handles large external Kaggle CSVs (e.g. WhatsApp / Telegram Play Store Reviews).
Applies:
  1. Strict Date Range Filter: 2021-01-01 to 2021-07-31
  2. Noise Reduction Keyword Filter: Privacy, Policy, Security, Terms, Data Sharing, Migration terms (ID & EN)
  3. Sampling: Caps max rows per dataset to prevent API translation rate limits
  4. Batch Translation: Translates Indonesian (id) text to English (en) using deep_translator
  5. Harmonization: Standardizes columns to pipeline schema
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pandas as pd
from datetime import datetime, timezone
from config import DATA_RAW_DIR, COLL_LOG_PATH

try:
    from deep_translator import GoogleTranslator
    HAS_TRANSLATOR = True
except ImportError:
    HAS_TRANSLATOR = False

KAGGLE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kaggle")

# Keywords for noise filtering (English + Indonesian)
RELEVANT_KEYWORDS = [
    "privasi", "privacy", "kebijakan", "policy", "syarat", "terms", 
    "ketentuan", "tos", "data", "facebook", "fb", "telegram", "signal", 
    "pindah", "switch", "migrate", "update", "keamanan", "security", 
    "aturan", "ganti", "hapus", "delete", "akun", "account", "sharing", 
    "share", "ijin", "izin", "personal", "pribadi", "bocor", "leak"
]

def log_collection(source, query, count, status, run_ts=None):
    run_ts = run_ts or datetime.now(timezone.utc).isoformat()
    row = pd.DataFrame([{
        "timestamp": run_ts,
        "source": source,
        "query": query,
        "count": count,
        "status": status,
    }])
    if os.path.exists(COLL_LOG_PATH):
        row.to_csv(COLL_LOG_PATH, mode="a", header=False, index=False)
    else:
        os.makedirs(os.path.dirname(COLL_LOG_PATH), exist_ok=True)
        row.to_csv(COLL_LOG_PATH, index=False)

def translate_batch(texts, max_retries=3):
    """Translate a list of Indonesian texts to English using deep_translator."""
    if not HAS_TRANSLATOR:
        print("  [Kaggle] Warning: deep_translator not installed. Keeping original text.")
        return texts
    
    translator = GoogleTranslator(source='auto', target='en')
    translated = []
    print(f"  [Kaggle] Translating {len(texts):,} records to English...")
    
    for i, t in enumerate(texts):
        if not isinstance(t, str) or not t.strip():
            translated.append("")
            continue
        
        # Avoid unnecessary translation for short non-text
        if len(t) < 3:
            translated.append(t)
            continue

        res = t
        for attempt in range(max_retries):
            try:
                res = translator.translate(t)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    res = t
                time.sleep(0.5)
        
        translated.append(res)
        if (i + 1) % 100 == 0 or (i + 1) == len(texts):
            print(f"    Translated {i + 1}/{len(texts)} rows...")
            time.sleep(0.2) # Polite API delay
            
    return translated

def process_kaggle_csv(file_path: str, date_start="2021-01-01", date_end="2021-07-31", max_sample=3000):
    """Filter, sample, translate, and standardize a Kaggle review CSV."""
    if not os.path.exists(file_path):
        print(f"  [Kaggle] File not found: {file_path}")
        return pd.DataFrame()

    print(f"\n  [Kaggle] Reading dataset: {os.path.basename(file_path)}")
    df = pd.read_csv(file_path, low_memory=False)
    print(f"  [Kaggle] Raw row count: {len(df):,}")

    # Detect text column
    text_col = None
    for c in ["content", "review", "text", "body", "comment", "Review"]:
        if c in df.columns:
            text_col = c
            break
    if not text_col:
        print("  [Kaggle] Could not find text column in CSV!")
        return pd.DataFrame()

    # Detect date column
    date_col = None
    for c in ["at", "date", "created_at", "timestamp", "Time", "Date"]:
        if c in df.columns:
            date_col = c
            break
    if not date_col:
        print("  [Kaggle] Could not find date column in CSV!")
        return pd.DataFrame()

    # 1. Date Range Filtering
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce", utc=True)
    df = df.dropna(subset=[date_col])

    start_dt = pd.to_datetime(date_start, utc=True)
    end_dt = pd.to_datetime(date_end, utc=True)

    df_filtered = df[(df[date_col] >= start_dt) & (df[date_col] <= end_dt)].copy()
    print(f"  [Kaggle] Rows within 2021 date range ({date_start} to {date_end}): {len(df_filtered):,}")

    if df_filtered.empty:
        print("  [Kaggle] No rows match the specified date range.")
        return pd.DataFrame()

    # 2. Keyword / Noise Filtering
    pattern = "|".join(RELEVANT_KEYWORDS)
    df_filtered = df_filtered[df_filtered[text_col].astype(str).str.contains(pattern, case=False, na=False)]
    print(f"  [Kaggle] Rows matching privacy/policy/migration keywords: {len(df_filtered):,}")

    if df_filtered.empty:
        print("  [Kaggle] No rows match the privacy keyword filters.")
        return pd.DataFrame()

    # 3. Sampling to prevent API translation limits
    if len(df_filtered) > max_sample:
        df_filtered = df_filtered.sample(n=max_sample, random_state=42)
        print(f"  [Kaggle] Sampled down to {len(df_filtered):,} rows for processing & translation.")

    # 4. Translation
    translated_texts = translate_batch(df_filtered[text_col].tolist())
    df_filtered["translated_text"] = translated_texts

    # 5. Schema Harmonization
    app_source = "kaggle_whatsapp" if "whatsapp" in file_path.lower() else "kaggle_telegram"
    
    score_col = None
    for c in ["score", "rating", "star", "stars", "Rating"]:
        if c in df_filtered.columns:
            score_col = c
            break

    records = []
    for idx, row in df_filtered.iterrows():
        records.append({
            "post_id":           f"kaggle_{idx}",
            "source":            app_source,
            "text":              row["translated_text"],
            "url":               "https://kaggle.com/datasets",
            "timestamp":         row[date_col].isoformat(),
            "engagement_metric": float(row[score_col]) if score_col else 1.0,
            "country":           "ID", # Indonesian dataset
            "lang":              "id_en",
            "query_used":        "kaggle_play_store_reviews",
        })

    out_df = pd.DataFrame(records)
    
    # Save output
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    ts_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = os.path.join(DATA_RAW_DIR, f"{app_source}_{ts_label}.csv")
    out_df.to_csv(out_path, index=False)
    print(f"  [Kaggle] Saved {len(out_df):,} clean translated records -> {out_path}")
    
    log_collection(app_source, "kaggle_ingest", len(out_df), "OK")
    return out_df

def process_all_kaggle():
    """Scans the round3/data/kaggle directory for any CSV files and processes them."""
    if not os.path.exists(KAGGLE_DIR):
        os.makedirs(KAGGLE_DIR, exist_ok=True)
        print(f"  [Kaggle] Created folder: {KAGGLE_DIR}. Place Kaggle CSV files here!")
        return

    csv_files = [os.path.join(KAGGLE_DIR, f) for f in os.listdir(KAGGLE_DIR) if f.endswith(".csv")]
    if not csv_files:
        print(f"  [Kaggle] No CSV files found in {KAGGLE_DIR}.")
        return

    for f in csv_files:
        process_kaggle_csv(f)

if __name__ == "__main__":
    print("=== Kaggle Dataset Ingestion & Translation Collector ===")
    process_all_kaggle()
