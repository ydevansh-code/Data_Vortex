# Round 2 Implementation Plan: Data Vortex A'26

## Problem Definition & Context
We are entering Round 2 (NLP) of the Data Vortex A'26 Hackathon (Team: Event Horizon). Dataset 2 (`Labeled_Social_NLP_Training_Data.csv`) is confirmed in `round2/Data/`. It contains 9,001 posts with both `sentiment_label` (Positive, Negative, Neutral) and `topic_category` (Community_Discussion, Technical_Issues, Feature_Feedback, Account_Security, etc.).
**Constraint:** Extreme time pressure (24-30 hours). All actions optimize for speed, defensibility, and exact alignment with the 7-section grading rubric.

## 1. Task Selection Decision Framework
*Confirmed from dataset inspection:*
*   **Selected Task:** **Text Classification (Sentiment Labeling & Topic Classification)**.
*   **Rationale:** The dataset contains discrete categorical label columns (`sentiment_label` and `topic_category`). This maps directly to the required "Confusion Matrix" rubric section. Primary focus will be `sentiment_label` (with multi-class classification for `topic_category` as extended benchmark).

## 2. Preprocessing Pipeline
*Designed for robust text handling and EDA visualization.*

| Step | Method | Rationale |
| :--- | :--- | :--- |
| **Cleaning** | Lowercase, remove HTML/URLs/punctuation, handle emojis/mentions (`@user`). | Standardizes noisy social text (mirrors Phase 1 rigor). |
| **Tokenization** | Regex / spaCy tokenization. | Fast, suitable for TF-IDF vectorization. |
| **Stopwords** | **Retain initially.** | Removing "not" or negation words destroys sentiment polarity. |
| **Missing/Empty** | Count, flag, and remove empty rows. | Do not silently drop. Document in report. |
| **Duplicates** | Exact string match removal. | Prevents train/test leakage. |
| **Data Split** | 80/20 Stratified Split (`random_state=42`). | Ensures rare classes appear in test set. |
| **Class Imbalance** | `class_weight='balanced'`. | Faster than SMOTE, highly effective for text. |

### Bonus 3 — Preprocessing EDA Visuals
*Included inside Preprocessing Pipeline section:*
1. **Class Distribution Bar Chart:** Visualizes class balance across Positive/Negative/Neutral and Topic categories.
2. **Text Length Histogram:** Distribution of character and word counts by sentiment class.

## 3. Model Selection & Comparison Framework
*Evaluates candidates on validation split by Macro-F1 to select the primary deliverable.*

### Candidate Comparison Table (Fix 3 & Fix 4)
*Every evaluation table begins with the Majority-Class Baseline.*

| Model | Accuracy | Macro-F1 | Train Time | Selection Status |
| :--- | :--- | :--- | :--- | :--- |
| **Majority-Class Baseline** (`DummyClassifier`) | Baseline % | Baseline F1 | <1s | Benchmark |
| **Multinomial Naive Bayes** (TF-IDF) | TBD | TBD | ~1s | Candidate |
| **Logistic Regression** (TF-IDF, `C=1.0`) | TBD | TBD | ~5s | Candidate |
| **Linear SVM** (`LinearSVC`, TF-IDF) | TBD | TBD | ~5s | Candidate |

*   **Justification Statement for Report:** "Our final model achieves X% accuracy / Y macro-F1 versus a majority-class baseline of Z% — establishing that the model has actually learned semantic signal rather than exploiting class imbalance."

## 4. Training Methodology & Reproducibility
*   **Validation:** Single 80/20 Stratified Train/Test split (`random_state=42`).
*   **Hyperparameter Tuning:** Small grid search on winning model (e.g., `C` in LogReg: [0.1, 1.0, 10.0], `ngram_range`: [(1,1), (1,2)]).
*   **Git Commit Checkpoints (Fix 1):** Mandatory minimum 6 commits across pipeline lifecycle:
    1. `scaffold: initialize round2 repository structure & requirements`
    2. `eda: complete dataset inspection & task selection decision`
    3. `preprocess: complete text cleaning, deduplication & stratified split`
    4. `baseline: train model candidates & produce model comparison table`
    5. `eval: train final model, generate confusion matrix & error analysis`
    6. `report: complete 7-section technical report draft & pdf export`

