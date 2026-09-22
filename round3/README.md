# Round 3 — Real-Time Social Monitoring
**Data Vortex A'26 | Team: Event Horizon**

> **Topic:** WhatsApp Privacy Policy 2021 — Public Reaction  
> **Window:** Jan 1 – May 31, 2021 | **Geo:** India, Indonesia, Global

---

## Deliverables (Direct Links for Judges)

| # | Deliverable | Path |
|---|-------------|------|
| 1 | **Live Dataset (CSV)** | `data/processed/whatsapp_privacy_2021_scored_*.csv` |
| 2 | **Live Dataset (JSON)** | `data/processed/whatsapp_privacy_2021_scored_*.json` |
| 3 | **Scraping/Extraction Code** | `src/collectors/` — see [collectors/README.md](src/collectors/README.md) |
| 4 | **Real-Time Analysis Notebook** | `notebooks/Round3_RealTime_Analysis.ipynb` |
| 5 | **Analytical Report (PDF)** | `reports/Round3_Analytical_Report.pdf` |
| 6 | **Collection Audit Log** | `data/collection_log.csv` |

---

## How Round 3 Builds on Round 2

- **Model:** Reuses `round2/models/sentiment_linear_svm.pkl` without retraining (TF-IDF + LinearSVC, Macro-F1: 0.5914)
- **New:** Live multi-source collection (GDELT, Google Play, Reddit), time-series shift/spike detection, trigger correlation

---

## Quick Start

```bash
pip install -r round3/requirements.txt
python -m spacy download en_core_web_sm

# Smoke test (no credentials needed)
python round3/src/run_pipeline.py --smoke-test

# Full pipeline (after setting REDDIT_CLIENT_ID/SECRET env vars)
python round3/src/run_pipeline.py

# Start live scheduler (runs every 30 min)
python round3/src/scheduler.py
```

---

## Collection Timeline

| Run | Timestamp | Source | Records |
|-----|-----------|--------|---------|
| See `data/collection_log.csv` for full audit trail | | | |

---

## Detection Methodology

| Method | Threshold | Fixed Before Data? |
|--------|-----------|-------------------|
| Volume spike | z > 2.0 (7-day rolling) | Yes |
| Sentiment shift | \|z\| > 1.5 (7-day rolling) | Yes |

---

## See Also

- [`decisions.md`](decisions.md) — source selection, threshold rationale, limitations
- [`round2/README.md`](../round2/README.md) — Round 2 model documentation
