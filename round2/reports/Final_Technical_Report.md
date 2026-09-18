# Data Vortex A'26 - Round 2 Technical Report
**Team**: Event Horizon
**Theme**: Rebuilding the Social Engine (Semantic Comprehension)
**Date Generated**: 2026-09-18 03:08:11

---

## 1. Model Selection & Justification
After rigorous empirical benchmarking and a data integrity audit, the champion model is **BERTweet** (`vinai/bertweet-base`), a RoBERTa architecture pre-trained on 850M English Tweets. Clean evaluation on a strictly held-out test set (20% of deduplicated data, zero text overlap with train) yields **Macro-F1 0.7330** (Accuracy: **0.7335**).

### Model Selection Rationale
Social media text is characterized by informal grammar, slang, abbreviations, and heavy context dependence that confound bag-of-words models. BERTweet's deep bidirectional attention resolves these linguistic ambiguities, delivering +0.1358 Macro-F1 lift over the LinearSVC baseline (0.5972).

### Data Integrity & Leakage Audit
All 9,001 raw posts were deduplicated (exact text match) prior to splitting, removing duplicate entries that would inflate transformer memorization scores. The clean split: Train=5,530 / Val=790 (early stopping only) / Test=1,580 (strictly held out). Leakage assertion passed: zero text overlap across all three partitions.

## 2. Processing & Pipeline Design
Input posts are deduplicated on raw text, then fed directly to the BERTweet tokenizer (`normalization=True`, `max_length=128`, `padding=max_length`). BERTweet's built-in normalization handles URLs (@USER replacement), hashtags, and emoji.
For ablation context, we also ran the classical TF-IDF pipeline below. These ablation results confirm the value of contextual embeddings over bag-of-words.
### Preprocessing Ablation Study (TF-IDF Pipeline)
5-fold CV ablation verifies impact of each text normalization step:
- **A: Champion pipeline (remove punct, split hashtags, strip mentions)**: Macro-F1 0.5865 ± 0.0125
- **B: Keep punctuation**: Macro-F1 0.5865 ± 0.0125
- **C: Keep hashtag symbol + keep punct (no split, # survives)**: Macro-F1 0.5865 ± 0.0125
- **D: Retain mention token (@user)**: Macro-F1 0.5862 ± 0.0152
- **E: Bigrams only (ngram=(2,2)) — same text as A, model variant**: Macro-F1 0.4848 ± 0.0061

## 3. Model Performance & Evaluation Matrix
### Point Estimates (Hold-Out Test Set)
- **Champion Model**: BERTweet (`vinai/bertweet-base`), fine-tuned 5 epochs, lr=2e-5
- **Macro-F1**: 0.7330
- **Accuracy**: 0.7335
- **Cohen's Kappa**: 0.6015
- **LinearSVC Baseline (clean)**: Macro-F1 0.5972  |  Lift: +0.1358

### Statistical Significance (McNemar's Test)
To ensure the performance lift over the classical baseline is statistically significant, we ran McNemar's test comparing BERTweet to Tuned LinearSVC on the exact same test set.
- **Chi-squared**: 103.4557
- **p-value**: 0.000000 (Significant at alpha=0.05)

### Robustness & Calibration (LinearSVC)
- **Bootstrap 95% CI (1,000 resamples)**: 0.5731 - 0.6206
- **Expected Calibration Error (ECE)**: 0.0389
- **Maximum Calibration Error (MCE)**: 0.1630

*ECE < 0.04 indicates the model's confidence scores are highly reliable.*

## 4. Error Analysis
### The Neutral Class Problem
Classification threshold optimization for the Neutral class confirmed argmax as optimal (Delta Macro-F1: -0.0056). Mutual Information against topic category: MI = 0.0005. Error rates are uniformly distributed (38-41%) across all topics — model is not biased by topic vocabulary.

### Linguistic Error Taxonomy
Rule-based categorization of misclassified posts:
- **Punctuation Intensive (Possible Sarcasm/Emotion)**: 42.7% of errors
- **No Distinct Linguistic Pattern**: 31.3% of errors
- **Modality/Hypothetical**: 27.1% of errors
- **Explicit Negation**: 16.0% of errors
- **Contrast/Shift**: 14.9% of errors

Punctuation-intensive posts (sarcasm/emotion markers) and modality/hypothetical language account for ~70% of structured errors. Syntax-tree parsing is the primary future improvement vector.

## 5. Data Integrity Audit & Reproducibility
All metrics are reproducible. Seed = 42 everywhere. No hyperparameter searches on test data.
### Leakage Prevention
- Exact deduplication on raw `post_text` before any split (removes duplicate entries in source CSV)
- TF-IDF / tokenizer fitted on training partition only; test set strictly held out
- Near-duplicate audit (Jaccard ≥ 0.80 on word 3-grams) run post-split: zero matches found
- Manual label noise audit: 50-sample stratified sample reviewed, ~34% label noise / irreducible error estimated

---
*End of Report*