## 5. Evaluation Plan
*   **Baseline Benchmark (Fix 4):** `DummyClassifier(strategy='most_frequent')` is included as the first entry of every evaluation table to prove lift over class distribution defaults.
*   **Metrics:** Accuracy, Precision, Recall, Macro-F1, Weighted-F1.
*   **Confusion Matrix:** Generated programmatically via `seaborn` on held-out test predictions. Saved to `reports/figures/confusion_matrix.png`.

## 6. Error Analysis & Interpretability Plan
*Explicitly graded deliverable.*

*   **Quantitative Error Sampling:** Sample 15-20 misclassified test set instances. Categorize root cause (e.g., sarcasm, negation, short text, ambiguous boundary).
*   **Deliverable Table:**

| Text Snippet (Truncated) | True Label | Predicted Label | Likely Error Category |
| :--- | :--- | :--- | :--- |
| "The UI isn't exactly intuitive..." | Negative | Positive | Failed negation handling |
| "IDK." | Neutral | Negative | Extremely short text |

### Bonus 1 — LIME Explanations
*Using `lime.lime_text.LimeTextExplainer` on 2-3 sample predictions (1 correct, 1 misclassified):*
*   Extract top weighted features contributing to prediction.
*   Embed short visual/textual explanation paragraph inside Error Analysis section.

## 7. Report Structure
*Strict 1:1 mapping to the 7 required rulebook sections:*

1. **Problem Definition** (Task specification & dataset properties)
2. **Preprocessing Pipeline** (Cleaning, tokenization, EDA visuals)
3. **Model Selection** (Candidate comparison table vs Majority Baseline)
4. **Training Methodology** (Grid search & reproducibility seeds)
5. **Evaluation Metrics** (Precision, Recall, F1 vs Majority Baseline)
6. **Confusion Matrix** (Visual chart & class-by-class breakdown)
7. **Error Analysis** (15-20 error categorization table + LIME explanations + **Bonus 2: Limitations & Scope**)

### Bonus 2 — Limitations & Scope (Subsection at end of Report)
*4-6 concise sentences detailing:*
*   Model boundary conditions (struggles with heavy sarcasm, code-mixing, slang).
*   Future roadmap with more time (transformer fine-tuning, k-fold CV).

## 8. Repo Scaffold
```text
round2/
├── Data/
│   └── Labeled_Social_NLP_Training_Data.csv
├── notebooks/
│   └── 01_eda_and_baseline.ipynb
├── models/
│   └── sentiment_model.pkl
├── reports/
│   ├── figures/
│   │   ├── class_distribution.png
│   │   ├── text_length_hist.png
│   │   └── confusion_matrix.png
│   └── Round2_Technical_Report.pdf
├── src/
│   ├── preprocess.py
│   ├── train.py
│   └── evaluate.py
├── decisions.md
├── README.md
└── requirements.txt
```

## 9. Timeline & Percentage Checkpoints (Fix 2)
*Based on total remaining time budget (24-32 hours):*

- **0-5%:** Repository scaffold creation & dataset inspection commit.
- **5-20%:** Preprocessing pipeline, text cleaning, & EDA visuals (class dist, text length).
- **20-35%:** Model candidate comparison (Majority Baseline vs MNB vs LogReg vs SVM).
- **35-45%:** Hyperparameter tuning on winning model & artifact persistence (`.pkl`).
- **45-60%:** Evaluation suite, confusion matrix generation, Error Analysis table & LIME explanations.
- **60-85%:** Technical Report drafting (7 required sections + Limitations subsection).
- **85-95%:** PDF compilation, formatting check, and final review.
- **95-100% (Hard Floor - Last 60-90 Mins):** Final Git commit, push to GitHub, and submission verification (NO NEW CODE).

## 10. Anti-Fabrication & Integrity Guardrails
*   **No Data Leakage:** TF-IDF fit strictly on training split; transform on test split.
*   **Empirical Metrics Only:** All metrics and charts created programmatically from actual test runs.
*   **Originality:** 100% original prose and code.

## Open Questions & Status

1. **Task Type:** Confirmed as **Sentiment & Topic Text Classification**.
2. **Dataset Size:** 9,001 rows confirmed (`Labeled_Social_NLP_Training_Data.csv`).
3. **Compute:** CPU-friendly TF-IDF linear baseline prioritized for instant execution.
4. **Git Enforcement:** Minimum 6 commits logged across percentage checkpoints.
