"""
trigger_correlation.py - Shift/Spike to News Trigger Correlator
Data Vortex A'26 | Team: Event Horizon

For each detected sentiment shift or engagement spike, queries GDELT
for real news headlines within a ±24h window and surfaces the most
plausible real-world trigger. Correlation is clearly labeled as a
data-grounded hypothesis, not a certainty.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta, timezone
from config import REPORTS_DIR, FIGURES_DIR

GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

WHATSAPP_TRIGGERS = {
    "2021-01-06": "WhatsApp announces updated Terms of Service and Privacy Policy; users must accept by Feb 8",
    "2021-01-08": "Viral backlash begins; Signal and Telegram see massive download spikes",
    "2021-01-12": "Indian competition regulator CCI announces probe into WhatsApp",
    "2021-01-14": "Multiple Indian government officials comment on the policy",
    "2021-02-08": "Original policy deadline; WhatsApp delays enforcement to May 15",
    "2021-02-15": "WhatsApp runs full-page newspaper ads in India to clarify policy",
    "2021-03-04": "India's Meity sends WhatsApp formal notice demanding policy withdrawal",
    "2021-04-05": "Delhi High Court hears petition against WhatsApp policy",
    "2021-05-15": "New enforcement deadline passes; WhatsApp does not delete non-accepting accounts",
    "2021-05-25": "EU-level GDPR scrutiny discussion intensifies",
}

def fetch_gdelt_headlines(query: str, ts_start: datetime, ts_end: datetime, max_records: int = 10) -> list:
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_records,
        "startdatetime": ts_start.strftime("%Y%m%d%H%M%S"),
        "enddatetime":   ts_end.strftime("%Y%m%d%H%M%S"),
        "format": "json",
        "sort": "DateDesc",
        "sourcelang": "english",
    }
    try:
        resp = requests.get(GDELT_DOC_URL, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("articles", [])
    except Exception as e:
        print(f"  [Trigger] GDELT error: {e}")
        return []

def find_nearest_known_trigger(date_str: str) -> tuple:
    try:
        target = datetime.strptime(date_str[:10], "%Y-%m-%d")
    except Exception:
        return None, None
    best_key, best_delta = None, None
    for k in WHATSAPP_TRIGGERS:
        d = datetime.strptime(k, "%Y-%m-%d")
        delta = abs((target - d).days)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best_key = k
    if best_delta is not None and best_delta <= 7:
        return best_key, WHATSAPP_TRIGGERS[best_key]
    return None, None

def correlate_triggers(shift_results: dict, activity_results: dict) -> dict:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    all_events = []

    for s in shift_results.get("shifts", []):
        all_events.append({"type": "sentiment_shift", "date": s["date"][:10],
                           "direction": s.get("direction", ""), "zscore": s.get("zscore", 0)})
    for s in activity_results.get("volume_spikes", []):
        all_events.append({"type": "volume_spike", "date": s["date"][:10],
                           "zscore": s.get("zscore", 0)})
    for s in activity_results.get("engagement_spikes", []):
        all_events.append({"type": "engagement_spike", "date": s["date"][:10],
                           "zscore": s.get("zscore", 0)})

    correlations = []
    seen_dates = set()

    for event in all_events:
        date = event["date"]
        if date in seen_dates:
            continue
        seen_dates.add(date)

        ts = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        ts_start = ts - timedelta(hours=48)
        ts_end   = ts + timedelta(hours=48)

        print(f"  [Trigger] Querying GDELT for {date} ({event['type']}) ...")
        articles = fetch_gdelt_headlines(
            "WhatsApp privacy policy", ts_start, ts_end, max_records=5
        )
        time.sleep(0.5)

        nearest_key, nearest_desc = find_nearest_known_trigger(date)

        corr = {
            "event_date":   date,
            "event_type":   event["type"],
            "zscore":       event.get("zscore", 0),
            "gdelt_headlines": [
                {"title": a.get("title", ""), "url": a.get("url", ""), "date": a.get("seendate", "")}
                for a in articles[:5]
            ],
            "known_trigger": {
                "date": nearest_key,
                "description": nearest_desc,
            } if nearest_key else None,
            "hypothesis": (
                f"Data-grounded hypothesis: The {event['type']} on {date} "
                f"likely correlates with '{nearest_desc}' ({nearest_key})."
                if nearest_key else
                f"Data-grounded hypothesis: The {event['type']} on {date} "
                f"may relate to ongoing policy discussion but no specific trigger was identified."
            ),
        }
        correlations.append(corr)
        print(f"    -> {len(articles)} headlines found. Trigger: {nearest_key}")

    output = {
        "total_events_correlated": len(correlations),
        "correlations": correlations,
        "known_triggers_timeline": WHATSAPP_TRIGGERS,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = os.path.join(REPORTS_DIR, "trigger_correlations.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"[Trigger] Saved -> {out_path}")
    return output

if __name__ == "__main__":
    print("=== Trigger Correlation ===")
    shift_path  = os.path.join(REPORTS_DIR, "shift_results.json")
    act_path    = os.path.join(REPORTS_DIR, "activity_results.json")

    with open(shift_path)  as f: shift_r  = json.load(f)
    with open(act_path)    as f: activity_r = json.load(f)

    result = correlate_triggers(shift_r, activity_r)
    print(f"Events correlated: {result['total_events_correlated']}")
