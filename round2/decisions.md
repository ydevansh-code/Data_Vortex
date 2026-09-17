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
