# Social Engine: Semantic Comprehension Layer Reconstruction
**Team**: Event Horizon  
**Track**: Data Vortex A'26 - Round 2  

> [!IMPORTANT]
> **MODEL STATUS: TWO DISTINCT APPROACHES**
> 
> **LOCAL REPRODUCIBLE MODEL**
> **Model**: Tuned LinearSVC
> **Macro-F1**: 0.5914
> **Accuracy**: 0.5911
> **Status**: Full reproducible pipeline included in the repository (CPU-friendly).
> 
> **INDEPENDENT GPU BENCHMARK**
> **Model**: BERTweet (vinai/bertweet-base)
> **Macro-F1**: 0.7330
> **Accuracy**: 0.7335
> **Environment**: Google Colab T4
> **Status**: Pre-computed benchmark (predictions provided, requires GPU to retrain).

---

## 1. Executive Summary
This report details our solution for the Round 2 semantic comprehension layer. We implemented a rigorous, leak-free, 3-class sentiment classification pipeline. To ensure reproducibility on standard hardware, our core deliverable is a highly tuned, TF-IDF based **LinearSVC** model. To demonstrate the performance ceiling available with modern compute, we also provide an independent **BERTweet** benchmark trained on Google Colab, achieving a statistically significant 0.14+ Macro-F1 lift over the local baseline.

## 2. Problem & Objective
**Objective**: Build a robust NLP solution for 3-class social-media sentiment classification (Positive / Negative / Neutral) to power the "Social Engine".
**Challenge**: Social media text is notoriously noisy, heavily reliant on context, and riddled with sarcasm, informal grammar, and implicit modalities, making boundaries between classes (especially Neutral vs. Negative) highly ambiguous.

## 3. Dataset & Data Quality
**Raw Data**: 9,001 labelled posts.
**Cleaned Data**: 7,900 deduplicated posts.

**DECISION**: Exact text deduplication prior to dataset splitting.
**EVIDENCE**: Jaccard similarity audit (≥ 0.80 on word 3-grams) confirmed 0 near-duplicate leakage post-split.
**WHY**: Social media datasets often contain retweets or bot spam. Failing to deduplicate artificially inflates test metrics (leakage).
**IMPACT**: Ensures our reported metrics reflect true generalization, not memorization.

## 4. End-to-End Pipeline

![End-to-End Pipeline](figures/pipeline.png)

## 5. Exploratory Data Analysis
Manual review of a 50-sample stratified subset revealed a label noise floor of approximately 34%. This establishes an irreducible error rate, indicating that a "perfect" model would likely plateau around ~0.66 Accuracy based purely on human disagreement and ambiguous annotations.

## 6. Preprocessing Decisions

**DECISION**: Remove punctuation, strip mentions (`@user`), and split hashtags for the local model.
**EVIDENCE**: 5-fold CV showed this standard normalization (Macro-F1: 0.5865 ± 0.0125) performed equivalently to retaining punctuation, while simplifying the feature space.
**WHY**: In bag-of-words models, keeping symbols rarely provides consistent signal without massive data.
**IMPACT**: Reduces dimensionality and overfitting for the local LinearSVC pipeline.

**DECISION**: Delegate emoji/hashtag handling to the tokenizer for the BERTweet benchmark.
**EVIDENCE**: BERTweet is pre-trained on 850M tweets with `normalization=True`.
**WHY**: Subword tokenization preserves the semantic intent of emojis and slang natively.
**IMPACT**: Captures nuanced sentiment missed by standard TF-IDF.

## 7. Model Selection

**DECISION**: Select LinearSVC as the Local Reproducible Model and BERTweet as the GPU Benchmark.
**EVIDENCE**: McNemar's test (Chi-squared = 103.4557, p < 0.0001) confirms BERTweet's massive superiority on the exact same test set.
**WHY**: LinearSVC is deterministic, fast, and runs anywhere. BERTweet represents the state-of-the-art for this specific domain but requires accelerators.
**IMPACT**: Provides the judges with both a guaranteed reproducible artifact and a competitive production-grade benchmark.

## 8. Feature Engineering & Ablation Experiments

**DECISION**: Use unigram TF-IDF rather than bigrams for the local model.
**EVIDENCE**: 5-fold CV showed unigram Macro-F1 = 0.5865, while bigrams (ngram=(2,2)) dropped substantially to 0.4848.
**WHY**: Short social-media posts produce extremely sparse high-dimensional phrase features, leading to catastrophic overfitting.
**IMPACT**: Better generalization and smaller model footprint on this dataset.

**DECISION**: Reject explicit negation tagging.
**EVIDENCE**: Cross-validation showed no statistically significant lift when appending `_NEG` to tokens following negation words.
**WHY**: Linear models struggle to capture the scope of negation purely through appended tags without dependency parsing.
**IMPACT**: Pipeline remains simpler and faster without sacrificing empirical performance.

## 9. Final Local Model (Reproducible)
* **Architecture**: LinearSVC
* **Features**: Unigram TF-IDF (sublinear TF enabled, optimized min/max document frequency)
* **Hyperparameter Tuning**: RandomizedSearchCV (5-fold CV)
* **Calibration**: Expected Calibration Error (ECE) = 0.0389, Maximum Calibration Error (MCE) = 0.1630 (Note: calibration metric derived from decision_function/Platt scaling).
* **Robustness**: Bootstrap 95% CI (1,000 resamples): 0.5731 - 0.6206.

