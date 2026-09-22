"""
scheduler.py - Live Polling Orchestrator
Data Vortex A'26 | Team: Event Horizon

Runs all enabled collectors every SCHEDULER_INTERVAL_MINUTES minutes.
Appends fresh data to data/raw/ and logs every run to data/collection_log.csv.
Run this at the start of the collection window and leave it running.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
from datetime import datetime, timezone
from config import SOURCES, SCHEDULER_INTERVAL_MINUTES

def run_all_collectors():
    ts = datetime.now(timezone.utc).isoformat()
    print(f"\n{'='*60}")
    print(f"[Scheduler] Run at {ts}")
    print(f"{'='*60}")

    if SOURCES.get("gdelt"):
        try:
            from collectors.gdelt_collector import collect_gdelt
            collect_gdelt()
        except Exception as e:
            print(f"  [Scheduler] GDELT failed: {e}")

    if SOURCES.get("google_play"):
        try:
            from collectors.google_play_reviews_collector import collect_google_play
            collect_google_play()
        except Exception as e:
            print(f"  [Scheduler] Google Play failed: {e}")

    if SOURCES.get("hn"):
        try:
            from collectors.hn_collector import collect_hn
            collect_hn()
        except Exception as e:
            print(f"  [Scheduler] HN failed: {e}")

    if SOURCES.get("kaggle"):
        try:
            from collectors.kaggle_collector import collect_kaggle
            collect_kaggle()
        except Exception as e:
            print(f"  [Scheduler] Kaggle failed: {e}")

    print(f"[Scheduler] Run complete. Next run in {SCHEDULER_INTERVAL_MINUTES} min.\n")

if __name__ == "__main__":
    print(f"=== Data Vortex R3 Scheduler ===")
    print(f"Interval: every {SCHEDULER_INTERVAL_MINUTES} minutes")
    print(f"Press Ctrl+C to stop.\n")

    while True:
        try:
            run_all_collectors()
            time.sleep(SCHEDULER_INTERVAL_MINUTES * 60)
        except KeyboardInterrupt:
            print("\n[Scheduler] Stopped by user.")
            break
        except Exception as e:
            print(f"[Scheduler] Unexpected error: {e}. Retrying in 60s.")
            time.sleep(60)
