"""
google_play_reviews_collector.py - Google Play Store Review Collector
Data Vortex A'26 | Team: Event Horizon

Scrapes user reviews for com.whatsapp from Google Play (free, no auth).
Filters by date range and languages/countries defined in config.

Required env vars: None
Dependency: google-play-scraper
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pandas as pd
from datetime import datetime, timezone
from config import (
    GOOGLE_PLAY_APP_ID, GOOGLE_PLAY_LANGS, GOOGLE_PLAY_COUNTRIES,
    DATE_START, DATE_END, DATA_RAW_DIR, COLL_LOG_PATH
)

try:
    from google_play_scraper import reviews, Sort
    GP_AVAILABLE = True
except ImportError:
    GP_AVAILABLE = False
    print("[WARN] google-play-scraper not installed. Run: pip install google-play-scraper")

DATE_START_DT = datetime.strptime(DATE_START, "%Y-%m-%d").replace(tzinfo=timezone.utc)
DATE_END_DT   = datetime.strptime(DATE_END,   "%Y-%m-%d").replace(tzinfo=timezone.utc)

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

def collect_google_play(max_per_combo: int = 5000) -> pd.DataFrame:
    if not GP_AVAILABLE:
        log_collection("google_play", GOOGLE_PLAY_APP_ID, 0, "SKIP_NO_LIB")
        return pd.DataFrame()

    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    run_ts   = datetime.now(timezone.utc).isoformat()
    all_rows = []

    for lang in GOOGLE_PLAY_LANGS:
        for country in GOOGLE_PLAY_COUNTRIES:
            print(f"  [GP] lang={lang} country={country} ...")
            try:
                result, _ = reviews(
                    GOOGLE_PLAY_APP_ID,
                    lang=lang,
                    country=country,
                    sort=Sort.NEWEST,
                    count=max_per_combo,
                )
                kept = 0
                for r in result:
                    at = r.get("at")
                    if at is None:
                        continue
                    if hasattr(at, "tzinfo") and at.tzinfo is None:
                        at = at.replace(tzinfo=timezone.utc)
                    elif not hasattr(at, "tzinfo"):
                        continue
                    if not (DATE_START_DT <= at <= DATE_END_DT):
                        continue
                    all_rows.append({
                        "post_id":           r.get("reviewId", ""),
                        "source":            "google_play",
                        "source_type":       "bonus_live_scraped",
                        "source_name":       "google_play",
                        "text":              r.get("content", ""),
                        "timestamp":         at.isoformat(),
                        "engagement_metric": float(r.get("thumbsUpCount", 0)),
                        "star_rating":       r.get("score", 0),
                        "country":           country,
                        "lang":              lang,
                        "query_used":        f"{lang}_{country}",
                    })
                    kept += 1
                print(f"    -> {kept} reviews in date range")
                time.sleep(1.0)
            except Exception as e:
                print(f"    [GP] ERROR lang={lang} country={country}: {e}")
                log_collection("google_play", f"{lang}_{country}", 0, f"ERROR:{e}", run_ts)

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df.drop_duplicates(subset=["post_id"], inplace=True)
        ts_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(DATA_RAW_DIR, f"google_play_{ts_label}.csv")
        df.to_csv(out_path, index=False)
        print(f"  [GP] Saved {len(df):,} reviews -> {out_path}")
        log_collection("google_play", GOOGLE_PLAY_APP_ID, len(df), "OK", run_ts)
    else:
        print("  [GP] No reviews in date range.")
        log_collection("google_play", GOOGLE_PLAY_APP_ID, 0, "EMPTY", run_ts)

    return df

if __name__ == "__main__":
    print("=== Google Play Collector — WhatsApp Reviews Jan–May 2021 ===")
    df = collect_google_play()
    print(f"Total rows collected: {len(df):,}")