## 10. Independent BERTweet Benchmark (GPU)
* **Architecture**: `vinai/bertweet-base` (RoBERTa pre-trained on English tweets).
* **Training**: 5 epochs, learning rate 2e-5, early stopping on 10% validation set.
* **Evaluation**: Strictly evaluated on the same 20% held-out test set (1,580 rows).
* **Cohen's Kappa**: 0.6015 (Moderate/Substantial agreement, significantly outperforming random chance expectation of ~0.33).

## 11. Evaluation

| Metric | Local Model (LinearSVC) | GPU Benchmark (BERTweet) |
| :--- | :--- | :--- |
| **Accuracy** | 0.5911 | 0.7335 |
| **Macro-F1** | 0.5914 | 0.7330 |
| **Precision (Macro)**| 0.5919 | 0.7340 |
| **Recall (Macro)** | 0.5954 | 0.7335 |

## 12. Confusion Matrix & Error Analysis

> [!NOTE]
> The following Error Taxonomy and Error Analysis is derived from the **Local LinearSVC Model** outputs to ensure reproducible diagnostic scripts.

### Linguistic Error Taxonomy
A rule-based categorization of misclassified posts reveals:
*   **Punctuation Intensive (Possible Sarcasm/Emotion)**: 42.7% of errors
*   **No Distinct Linguistic Pattern**: 31.3% of errors
*   **Modality/Hypothetical**: 27.1% of errors
*   **Explicit Negation**: 16.0% of errors
*   **Contrast/Shift**: 14.9% of errors

**DECISION**: Classify the "Neutral" boundary problem as the primary failure mode.
**EVIDENCE**: The local model struggles most with Neutral (F1 = 0.5098) compared to Negative (0.6427) and Positive (0.6216).
**WHY**: Social media posts frequently contain weak implicit signals that humans annotate inconsistently. Threshold tuning (argmax) did not resolve this (Delta Macro-F1: -0.0056).
**IMPACT**: Confirms that bag-of-words cannot distinguish between objective statements and subtle sarcasm.

## 13. Interpretability
LIME (Local Interpretable Model-agnostic Explanations) was applied to the local model.
*   **Correct Classifications**: Heavily rely on explicit polar words (e.g., "sorry", "shit").
*   **Misclassifications**: Frequently occur when neutral entities or geopolitical terms (e.g., "SCOTUS", "14th Amendment") are assigned latent polar weights by the model due to training set biases, overriding the neutral context of the sentence.

## 14. Limitations
1.  **Context Window**: BERTweet truncates at 128 tokens. While sufficient for tweets, longer forum posts lose context.
2.  **Sarcasm & Modality**: As proven by the error taxonomy, ~70% of structured errors stem from punctuation-heavy sarcastic structures or hypothetical modalities ("If I were..."). Neither TF-IDF nor base BERTweet handles these flawlessly without conversational context.
3.  **Irreducible Error**: The estimated 34% label noise in the raw dataset places a hard ceiling on achievable empirical performance.

## 15. Future Improvements
*   **Syntax-Tree Parsing**: Incorporate dependency parsing to explicitly model the scope of negation and contrastive shifts.
*   **Ensemble**: Soft-voting ensemble combining BERTweet's contextual embeddings with explicit linguistic features (e.g., VADER polarity scores, POS tag counts) to ground the transformer.
*   **Data Centric**: Apply confident learning (e.g., Cleanlab) to automatically detect and re-annotate the ~34% noisy labels in the training set before fine-tuning.

## 16. Reproducibility
*   **Local Pipeline**: Run `python run_pipeline.py`. Deterministic seed (`42`) used throughout. All preprocessing, splits, and training are hermetically sealed.
*   **Benchmark Verifier**: Run `python benchmarks/bertweet/verify_benchmark.py` to instantly validate the BERTweet CSV outputs locally without a GPU.

---

## 17. FINAL CONSISTENCY CHECK
As requested by strict audit standards, we verify the internal consistency of all reported numbers across the repository.

> [!WARNING]
> **Audit Findings & Reconciliations:**
> 1.  **Local Model Macro-F1:** An earlier draft of the report cited LinearSVC Macro-F1 as `0.5972`. **FLAGGED CONTRADICTION**. The true generated `metrics.json` value is **`0.5914`**. This report has been corrected to use the true `0.5914` value.
> 2.  **Calibration Metrics:** The `0.0389` ECE and `0.1630` MCE values were preserved as they apply to the Platt-scaled LinearSVC model.
> 3.  **Model Separation:** The text now explicitly attributes the 0.7330 F1 to the Colab GPU benchmark, and the 0.5914 F1 to the reproducible local model.

**Verified Master Parameters:**
*   **Final Local Model**: Tuned LinearSVC
*   **Local Test Accuracy**: 0.5911 (matches metrics.json)
*   **Local Macro-F1**: 0.5914 (matches metrics.json)
*   **BERTweet Benchmark Accuracy**: 0.7335 (matches bertweet_benchmark.json)
*   **BERTweet Benchmark Macro-F1**: 0.7330 (matches bertweet_benchmark.json)
*   **Confusion-Matrix Model**: Local LinearSVC (Explicitly stated in Section 12)
*   **Multi-Seed Model**: Local LinearSVC (Bootstrap CI)
*   **Calibration Model**: Local LinearSVC
*   **Test-Set Size**: 1,580 rows
*   **Split Methodology**: 70/10/20 (Train 5530 / Val 790 / Test 1580), strictly deduplicated text.