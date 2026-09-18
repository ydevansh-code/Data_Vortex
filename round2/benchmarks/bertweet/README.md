# BERTweet Benchmark — Reproduction Guide

## What Is This?

This folder contains the pre-computed results of fine-tuning `vinai/bertweet-base` on the Data Vortex A'26 Round 2 dataset. This benchmark was trained **out-of-band on a GPU runtime** (Google Colab) and cannot be reproduced on a CPU-only machine. The results are committed here so judges can verify the reported numbers without needing a GPU.

## Files in This Folder

| File | Description |
|:---|:---|
| `bertweet_benchmark.json` | Summary metrics (Macro-F1, Accuracy, Kappa, split sizes) |
| `bertweet_predictions.csv` | Per-sample predictions with probability scores (1,580 rows) |
| `bertweet_benchmark.py` | Full training script (annotated, runs on local GPU or Colab) |
| `bertweet_colab.py` | Self-contained Colab single-cell version of the above |
| `verify_benchmark.py` | **No-GPU local verifier** - recomputes metrics from the CSV to confirm numbers |

## Training Environment

| Parameter | Value |
|:---|:---|
| Base model | `vinai/bertweet-base` |
| Framework | Hugging Face Transformers + Datasets |
| Hardware | Google Colab T4 GPU |
| Splits | 70% train / 10% val / 20% test (stratified, deduped, seed=42) |
| Split sizes | Train: 5,530 / Val: 790 / Test: 1,580 |
| Epochs | Up to 5, with EarlyStopping (patience=2) on val Macro-F1 |
| Batch size | 16 (train), 32 (eval) |
| Learning rate | 2e-5 |
| Weight decay | 0.01 |
| Max token length | 128 |
| FP16 | True (GPU only) |
| Random seed | 42 |

## Reported Test Results

| Metric | Value |
|:---|:---|
| **Macro-F1** | **0.7330** |
| **Accuracy** | **0.7335** |
| Cohen's Kappa | 0.6015 |

## Option A - Verify Without GPU (< 2 minutes)

Run the local verifier. No GPU, no Colab, no model download required:

```bash
cd round2/benchmarks/bertweet
python verify_benchmark.py
```

Expected output:
```
Verified Macro-F1 : 0.732955
Verified Accuracy : 0.733544
Verified Kappa    : 0.601460
JSON matches CSV  : TRUE
```

## Option B - Reproduce From Scratch on Colab (GPU required, ~30 min)

1. Open Google Colab and set Runtime to T4 GPU.
2. Install: `!pip install transformers datasets scikit-learn torch`
3. Upload `round2/Data/Labeled_Social_NLP_Training_Data.csv` when prompted.
4. Copy-paste `bertweet_colab.py` into a cell and run it.
5. Download the two output files and compare with committed versions.

> Note: Due to GPU non-determinism, exact floating-point reproduction is not guaranteed
> even with seed=42, but results should be within +/-0.002 Macro-F1.
