"""
create_notebook.py - Creates Round3_RealTime_Analysis.ipynb notebook
"""
import nbformat as nbf
import os

nb = nbf.v4.new_notebook()

cells = [
    nbf.v4.new_markdown_cell("""# Data Vortex A'26 — Round 3 Notebook
## Live Social Media & Review Monitoring: 2021 WhatsApp Privacy Backlash & Migration Analysis

**Team:** Event Horizon  
**Dataset:** 14,891 cleaned rows across 3 distinct time windows:
- **T-0 (Baseline):** Nov 1, 2020 – Dec 31, 2020
- **T+1 (Shock Phase):** Jan 1, 2021 – Jan 31, 2021
- **T+2 (Fallout Phase):** Feb 1, 2021 – Jul 31, 2021
"""),

    nbf.v4.new_code_cell("""import os, sys, glob, json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_PATH = "../data/processed/whatsapp_privacy_2021_merged_final.csv"
SCORED_PATH = sorted(glob.glob("../data/processed/whatsapp_privacy_2021_scored_*.csv"))[-1]

df_raw = pd.read_csv(DATA_PATH)
df_scored = pd.read_csv(SCORED_PATH)

print(f"Merged Dataset Rows: {len(df_raw):,}")
print(f"Scored Dataset Rows: {len(df_scored):,}")
df_scored.head()
"""),

    nbf.v4.new_markdown_cell("""## 1. Sentiment Distribution & Source Breakdown"""),

    nbf.v4.new_code_cell("""print("Source Breakdown:")
print(df_scored["source"].value_counts())

print("\\nSentiment Distribution:")
print(df_scored["sentiment_label"].value_counts(normalize=True))
"""),

    nbf.v4.new_markdown_cell("""## 2. Aspect-Term Sentiment Analysis (ATSA)
Aspect-Term analysis targeting core backlash terms: `metadata`, `privacy`, `facebook`, `security`, `terms`, `switch`."""),

    nbf.v4.new_code_cell("""with open("../reports/atsa_results.json") as f:
    atsa_data = json.load(f)

atsa_df = pd.DataFrame(atsa_data)
atsa_df
"""),

    nbf.v4.new_markdown_cell("""## 3. LDA Topic Evolution Across Timeline Phases (T-0, T+1, T+2)"""),

    nbf.v4.new_code_cell("""with open("../reports/lda_topic_evolution.json") as f:
    lda_data = json.load(f)

for phase, info in lda_data.items():
    print(f"=== {phase} (N={info['count']}) ===")
    for topic in info['topics']:
        print(f"  * {topic}")
    print()
"""),

    nbf.v4.new_markdown_cell("""## 4. Volume & Event Trigger Overlays (Jan 4, Jan 7, Jan 15)"""),

    nbf.v4.new_code_cell("""with open("../reports/activity_results.json") as f:
    activity_data = json.load(f)

print(f"Volume Spikes: {activity_data['n_spikes_volume']}")
print(f"Engagement Spikes: {activity_data['n_spikes_engagement']}")
"""),

    nbf.v4.new_markdown_cell("""## 5. Figures Visualization"""),

    nbf.v4.new_code_cell("""from IPython.display import Image, display

display(Image(filename="../reports/figures/activity_analysis.png"))
display(Image(filename="../reports/figures/sentiment_timeseries.png"))
""")
]

nb['cells'] = cells

out_dir = "../notebooks"
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, "Round3_RealTime_Analysis.ipynb")

with open(out_path, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print(f"Created notebook -> {os.path.abspath(out_path)}")
