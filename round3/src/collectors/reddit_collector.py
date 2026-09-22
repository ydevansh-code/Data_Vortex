"""
reddit_collector.py - Reddit PRAW Collector
Data Vortex A'26 | Team: Event Horizon

Fetches submissions and comments from relevant subreddits mentioning
WhatsApp privacy keywords (Jan–May 2021).

Required env vars:
  REDDIT_CLIENT_ID     - from reddit.com/prefs/apps (script type)
  REDDIT_CLIENT_SECRET - from reddit.com/prefs/apps
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import pandas as pd
from datetime import datetime, timezone
from config import (
    REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT,
    KEYWORDS, GEOGRAPHY, DATE_START, DATE_END,
    DATA_RAW_DIR, COLL_LOG_PATH
)

DATE_START_TS = datetime.strptime(DATE_START, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()
DATE_END_TS   = datetime.strptime(DATE_END,   "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()

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

def get_reddit_instance():
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise EnvironmentError(
            "Reddit credentials missing. Set REDDIT_CLIENT_ID and "
            "REDDIT_CLIENT_SECRET environment variables.\n"
            "Register a free app at: https://www.reddit.com/prefs/apps"
        )
    import praw
    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        ratelimit_seconds=300,
    )

def collect_reddit(limit_per_query: int = 500) -> pd.DataFrame:
    os.makedirs(DATA_RAW_DIR, exist_ok=True)
    run_ts   = datetime.now(timezone.utc).isoformat()
    all_rows = []

    try:
        reddit = get_reddit_instance()
    except EnvironmentError as e:
        print(f"  [Reddit] SKIP: {e}")
        log_collection("reddit", "all", 0, "SKIP_NO_CREDS", run_ts)
        return pd.DataFrame()
    except Exception as e:
        print(f"  [Reddit] SKIP: {e}")
        log_collection("reddit", "all", 0, f"ERROR:{e}", run_ts)
        return pd.DataFrame()

    subreddits = GEOGRAPHY["reddit_subreddits"]
    search_queries = [
        "WhatsApp privacy policy",
        "WhatsApp new terms",
        "WhatsApp privacy",
        "delete WhatsApp",
        "WhatsApp ban",
    ]

    for sub_name in subreddits:
        for query in search_queries:
            print(f"  [Reddit] r/{sub_name} | '{query}'")
            try:
                subreddit = reddit.subreddit(sub_name)
                results = subreddit.search(
                    query,
                    sort="new",
                    time_filter="all",
                    limit=limit_per_query,
                )
                kept = 0
                for post in results:
                    ts = post.created_utc
                    if not (DATE_START_TS <= ts <= DATE_END_TS):
                        continue
                    created_iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
                    text = f"{post.title} {post.selftext}".strip()
                    if not text:
                        continue
                    all_rows.append({
                        "post_id":           post.id,
                        "source":            "reddit",
                        "text":              text,
                        "timestamp":         created_iso,
                        "engagement_metric": float(post.score),
                        "num_comments":      post.num_comments,
                        "subreddit":         sub_name,
                        "url":               f"https://reddit.com{post.permalink}",
                        "country":           "",
                        "lang":              "en",
                        "query_used":        query,
                    })
                    kept += 1
                print(f"    -> {kept} posts in date range")
                time.sleep(0.6)
            except Exception as e:
                print(f"    [Reddit] ERROR r/{sub_name} '{query}': {e}")
                log_collection("reddit", f"r/{sub_name}:{query}", 0, f"ERROR:{e}", run_ts)

    df = pd.DataFrame(all_rows)
    if not df.empty:
        df.drop_duplicates(subset=["post_id"], inplace=True)
        ts_label = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = os.path.join(DATA_RAW_DIR, f"reddit_{ts_label}.csv")
        df.to_csv(out_path, index=False)
        print(f"  [Reddit] Saved {len(df):,} posts -> {out_path}")
        log_collection("reddit", "multi-query", len(df), "OK", run_ts)
    else:
        print("  [Reddit] No posts collected.")
        log_collection("reddit", "multi-query", 0, "EMPTY", run_ts)

    return df

if __name__ == "__main__":
    print("=== Reddit Collector — WhatsApp Privacy Jan–May 2021 ===")
    df = collect_reddit()
    print(f"Total rows collected: {len(df):,}")
