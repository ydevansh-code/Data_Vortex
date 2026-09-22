"""
primary_pipeline.py - Primary Dataset Processor & Translation Pipeline
Data Vortex A'26 | Team: Event Horizon

Reads large playstore CSVs in chunks.
Filters by date, score, and keywords before expensive translation.
Uses MarianMT (Helsinki-NLP/opus-mt-id-en) for local translation.
Merges with bonus live-scraped data to output combined_dataset.csv.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glob
import re
import argparse
import pandas as pd
from datetime import datetime, timezone
import torch
from transformers import MarianMTModel, MarianTokenizer

from config import DATA_RAW_DIR, DATA_PROC_DIR, KEYWORDS_ID, KEYWORDS

def get_marian_translator():
    print("  [Model] Loading Helsinki-NLP/opus-mt-id-en ...")
    model_name = "Helsinki-NLP/opus-mt-id-en"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    
    return {"model": model, "tokenizer": tokenizer, "device": device}

def batch_translate(texts, translator, batch_size=32):
    model = translator["model"]
    tokenizer = translator["tokenizer"]
    device = translator["device"]
    
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        try:
            inputs = tokenizer(batch, return_tensors="pt", padding=True, truncation=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            translated = model.generate(**inputs)
            tgt_text = [tokenizer.decode(t, skip_special_tokens=True) for t in translated]
            results.extend(tgt_text)
        except Exception as e:
            print(f"    [Translate Error] {e}")
            results.extend(["" for _ in batch])
    return results

def process_whatsapp(translator, sample=False):
    print("\n--- Processing WhatsApp Primary Data ---")
    files = glob.glob(os.path.join(DATA_RAW_DIR, "playstore_com.whatsapp_*.csv"))
    if not files:
        print("  [Error] No WhatsApp raw data found.")
        return pd.DataFrame()
    
    filepath = files[0]
    print(f"  [Input] {os.path.basename(filepath)}")
    
    # 1. Read Data
    if sample:
        df = pd.read_csv(filepath, nrows=5000)
    else:
        # Since we filter heavily, we can read chunks
        chunks = []
        for chunk in pd.read_csv(filepath, chunksize=100000, low_memory=False):
            chunks.append(chunk)
        df = pd.concat(chunks, ignore_index=True)
        
    print(f"  [Stats] Initial rows: {len(df):,}")
    
    # Clean text column
    df['content'] = df['content'].fillna("").astype(str)
    
    # 2. Date Filter: Jan 1 2021 to Jun 30 2021
    df['at_dt'] = pd.to_datetime(df['at'], errors='coerce', utc=True)
    df = df.dropna(subset=['at_dt'])
    
    start_dt = pd.to_datetime("2020-11-01", utc=True)
    end_dt = pd.to_datetime("2021-07-31", utc=True)
    
    df = df[(df['at_dt'] >= start_dt) & (df['at_dt'] <= end_dt)]
    print(f"  [Stats] After Date Filter (Jan-Jun 2021): {len(df):,}")
    
    # 3. Rating filter: score <= 2
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    df = df[df['score'] <= 2]
    print(f"  [Stats] After Score Filter (<= 2): {len(df):,}")
    
    # 4. Keyword filter (Backlash)
    kw_pattern = "|".join([re.escape(k) for k in KEYWORDS_ID + ["privacy", "data", "facebook", "share", "policy", "terms", "privasi", "kebijakan"]])
    df['matched'] = df['content'].str.contains(kw_pattern, case=False, na=False)
    df_filtered = df[df['matched']].copy()
    print(f"  [Stats] After Keyword Filter: {len(df_filtered):,}")
    
    if len(df_filtered) == 0:
        return pd.DataFrame()
        
    # 5. Translation
    print(f"  [Translating] {len(df_filtered):,} rows...")
    df_filtered['translated_text'] = batch_translate(df_filtered['content'].tolist(), translator)
    
    # 6. Formatting
    out_df = pd.DataFrame({
        "post_id": df_filtered["reviewId"],
        "source": "whatsapp",
        "source_type": "primary_dataset",
        "source_name": "whatsapp_playstore",
        "text": df_filtered["translated_text"],
        "timestamp": df_filtered["at_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engagement_metric": df_filtered["thumbsUpCount"] if "thumbsUpCount" in df_filtered else 0.0,
        "lang": "en",
        "backlash_flag": 1
    })
    
    # Clean output texts
    out_df["text"] = out_df["text"].str.replace(r"http\S+", "", regex=True)
    out_df["text"] = out_df["text"].str.replace(r"[^\x00-\x7F]+", " ", regex=True)
    out_df["text"] = out_df["text"].str.replace(r"\s+", " ", regex=True).str.strip()
    out_df = out_df[out_df["text"].str.len() >= 5]
    
    out_path = os.path.join(DATA_PROC_DIR, "whatsapp_backlash_clean.csv")
    os.makedirs(DATA_PROC_DIR, exist_ok=True)
    out_df.to_csv(out_path, index=False)
    print(f"  [Output] Saved {len(out_df):,} rows -> {out_path}")
    
    return out_df

def process_telegram(translator, sample=False):
    print("\n--- Processing Telegram Primary Data ---")
    files = glob.glob(os.path.join(DATA_RAW_DIR, "Telegram_Review_Cleaned.csv"))
    if not files:
        print("  [Error] No Telegram raw data found.")
        return pd.DataFrame()
    
    filepath = files[0]
    print(f"  [Input] {os.path.basename(filepath)}")
    
    try:
        from langdetect import detect
    except ImportError:
        print("  [Warn] langdetect not installed. Will translate all non-ascii.")
        detect = lambda x: 'en'
        
    if sample:
        df = pd.read_csv(filepath, nrows=5000)
    else:
        df = pd.read_csv(filepath, low_memory=False)
        
    print(f"  [Stats] Initial rows: {len(df):,}")
    
    df['content'] = df['content'].fillna("").astype(str)
    
    # 2. Date Filter: Jan 1 2021 to Jul 31 2021
    df['at_dt'] = pd.to_datetime(df['at'], errors='coerce', utc=True)
    df = df.dropna(subset=['at_dt'])
    
    start_dt = pd.to_datetime("2020-11-01", utc=True)
    end_dt = pd.to_datetime("2021-07-31", utc=True)
    
    df = df[(df['at_dt'] >= start_dt) & (df['at_dt'] <= end_dt)]
    print(f"  [Stats] After Date Filter (Jan-Jul 2021): {len(df):,}")
    
    # 3. Rating filter: score >= 4 (Migration positive reviews)
    df['score'] = pd.to_numeric(df['score'], errors='coerce')
    df = df[df['score'] >= 4]
    print(f"  [Stats] After Score Filter (>= 4): {len(df):,}")
    
    # 4. Keyword filter (Migration)
    kw_pattern = "|".join([re.escape(k) for k in ["whatsapp", "switch", "privacy", "data", "facebook", "better", "signal", "pindah"]])
    df['matched'] = df['content'].str.contains(kw_pattern, case=False, na=False)
    df_filtered = df[df['matched']].copy()
    print(f"  [Stats] After Keyword Filter: {len(df_filtered):,}")
    
    if len(df_filtered) == 0:
        return pd.DataFrame()
        
    # 5. Language Detection & Translation
    def safe_detect(text):
        if len(text) < 10: return 'en'
        try: return detect(text)
        except: return 'en'
        
    print("  [LangDetect] Detecting languages...")
    df_filtered['lang'] = df_filtered['content'].apply(safe_detect)
    
    non_en = df_filtered[df_filtered['lang'] != 'en']
    print(f"  [Translating] {len(non_en):,} non-English rows...")
    
    translated_map = {}
    if len(non_en) > 0:
        translated_texts = batch_translate(non_en['content'].tolist(), translator)
        for idx, trans in zip(non_en.index, translated_texts):
            translated_map[idx] = trans
            
    def get_final_text(row):
        if row.name in translated_map:
            return translated_map[row.name]
        return row['content']
        
    df_filtered['translated_text'] = df_filtered.apply(get_final_text, axis=1)
    
    # 6. Formatting
    out_df = pd.DataFrame({
        "post_id": df_filtered["reviewId"],
        "source": "telegram",
        "source_type": "primary_dataset",
        "source_name": "telegram_playstore",
        "text": df_filtered["translated_text"],
        "timestamp": df_filtered["at_dt"].dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engagement_metric": df_filtered["thumbsUpCount"] if "thumbsUpCount" in df_filtered else 0.0,
        "lang": "en",
        "migration_flag": 1
    })
    
    out_df["text"] = out_df["text"].str.replace(r"http\S+", "", regex=True)
    out_df["text"] = out_df["text"].str.replace(r"[^\x00-\x7F]+", " ", regex=True)
    out_df["text"] = out_df["text"].str.replace(r"\s+", " ", regex=True).str.strip()
    out_df = out_df[out_df["text"].str.len() >= 5]
    
    out_path = os.path.join(DATA_PROC_DIR, "telegram_migration_clean.csv")
    out_df.to_csv(out_path, index=False)
    print(f"  [Output] Saved {len(out_df):,} rows -> {out_path}")
    
    return out_df

def merge_bonus_data():
    print("\n--- Merging Bonus Live Data ---")
    bonus_files = glob.glob(os.path.join(DATA_RAW_DIR, "gdelt_live_stream*.csv")) + \
                  glob.glob(os.path.join(DATA_RAW_DIR, "hn_*.csv")) + \
                  glob.glob(os.path.join(DATA_RAW_DIR, "google_play_*.csv"))
    
    frames = []
    for f in bonus_files:
        try:
            df = pd.read_csv(f)
            # Ensure required columns
            for col in ["post_id", "source", "source_type", "source_name", "text", "timestamp", "engagement_metric", "lang"]:
                if col not in df.columns:
                    df[col] = ""
                    
            if "source_type" in df.columns and len(df) > 0 and pd.isna(df["source_type"].iloc[0]):
                df["source_type"] = "bonus_live_scraped"
                df["source_name"] = df["source"]
                
            frames.append(df)
            print(f"  [Merged Bonus] {os.path.basename(f)} ({len(df)} rows)")
        except Exception as e:
            pass
            
    if frames:
        return pd.concat(frames, ignore_index=True)
    return pd.DataFrame()

def run_pipeline(sample=False):
    print("=== Data Vortex R3 — Primary Pipeline ===")
    
    try:
        translator = get_marian_translator()
    except Exception as e:
        print(f"  [Error] Failed to load translator: {e}. Check if transformers and sentencepiece are installed.")
        return
        
    df_wa = process_whatsapp(translator, sample=sample)
    df_tg = process_telegram(translator, sample=sample)
    df_bonus = merge_bonus_data()
    
    frames = []
    if len(df_wa) > 0: frames.append(df_wa)
    if len(df_tg) > 0: frames.append(df_tg)
    if len(df_bonus) > 0: frames.append(df_bonus)
    
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        # Add flags to missing rows
        if "backlash_flag" not in combined.columns: combined["backlash_flag"] = 0
        if "migration_flag" not in combined.columns: combined["migration_flag"] = 0
        combined["backlash_flag"] = combined["backlash_flag"].fillna(0)
        combined["migration_flag"] = combined["migration_flag"].fillna(0)
        
        out_path = os.path.join(DATA_PROC_DIR, "whatsapp_privacy_2021_merged_final.csv")
        combined.to_csv(out_path, index=False)
        print(f"\n[Success] Combined dataset saved -> {out_path} ({len(combined):,} total rows)")
    else:
        print("\n[Warning] No data processed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", action="store_true", help="Run on a 5000-row sample")
    args = parser.parse_args()
    
    run_pipeline(sample=args.sample)
