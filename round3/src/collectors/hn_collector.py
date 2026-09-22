"""
hn_collector.py - Hacker News Algolia API Collector
Data Vortex A'26 | Team: Event Horizon

Fetches comments and stories mentioning WhatsApp privacy policy updates.
Uses the free Algolia HN Search API (no auth required).
Excellent source for tech-community sentiment on privacy matters.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import requests
import pandas as pd
from datetime import datetime, timezone
from config import (
    DATE_START, DATE_END,
    DATA_RAW_DIR, COLL_LOG_PATH
)

HN_API_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_QUERIES = ["whatsapp privacy", "whatsapp policy", "whatsapp terms", "signal telegram"]

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

def collect_hn(start: str = DATE_START, end: str = DATE_END) -> pd.DataFrame:
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    all_records = []
    run_ts = datetime.now(timezone.utc).isoformat()
    
    start_ts = int(datetime.strptime(start, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())
    end_ts   = int(datetime.strptime(end, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())

    for query in HN_QUERIES:
        print(f"  [HN] Querying: '{query}'")
        params = {
            "query": query,
            "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
            "hitsPerPage": 1000, # Max allowed by Algolia
        }
        
        try:
            resp = requests.get(HN_API_URL, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            hits = data.get("hits", [])
            
            for h in hits:
                # Text can be in 'story_text', 'comment_text', or just 'title'
                text = h.get("comment_text") or h.get("story_text") or h.get("title") or ""
                
                # Basic cleaning of HTML tags commonly returned by HN Algolia API
                text = text.replace("<p>", " ").replace("</p>", " ").replace("&#x2F;", "/").replace("&quot;", '"')
                
                if not text.strip():
                    continue
                    
                all_records.append({
                    "post_id":           str(h.get("objectID", "")),
                    "source":            "hacker_news",
                    "source_type":       "bonus_live_scraped",
                    "source_name":       "hacker_news",
                    "text":              text,
                    "url":               f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                    "timestamp":         h.get("created_at", ""),
                    "engagement_metric": float(h.get("points") or 0), # Points (upvotes)
                    "country":           "Global", # HN is global tech community
                    "lang":              "en",
                    "query_used":        query,
                })
            time.sleep(1) # Be polite
        except Exception as e:
            print(f"  [HN] Error fetching '{query}': {e}")

    df = pd.DataFrame(all_records)
    if not df.empty:
        df.drop_duplicates(subset=["post_id"], inplace=True)
        ts_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(DATA_RAW_DIR, f"hn_{ts_label}.csv")
        df.to_csv(out_path, index=False)
        print(f"  [HN] Saved {len(df):,} records -> {out_path}")
        log_collection("hacker_news", "multi-query batch", len(df), "OK", run_ts)
    else:
        print("  [HN] No records returned.")
        log_collection("hacker_news", "multi-query batch", 0, "EMPTY", run_ts)

    return df

if __name__ == "__main__":
    print("=== Hacker News Collector ===")
    df = collect_hn()
    print(f"Total rows collected: {len(df):,}")
