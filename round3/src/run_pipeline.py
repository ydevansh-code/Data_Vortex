"""
run_pipeline.py - End-to-End Pipeline Orchestrator
Data Vortex A'26 | Team: Event Horizon

Runs: collect (if due) -> preprocess -> score -> analyze -> correlate -> report
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import argparse
from datetime import datetime, timezone
from config import REPORTS_DIR

def banner(msg):
    print(f"\n{'='*60}\n  {msg}\n{'='*60}")

def run_pipeline(skip_collect: bool = False, smoke_test: bool = False):
    banner("Data Vortex R3 — Full Pipeline")

    if smoke_test:
        banner("SMOKE TEST MODE — using mock data")
        _smoke_test()
        return

    if not skip_collect:
        banner("Phase 1: Data Collection")
        from collectors.gdelt_collector import collect_gdelt
        from collectors.google_play_reviews_collector import collect_google_play
        from collectors.hn_collector import collect_hn
        from collectors.kaggle_collector import process_all_kaggle
        collect_gdelt()
        collect_google_play()
        try:
            collect_hn()
        except Exception as e:
            print(f"  [HN] Skipped: {e}")
        try:
            process_all_kaggle()
        except Exception as e:
            print(f"  [Kaggle] Skipped: {e}")

    banner("Phase 2: Preprocessing")
    from preprocess import preprocess
    df = preprocess()

    banner("Phase 3: Model Scoring")
    from apply_model import apply_model
    df_scored = apply_model()

    banner("Phase 4a: Activity Analysis")
    from activity_analysis import run_activity_analysis
    activity_r = run_activity_analysis()

    banner("Phase 4b: Shift Detection")
    from shift_detection import run_shift_detection
    shift_r = run_shift_detection()

    banner("Phase 4c: Entity & Topic Extraction")
    from entity_topic_extraction import run_extraction
    entity_r = run_extraction()

    banner("Phase 4d: Trigger Correlation")
    from trigger_correlation import correlate_triggers
    trigger_r = correlate_triggers(shift_r, activity_r)

    banner("Phase 5: Report Generation")
    try:
        from generate_report import build_report
        pdf_path = build_report()
        print(f"  Report saved: {pdf_path}")
    except Exception as e:
        print(f"  [Report] ERROR: {e}")

    banner("Pipeline Complete")
    print(f"  Sentiment shifts: {shift_r.get('shifts_detected', 0)}")
    print(f"  Volume spikes:    {len(activity_r.get('volume_spikes', []))}")
    print(f"  Triggers correlated: {trigger_r.get('total_events_correlated', 0)}")

def _smoke_test():
    import pandas as pd
    import pickle
    from config import MODEL_PATH, DATA_PROC_DIR, TOPIC_SLUG
    import os

    print("  [Smoke] Testing model load...")
    model_path = os.path.abspath(MODEL_PATH)
    assert os.path.exists(model_path), f"Model not found: {model_path}"
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    test_texts = [
        "WhatsApp privacy policy is a total disaster",
        "Updated my WhatsApp terms today",
        "I love WhatsApp despite the new policy",
    ]
    preds = model.predict(test_texts)
    print(f"  [Smoke] Predictions: {list(zip(test_texts, preds))}")

    print("  [Smoke] Creating mock processed CSV...")
    os.makedirs(DATA_PROC_DIR, exist_ok=True)
    mock_data = pd.DataFrame({
        "post_id": [f"mock_{i}" for i in range(10)],
        "source": ["gdelt"] * 5 + ["google_play"] * 5,
        "text": test_texts * 3 + ["WhatsApp"] * 1,
        "timestamp": ["2021-01-10T00:00:00+00:00"] * 10,
        "engagement_metric": [5.0] * 10,
    })
    mock_path = os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_merged_SMOKE.csv")
    mock_data.to_csv(mock_path, index=False)
    print(f"  [Smoke] Mock CSV written: {mock_path}")
    print("  [Smoke] PASS — pipeline structure intact.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Data Vortex R3 Pipeline")
    parser.add_argument("--skip-collect", action="store_true", help="Skip data collection step")
    parser.add_argument("--smoke-test",   action="store_true", help="Run smoke test with mock data")
    args = parser.parse_args()
    run_pipeline(skip_collect=args.skip_collect, smoke_test=args.smoke_test)
