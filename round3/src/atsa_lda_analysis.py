"""
atsa_lda_analysis.py - Aspect-Term Sentiment & LDA Topic Evolution
Data Vortex A'26 | Team: Event Horizon

1. ATSA: Aspect-Term Sentiment Analysis on targeted keywords.
2. LDA Topic Evolution: Topic proportions across T-0, T+1, T+2 phases.
"""

import os, sys, glob, json
import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from config import DATA_PROC_DIR, REPORTS_DIR, FIGURES_DIR, TOPIC_SLUG

def get_latest_scored_csv() -> str:
    files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_scored_*.csv")))
    if not files:
        files = sorted(glob.glob(os.path.join(DATA_PROC_DIR, f"{TOPIC_SLUG}_merged_*.csv")))
    return files[-1]

def run_atsa(df: pd.DataFrame):
    print("=== Aspect-Term Sentiment Analysis (ATSA) ===")
    aspect_terms = ["privacy", "metadata", "facebook", "policy", "terms", "switch", "security", "signal", "telegram"]
    
    results = []
    for term in aspect_terms:
        matches = df[df["text"].str.contains(term, case=False, na=False)]
        if len(matches) > 0:
            avg_sent = matches["sentiment_numeric"].mean()
            neg_ratio = (matches["sentiment_label"] == "Negative").mean()
            pos_ratio = (matches["sentiment_label"] == "Positive").mean()
            
            # Break down by source (WhatsApp vs Telegram)
            wa_matches = matches[matches["source"] == "whatsapp"]
            tg_matches = matches[matches["source"] == "telegram"]
            
            wa_sent = wa_matches["sentiment_numeric"].mean() if len(wa_matches) > 0 else np.nan
            tg_sent = tg_matches["sentiment_numeric"].mean() if len(tg_matches) > 0 else np.nan
            
            results.append({
                "aspect_term": term,
                "total_mentions": len(matches),
                "avg_sentiment": round(avg_sent, 4),
                "negative_ratio": round(neg_ratio, 4),
                "positive_ratio": round(pos_ratio, 4),
                "whatsapp_avg_sentiment": round(wa_sent, 4) if not np.isnan(wa_sent) else None,
                "telegram_avg_sentiment": round(tg_sent, 4) if not np.isnan(tg_sent) else None,
            })
            
    res_df = pd.DataFrame(results)
    out_path = os.path.join(REPORTS_DIR, "atsa_results.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  [ATSA] Saved results -> {out_path}")
    print(res_df.to_string(index=False))
    return res_df

def run_lda_evolution(df: pd.DataFrame):
    print("\n=== LDA Topic Evolution Across Timeline Phases ===")
    df["ts"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    
    # Define T-0, T+1, T+2 phases
    t0_mask = (df["ts"] >= "2020-11-01") & (df["ts"] < "2021-01-01")
    t1_mask = (df["ts"] >= "2021-01-01") & (df["ts"] < "2021-02-01")
    t2_mask = (df["ts"] >= "2021-02-01") & (df["ts"] <= "2021-07-31")
    
    phases = {
        "T-0 (Baseline: Nov-Dec 2020)": df[t0_mask],
        "T+1 (Shock Phase: Jan 2021)": df[t1_mask],
        "T+2 (Fallout Phase: Feb-Jul 2021)": df[t2_mask],
    }
    
    lda_summary = {}
    
    for phase_name, p_df in phases.items():
        texts = p_df["text"].fillna("").astype(str).tolist()
        if len(texts) < 10:
            lda_summary[phase_name] = {"count": len(texts), "topics": []}
            continue
            
        vectorizer = CountVectorizer(max_df=0.9, min_df=2, stop_words="english", ngram_range=(1,2))
        dtm = vectorizer.fit_transform(texts)
        
        lda = LatentDirichletAllocation(n_components=3, random_state=42)
        lda.fit(dtm)
        
        feature_names = vectorizer.get_feature_names_out()
        topics = []
        for topic_idx, topic in enumerate(lda.components_):
            top_features_ind = topic.argsort()[:-8 - 1:-1]
            top_features = [feature_names[i] for i in top_features_ind]
            topics.append(f"Topic {topic_idx+1}: " + ", ".join(top_features))
            
        lda_summary[phase_name] = {
            "count": len(texts),
            "topics": topics
        }
        
    out_path = os.path.join(REPORTS_DIR, "lda_topic_evolution.json")
    with open(out_path, "w") as f:
        json.dump(lda_summary, f, indent=2)
    print(f"  [LDA] Saved topic evolution -> {out_path}")
    for p, info in lda_summary.items():
        print(f"\n--- {p} (N={info['count']}) ---")
        for top in info["topics"]:
            print(f"  * {top}")
            
    return lda_summary

def main():
    csv_path = get_latest_scored_csv()
    print(f"Loading data from: {os.path.basename(csv_path)}")
    df = pd.read_csv(csv_path, low_memory=False)
    
    run_atsa(df)
    run_lda_evolution(df)

if __name__ == "__main__":
    main()
