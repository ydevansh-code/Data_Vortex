"""
activity_analysis.py - Volume & Engagement Spike Detection
Data Vortex A'26 | Team: Event Horizon

Buckets post volume and engagement by day/hour, computes rolling
mean + std, and flags spikes using a z-score threshold.

Threshold: z-score > 2.0 (stated explicitly for reproducibility).
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
    TOPIC_SLUG, SPIKE_ZSCORE_THRESHOLD
)

def get_latest_scored_csv() -> str:
    files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_scored_*.csv")))
    if not files:
        files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_merged_*.csv")))
    if not files:
        raise FileNotFoundError("No scored CSV found. Run preprocess.py + apply_model.py first.")
    return files[-1]

def compute_activity(df: pd.DataFrame, freq: str = "D") -> pd.DataFrame:
    df = df.copy()
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["ts"])
    df["bucket"] = df["ts"].dt.to_period(freq).dt.to_timestamp().dt.tz_localize("UTC")

    agg = df.groupby("bucket").agg(
        volume=("post_id", "count"),
        engagement_sum=("engagement_metric", "sum"),
        engagement_mean=("engagement_metric", "mean"),
    ).reset_index()
    agg.sort_values("bucket", inplace=True)

    window = 7 if freq == "D" else 24
    agg["vol_roll_mean"] = agg["volume"].rolling(window, min_periods=1).mean()
    agg["vol_roll_std"]  = agg["volume"].rolling(window, min_periods=1).std().fillna(0)
    agg["vol_zscore"]    = (agg["volume"] - agg["vol_roll_mean"]) / (agg["vol_roll_std"] + 1e-9)
    agg["is_spike"]      = agg["vol_zscore"] > SPIKE_ZSCORE_THRESHOLD

    agg["eng_roll_mean"] = agg["engagement_sum"].rolling(window, min_periods=1).mean()
    agg["eng_roll_std"]  = agg["engagement_sum"].rolling(window, min_periods=1).std().fillna(0)
    agg["eng_zscore"]    = (agg["engagement_sum"] - agg["eng_roll_mean"]) / (agg["eng_roll_std"] + 1e-9)
    agg["is_eng_spike"]  = agg["eng_zscore"] > SPIKE_ZSCORE_THRESHOLD

    return agg

def plot_activity(agg: pd.DataFrame, freq_label: str = "Daily"):
    os.makedirs(FIGURES_DIR, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), facecolor="#0f1117")
    fig.suptitle(f"WhatsApp Privacy 2021 — {freq_label} Activity",
                 color="white", fontsize=14, fontweight="bold")

    for ax in axes:
        ax.set_facecolor("#1a1d2e")
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_edgecolor("#444")

    ax1 = axes[0]
    ax1.plot(agg["bucket"], agg["volume"], color="#3498db", linewidth=1.5, label="Volume")
    ax1.fill_between(agg["bucket"], agg["volume"], alpha=0.2, color="#3498db")
    ax1.plot(agg["bucket"], agg["vol_roll_mean"], color="#f39c12", linewidth=1, linestyle="--", label="Rolling Mean")
    spikes = agg[agg["is_spike"]]
    ax1.scatter(spikes["bucket"], spikes["volume"], color="#e74c3c", zorder=5, s=60, label=f"Spike (z>{SPIKE_ZSCORE_THRESHOLD})")

    # Key Event Trigger Overlays
    triggers = [
        ("2021-01-04", "Jan 4: In-App Policy Notice", "#e74c3c"),
        ("2021-01-07", "Jan 7: Elon Musk 'Use Signal'", "#f1c40f"),
        ("2021-01-15", "Jan 15: WA Delays Deadline", "#2ecc71"),
    ]
    for date_str, label, col in triggers:
        dt = pd.to_datetime(date_str, utc=True)
        if agg["bucket"].min() <= dt <= agg["bucket"].max():
            ax1.axvline(dt, color=col, linestyle=":", linewidth=1.5, label=label)

    ax1.set_ylabel("Post Volume", color="white")
    ax1.set_title("Post Volume Over Time (With Event Triggers)", color="#3498db", fontsize=11)
    ax1.legend(facecolor="#1a1d2e", labelcolor="white", fontsize=8, loc="upper right")
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator())

    ax2 = axes[1]
    ax2.plot(agg["bucket"], agg["engagement_sum"], color="#2ecc71", linewidth=1.5, label="Engagement")
    ax2.fill_between(agg["bucket"], agg["engagement_sum"], alpha=0.2, color="#2ecc71")
    ax2.plot(agg["bucket"], agg["eng_roll_mean"], color="#f39c12", linewidth=1, linestyle="--", label="Rolling Mean")
    eng_spikes = agg[agg["is_eng_spike"]]
    ax2.scatter(eng_spikes["bucket"], eng_spikes["engagement_sum"], color="#e74c3c", zorder=5, s=60, label=f"Spike (z>{SPIKE_ZSCORE_THRESHOLD})")
    ax2.set_ylabel("Engagement Sum", color="white")
    ax2.set_title("Engagement Over Time", color="#2ecc71", fontsize=11)
    ax2.legend(facecolor="#1a1d2e", labelcolor="white", fontsize=8)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax2.xaxis.set_major_locator(mdates.MonthLocator())

    plt.tight_layout()
    out_path = os.path.join(FIGURES_DIR, "activity_analysis.png")
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="#0f1117")
    plt.close()
    print(f"  [Activity] Saved figure -> {out_path}")
    return out_path

def run_activity_analysis(freq: str = "D") -> dict:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    csv_path = get_latest_scored_csv()
    print(f"[Activity] Loading: {os.path.basename(csv_path)}")
    df = pd.read_csv(csv_path, low_memory=False)

    freq_label = "Daily" if freq == "D" else "Hourly"
    agg = compute_activity(df, freq=freq)

    spikes = agg[agg["is_spike"]]
    eng_spikes = agg[agg["is_eng_spike"]]
    print(f"  Volume spikes detected: {len(spikes)}")
    print(f"  Engagement spikes detected: {len(eng_spikes)}")

    plot_activity(agg, freq_label)

    results = {
        "freq": freq,
        "threshold_zscore": SPIKE_ZSCORE_THRESHOLD,
        "total_buckets": len(agg),
        "volume_spikes": [
            {"date": str(r["bucket"]), "volume": int(r["volume"]),
             "zscore": round(float(r["vol_zscore"]), 3)}
            for _, r in spikes.iterrows()
        ],
        "engagement_spikes": [
            {"date": str(r["bucket"]), "engagement": float(r["engagement_sum"]),
             "zscore": round(float(r["eng_zscore"]), 3)}
            for _, r in eng_spikes.iterrows()
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    out_path = os.path.join(REPORTS_DIR, "activity_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[Activity] Saved -> {out_path}")
    return results

if __name__ == "__main__":
    print("=== Activity Analysis ===")
    r = run_activity_analysis()
    print(f"Volume spikes: {len(r['volume_spikes'])}")
    for s in r["volume_spikes"]:
        print(f"  {s['date']}: volume={s['volume']} z={s['zscore']}")
