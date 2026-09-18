# Trained Model Files — Data Vortex A'26 Round 2

## Files

### `sentiment_linear_svm.pkl` — OFFICIAL SUBMISSION CHAMPION (Local)
- **What it is:** scikit-learn Pipeline containing TF-IDF vectorizer + LinearSVC classifier
- **Produced by:** `src/run_pipeline.py` → `src/train.py` (Stage 6: hyperparameter tuning)
- **Trained on:** 6,320 samples (80% of 7,900 cleaned rows, stratified, seed=42)
- **Parameters:** `tfidf__max_features=30000`, `tfidf__ngram_range=(1,2)`, `clf__C=0.1`
- **Test Macro-F1:** 0.5914 | **Test Accuracy:** 0.5911
- **Used by:** `src/evaluate.py` (loaded automatically by `run_pipeline.py`)

### `sentiment_optimized.pkl` — Calibrated variant (supplementary)
- **What it is:** CalibratedClassifierCV wrapper around LinearSVC — enables probability outputs (for ROC/PR curves, ECE calibration metrics)
- **Produced by:** `src/optimize.py` (standalone, not in main pipeline)
- **Trained on:** Same 6,320 training samples
- **Used by:** `src/generate_report.py` (reads `optimization_results.json` which this script produces)

## Note on BERTweet
The BERTweet benchmark (Macro-F1: 0.7330) was trained on Google Colab GPU and **its weights are not committed** here due to size (~440MB). Only the predictions CSV and benchmark JSON are committed.
See `benchmarks/bertweet/README.md` for full details and how to verify without downloading any weights.

## Smoke Test
To confirm both files load and predict correctly:
```bash
python -c "
import pickle
for f in ['models/sentiment_linear_svm.pkl', 'models/sentiment_optimized.pkl']:
    m = pickle.load(open(f, 'rb'))
    print(f, m.predict(['test sentence']))
"
```
