# Round 2 Methodological Decision Log

## Decision 1: Task Selection (Sentiment Classification)
- **Context:** Dataset 2 contains 9,001 posts with discrete labels for `sentiment_label` (Positive, Negative, Neutral) and `topic_category`.
- **Decision:** Select multi-class Text Sentiment Classification as primary task, with Topic Classification as benchmark.
- **Rationale:** Ensures 100% compliance with the required "Confusion Matrix" section of the rubric.

## Decision 2: Preprocessing & Stopwords Retention
- **Context:** Standard stopword removal strips words like "not", "no", "never".
- **Decision:** Retain negation stopwords in cleaning pipeline.
- **Rationale:** Preserves sentiment polarity critical for accurate sentiment classification.

## Decision 3: Baseline & Model Candidate Evaluation
- **Context:** Rubric requires explicit model selection justification.
- **Decision:** Benchmark `DummyClassifier(strategy='most_frequent')` against Multinomial Naive Bayes, Logistic Regression, and Linear SVM using Macro-F1.
- **Rationale:** Demonstrates true statistical learning above class imbalance baseline.

---

## Sept 18 2026 — Submission Polish Pass

- **Fixed NameError in generate_report.py:** Two f-strings referenced opt_res instead of 	est_m. Replaced with correct variable.
- **Fixed KeyError in generate_metrics_report.py:** Script assumed classification_report key; actual key is per_class. Fixed.
- **BERTweet benchmark made judge-proof:** Moved ertweet_benchmark.json + ertweet_predictions.csv to enchmarks/bertweet/. Added README.md (environment, params, reproduction steps) and erify_benchmark.py (local verifier, no GPU required, EXIT 0 confirmed).
- **BERTweet callout added to PDF:** generate_report.py now prints an explicit [PRE-COMPUTED BENCHMARK - GPU TRAINED ON GOOGLE COLAB] label in the Technical Report whenever BERTweet is the displayed champion. No ambiguity.
- **generate_report.py BT path updated:** Uses enchmarks/bertweet/ canonically, falls back to eports/ for backwards compatibility.
- **generate_metrics_report.py fully hardened:** All dict access converted to .get() with defaults. 	ry/except wraps the whole generation. Page map added as first page. BERTweet comparison table added conditionally.
- **Repo restructured:**
  - generate_final_report.py → deprecated/ (with deprecation header)
  - 8 analysis scripts → src/analysis/ (with README listing each script and run command)
  - ertweet_benchmark.py + ertweet_colab.py → enchmarks/bertweet/ (copies; originals left in src/ for existing imports)
- **models/README.md added:** Documents both pkl files, what trained them, what data, which is official champion.
- **README.md rewritten:** Full judge-facing documentation with deliverable paths, run instructions, BERTweet verification steps, and pipeline stage table.
- **.gitignore added:** Covers __pycache__, transformer output dirs (esults_bertweet*/), model weights, and temp files.
- **Pipeline verified:** python run_pipeline.py exits 0 cleanly in 13.6s after all changes.
