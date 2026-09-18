# Data Vortex A'26 — Round 2: NLP Sentiment Classification
**Team: Event Horizon | Task: Rebuilding the Social Engine (Semantic Layer)**

---

## What This Project Does

We build a complete NLP pipeline to classify social media posts into three sentiment categories
(Positive / Negative / Neutral) using 9,000 labelled training samples. The pipeline runs
end-to-end from raw CSV to trained model to polished PDF reports — every metric is computed live
from actual runs, with zero hardcoded numbers.

---

## Required Deliverables — Where to Find Them

| Deliverable | File Path |
|:---|:---|
| **1. NLP Script/Pipeline** | `src/run_pipeline.py` (main) |
| **2. Trained Model File** | `models/sentiment_linear_svm.pkl` |
| **3. Evaluation Metrics Report PDF** | `reports/Evaluation_Metrics_Report.pdf` |
| **4. Round 2 Technical Report PDF** | `reports/Round2_Technical_Report.pdf` |

---

## Quick Start — Reproduce Everything

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the full pipeline (preprocessing → training → evaluation → PDF reports)
python src/run_pipeline.py
```

This single command regenerates:
- `models/sentiment_linear_svm.pkl`
- `reports/metrics.json`
- All figures in `reports/figures/`
- `reports/Round2_Technical_Report.pdf`
- `reports/Evaluation_Metrics_Report.pdf`

---

## About the BERTweet Benchmark

The Technical Report references a BERTweet (vinai/bertweet-base) benchmark achieving Macro-F1 0.7330.
This was trained on Google Colab T4 GPU — it cannot be reproduced locally without a GPU.

**To verify the BERTweet numbers without a GPU (<2 min):**
```bash
python benchmarks/bertweet/verify_benchmark.py
```

**To reproduce from scratch (GPU required, ~30 min):**
See `benchmarks/bertweet/README.md` for full instructions.

---

## Repository Structure

```
round2/
├── Data/
│   └── Labeled_Social_NLP_Training_Data.csv   # Raw input dataset (9,000 rows)
├── models/
│   ├── sentiment_linear_svm.pkl               # OFFICIAL submission model
│   ├── sentiment_optimized.pkl                # Calibrated variant (for ROC/PR)
│   └── README.md                              # Model documentation
├── reports/
│   ├── Round2_Technical_Report.pdf            # DELIVERABLE #4
│   ├── Evaluation_Metrics_Report.pdf          # DELIVERABLE #3
│   ├── metrics.json                           # Live metrics source
│   └── figures/                              # All generated plots
├── src/
│   ├── run_pipeline.py                        # MAIN ENTRY POINT
│   ├── preprocess.py                          # Cleaning, dedup, split
│   ├── train.py                               # Model candidates + selection
│   ├── evaluate.py                            # Metrics, LIME, error analysis
│   ├── generate_report.py                     # Technical Report PDF generator
│   ├── generate_metrics_report.py             # Evaluation Metrics PDF generator
│   ├── optimize.py                            # Hyperparameter tuning
│   └── analysis/                             # Supplementary analysis scripts
│       └── README.md                         # Lists each script and run command
├── benchmarks/
│   └── bertweet/
│       ├── bertweet_benchmark.json            # Committed BERTweet results
│       ├── bertweet_predictions.csv           # Per-sample predictions (1,580 rows)
│       ├── verify_benchmark.py               # LOCAL VERIFIER (no GPU needed)
│       ├── bertweet_benchmark.py             # Full training script
│       ├── bertweet_colab.py                 # Colab-ready version
│       └── README.md                         # Environment + reproduction guide
├── deprecated/
│   └── generate_final_report.py              # Legacy script (superseded)
├── decisions.md                              # Technical decisions log
├── requirements.txt                          # Python dependencies
└── .gitignore
```

---

## Pipeline Stages

| Stage | Script | What Happens |
|:---|:---|:---|
| 1 | `preprocess.py` | Load CSV, remove 1,100 duplicates, clean text |
| 2 | `preprocess.py` | Stratified 80/20 train/test split (seed=42) |
| 3 | `preprocess.py` | EDA visualizations (class distribution, text length) |
| 4 | `train.py` | Compare NB, Logistic Regression, Linear SVM |
| 5 | `train.py` | Select Linear SVM (highest Macro-F1=0.5905) |
| 6 | `train.py` | GridSearchCV hyperparameter tuning |
| 7 | `evaluate.py` | Final test-set evaluation, all metrics |
| 8 | `evaluate.py` | LIME explainability, error analysis |
| 9 | `generate_report.py` | Render Round2_Technical_Report.pdf |
| 10 | `generate_metrics_report.py` | Render Evaluation_Metrics_Report.pdf |

---

## Key Results

| Model | Macro-F1 | Accuracy | Notes |
|:---|:---|:---|:---|
| Majority Baseline | 0.1721 | 0.3481 | |
| Multinomial NB | 0.5736 | 0.5741 | |
| Logistic Regression | 0.5884 | 0.5880 | |
| **Linear SVM (tuned)** | **0.5914** | **0.5911** | **Champion (local, fully reproducible)** |
| BERTweet (GPU, Colab) | 0.7330 | 0.7335 | Pre-computed benchmark — see benchmarks/ |
