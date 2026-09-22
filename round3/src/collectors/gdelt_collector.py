"""
gdelt_collector.py - GDELT 2.0 DOC API Collector (Optimized 5.5s Politeness + Monthly Ingestion)
Data Vortex A'26 | Team: Event Horizon

Fetches global news articles mentioning WhatsApp privacy keywords
from GDELT DOC 2.0 API with strict adherence to the 5-second rate limit.
Saves incrementally to round3/data/raw/gdelt_live_stream.csv.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from config import (
    DATE_START, DATE_END,
    DATA_RAW_DIR, COLL_LOG_PATH
)

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

GDELT_THEMES = [
    "whatsapp privacy policy",
    "whatsapp new terms",
    "whatsapp privacy",
    "telegram whatsapp privacy"
]

OUT_FILE = os.path.join(DATA_RAW_DIR, "gdelt_live_stream.csv")

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

def query_gdelt_window(query: str, start_dt: datetime, end_dt: datetime, maxrecords: int = 250) -> list:
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": maxrecords,
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime":   end_dt.strftime("%Y%m%d%H%M%S"),
        "format": "json",
        "sort": "DateDesc",
        "sourcelang": "english",
    }
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            resp = requests.get(GDELT_DOC_URL, params=params, timeout=25)
            if resp.status_code == 429:
                wait_time = 7.0 * (attempt + 1)
                print(f"  [GDELT] Rate limit hit (429). Waiting {wait_time}s...")
                time.sleep(wait_time)
                continue
                
            resp.raise_for_status()
            data = resp.json()
            return data.get("articles", [])
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"  [GDELT] Failed query '{query}': {e}")
                return []
            time.sleep(6.0)
            
    return []

def append_to_csv(records):
    if not records:
        return
    df_new = pd.DataFrame(records)
    if os.path.exists(OUT_FILE):
        df_existing = pd.read_csv(OUT_FILE, low_memory=False)
        df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        df_combined.drop_duplicates(subset=["post_id"], inplace=True)
        df_combined.to_csv(OUT_FILE, index=False)
    else:
        df_new.drop_duplicates(subset=["post_id"], inplace=True)
        df_new.to_csv(OUT_FILE, index=False)

def collect_gdelt(start: str = DATE_START, end: str = DATE_END, batch_days: int = 28) -> pd.DataFrame:
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    run_ts = datetime.now(timezone.utc).isoformat()

    start_dt = datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_dt   = datetime.strptime(end,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

    total_added = 0
    current = start_dt

    while current < end_dt:
        window_end = min(current + timedelta(days=batch_days), end_dt)
        batch_records = []

        for query in GDELT_THEMES:
            print(f"  [GDELT] Querying {current.date()} to {window_end.date()} | Theme: '{query}'...")
            articles = query_gdelt_window(query, current, window_end)
            print(f"    -> Received {len(articles)} articles.")
            for a in articles:
                batch_records.append({
                    "post_id":           a.get("url", ""),
                    "source":            "gdelt",
                    "source_type":       "bonus_live_scraped",
                    "source_name":       "gdelt",
                    "text":              a.get("title", ""),
                    "url":               a.get("url", ""),
                    "timestamp":         a.get("seendate", ""),
                    "engagement_metric": 0.0,
                    "country":           a.get("sourcecountry", ""),
                    "lang":              a.get("language", "English"),
                    "query_used":        query,
                })
            time.sleep(5.5) # Crucial: GDELT requires >5s between requests

        if batch_records:
            append_to_csv(batch_records)
            total_added += len(batch_records)
            if os.path.exists(OUT_FILE):
                cur_len = len(pd.read_csv(OUT_FILE, low_memory=False))
                print(f"  [GDELT] Saved! File now has {cur_len:,} total deduplicated records -> {OUT_FILE}")

        current = window_end

    print(f"  [GDELT] Finished all date ranges!")
    log_collection("gdelt", "multi-query batch", total_added, "OK", run_ts)
    
    if os.path.exists(OUT_FILE):
        return pd.read_csv(OUT_FILE)
    return pd.DataFrame()

if __name__ == "__main__":
    print("=== GDELT Collector (Strict 5.5s Rate Limit + Incremental Saving) ===")
    collect_gdelt()
