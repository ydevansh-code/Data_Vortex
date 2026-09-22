"""
shift_detection.py - Sentiment Shift Detection
Data Vortex A'26 | Team: Event Horizon

Computes rolling sentiment score over time, detects genuine shifts
using z-score crossing a stated threshold.

Threshold: z-score > 1.5 on a 24h rolling window.
Method: rolling mean of sentiment_numeric (Negative=0, Neutral=0.5, Positive=1.0)
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import glob
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timezone
from config import (
    DATA_PROC_DIR, REPORTS_DIR, FIGURES_DIR,
    TOPIC_SLUG, SHIFT_ZSCORE_THRESHOLD, ROLLING_WINDOW_HOURS
)

def get_latest_scored_csv() -> str:
    files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_scored_*.csv")))
    if not files:
        raise FileNotFoundError("No scored CSV. Run apply_model.py first.")
    return files[-1]

def compute_sentiment_timeseries(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    df = df.copy()
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts", "sentiment_numeric"])
    df["bucket"] = df["ts"].dt.to_period(freq).dt.to_timestamp().dt.tz_localize("UTC")

    ts = df.groupby("bucket").agg(
        sentiment_mean=("sentiment_numeric", "mean"),
        sentiment_std=("sentiment_numeric", "std"),
        n=("post_id", "count"),
        neg_frac=("sentiment_numeric", lambda x: (x == 0.0).mean()),
        pos_frac=("sentiment_numeric", lambda x: (x == 1.0).mean()),
    ).reset_index()
    ts.sort_values("bucket", inplace=True)

    window = 7 if freq == "D" else ROLLING_WINDOW_HOURS
    ts["roll_mean"] = ts["sentiment_mean"].rolling(window, min_periods=3, center=True).mean()
    ts["roll_std"]  = ts["sentiment_mean"].rolling(window, min_periods=3, center=True).std().fillna(0)
    ts["zscore"]    = (ts["sentiment_mean"] - ts["roll_mean"]) / (ts["roll_std"] + 1e-9)
    ts["is_shift"]  = ts["zscore"].abs() > SHIFT_ZSCORE_THRESHOLD
    ts["shift_dir"] = np.where(ts["zscore"] > SHIFT_ZSCORE_THRESHOLD, "positive",
                       np.where(ts["zscore"] < -SHIFT_ZSCORE_THRESHOLD, "negative", "none"))
    return ts

def plot_sentiment_timeseries(ts: pd.DataFrame):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(14, 9), facecolor="#0f1117")
    fig.suptitle("WhatsApp Privacy 2021 — Sentiment Over Time",
                 color="white", fontsize=14, fontweight="bold")

    for ax in axes:
        ax.set_facecolor("#1a1d2e")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    ax1 = axes[0]
    ax1.plot(ts["bucket"], ts["sentiment_mean"], color="#9b59b6", linewidth=1.5, label="Sentiment Score")
    ax1.plot(ts["bucket"], ts["roll_mean"], color="#f39c12", linewidth=1.2, linestyle="--", label="Rolling Mean")
    ax1.fill_between(ts["bucket"],
                     ts["roll_mean"] - SHIFT_ZSCORE_THRESHOLD * ts["roll_std"],
                     ts["roll_mean"] + SHIFT_ZSCORE_THRESHOLD * ts["roll_std"],
                     alpha=0.15, color="#f39c12", label=f"±{SHIFT_ZSCORE_THRESHOLD}σ band")
    shifts = ts[ts["is_shift"]]
    pos_shifts = shifts[shifts["shift_dir"] == "positive"]
    neg_shifts = shifts[shifts["shift_dir"] == "negative"]
    ax1.scatter(pos_shifts["bucket"], pos_shifts["sentiment_mean"], color="#2ecc71", zorder=6, s=70, marker="^", label="Positive Shift")
    ax1.scatter(neg_shifts["bucket"], neg_shifts["sentiment_mean"], color="#e74c3c", zorder=6, s=70, marker="v", label="Negative Shift")
    ax1.set_ylabel("Sentiment Score (0=Neg, 0.5=Neu, 1=Pos)", color="white")
    ax1.set_title("Rolling Sentiment Score with Shift Points", color="#9b59b6", fontsize=11)
    ax1.legend(facecolor="#1a1d2e", labelcolor="white", fontsize=8)
    ax1.set_ylim(0, 1)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())

    ax2 = axes[1]
    ax2.stackplot(ts["bucket"],
                  ts["neg_frac"], ts["pos_frac"],
                  labels=["Negative Fraction", "Positive Fraction"],
                  colors=["#e74c3c", "#2ecc71"], alpha=0.7)
    ax2.set_ylabel("Fraction", color="white")
    ax2.set_title("Negative vs Positive Fraction Over Time", color="#3498db", fontsize=11)
    ax2.legend(facecolor="#1a1d2e", labelcolor="white", fontsize=8)
    ax2.set_ylim(0, 1)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())

    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, "sentiment_timeseries.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0f1117")
    plt.close()
    print(f"  [Shift] Saved figure -> {out_path}")
    return out_path

def run_shift_detection(freq: str = "D") -> dict:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    csv_path = get_latest_scored_csv()
    print(f"[Shift] Loading: {os.path.basename(csv_path)}")
    df = pd.read_csv(csv_path, low_memory=False)
    if "sentiment_numeric" not in df.columns:
        from config import SENTIMENT_MAP
        df["sentiment_numeric"] = df["sentiment_label"].map(SENTIMENT_MAP).fillna(0.5)

    ts = compute_sentiment_timeseries(df, freq=freq)
    shifts = ts[ts["is_shift"]].copy()
    print(f"  Sentiment shifts detected: {len(shifts)}")

    plot_sentiment_timeseries(ts)

    results = {
        "method": "rolling_zscore",
        "freq": freq,
        "rolling_window_days": 7 if freq == "D" else ROLLING_WINDOW_HOURS,
        "threshold_zscore": SHIFT_ZSCORE_THRESHOLD,
        "total_buckets": len(ts),
        "shifts_detected": len(shifts),
        "shifts": [
            {
                "date": str(r["bucket"]),
                "sentiment_mean": round(float(r["sentiment_mean"]), 4),
                "zscore": round(float(r["zscore"]), 3),
                "direction": r["shift_dir"],
                "n_posts": int(r["n"]),
            }
            for _, r in shifts.iterrows()
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = os.path.join(REPORTS_DIR, "shift_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[Shift] Saved -> {out_path}")
    return results

if __name__ == "__main__":
    print("=== Sentiment Shift Detection ===")
    r = run_shift_detection()
    print(f"Shifts found: {r['shifts_detected']}")
    for s in r["shifts"]:
        print(f"  {s['date']}: sentiment={s['sentiment_mean']} z={s['zscore']} ({s['direction']})")
