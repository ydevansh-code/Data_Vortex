# Supplementary Analysis Scripts

These scripts perform deep-dive analyses beyond the main pipeline. They are NOT required to reproduce the submission — run `src/run_pipeline.py` for that.
Each produces a JSON/CSV artifact in `reports/` that the main Technical Report PDF reads from.

| Script | Output | What It Produces | Run Command |
|:---|:---|:---|:---|
| `ablation_study.py` | `reports/ablation_results.json` | Feature ablation: impact of n-grams, cleaning steps, char features on Macro-F1 | `python src/analysis/ablation_study.py` |
| `advanced_eval.py` | `reports/advanced_eval.json` | Calibration error (ECE), ROC/PR curves, learning curves | `python src/analysis/advanced_eval.py` |
| `audit_leakage_cv.py` | *(stdout only)* | Cross-validation leakage audit: ensures no text overlap across CV folds | `python src/analysis/audit_leakage_cv.py` |
| `error_analysis.py` | `reports/error_analysis.json`, `top_errors.csv`, `per_class_taxonomy.csv` | Granular misclassification taxonomy with linguistic patterns | `python src/analysis/error_analysis.py` |
| `linguistic_error_analysis.py` | `reports/linguistic_error_analysis.json` | Negation/sarcasm/ambiguity breakdown of errors | `python src/analysis/linguistic_error_analysis.py` |
| `neutral_class_analysis.py` | `reports/neutral_class_analysis.json` | Specific analysis of the underperforming Neutral class | `python src/analysis/neutral_class_analysis.py` |
| `statistical_tests.py` | `reports/statistical_tests.json` | McNemar / bootstrap significance tests between models | `python src/analysis/statistical_tests.py` |
| `adjudicate_labels.py` | `reports/label_noise_audit_50.csv` | Label noise audit: identifies ambiguous or mislabeled samples | `python src/analysis/adjudicate_labels.py` |

All scripts expect to be run from the `round2/` directory with `reports/` already populated by the main pipeline.
