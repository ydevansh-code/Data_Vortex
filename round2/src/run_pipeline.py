"""
run_pipeline.py — Round 2 Master Orchestrator
Data Vortex A'26 | Team: Event Horizon

Single entry point: runs all 9 stages end-to-end and reports results.
Usage: python round2/src/run_pipeline.py
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

from preprocess import run_preprocessing
from train import run_training
from evaluate import (
    evaluate_model,
    plot_confusion_matrix,
    run_error_analysis,
    run_lime_explanations,
    plot_per_class_metrics,
    save_metrics_json,
)
from generate_report import build_report
from generate_metrics_report import generate_pdf as build_metrics_report

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║     DATA VORTEX A'26 — ROUND 2: NLP PIPELINE                ║
║     Team: Event Horizon                                      ║
║     Sentiment & Topic Classification                         ║
╚══════════════════════════════════════════════════════════════╝
"""


def main():
    t_total = time.time()
    print(BANNER)

    # ── Stage 1-4: Preprocessing ──────────────────────────
    prep = run_preprocessing()
    X_train = prep["X_train"]
    X_test  = prep["X_test"]
    y_train = prep["y_train"]
    y_test  = prep["y_test"]
    raw_test = prep["raw_test"]

    # ── Stage 5-6: Training & Comparison ──────────────────
    train_out = run_training(X_train, y_train)
    best_model   = train_out["best_model"]
    winner_name  = train_out["winner_name"]
    df_cmp       = train_out["comparison_df"]

    baseline_row = df_cmp[df_cmp["Model"] == "Majority-Class Baseline"].iloc[0]
    baseline_acc = float(baseline_row["Accuracy"])
    baseline_f1  = float(baseline_row["Macro-F1"])

    # ── Stage 7: Evaluation ────────────────────────────────
    eval_result = evaluate_model(
        best_model, X_test, y_test, winner_name, baseline_acc, baseline_f1
    )

    # ── Stage 7b: Confusion Matrix ─────────────────────────
    plot_confusion_matrix(y_test, eval_result["y_pred"], eval_result["labels"], winner_name)
    plot_per_class_metrics(eval_result["report_dict"], eval_result["labels"])

    # ── Stage 8: Error Analysis ────────────────────────────
    df_errors = run_error_analysis(raw_test, y_test, eval_result["y_pred"])

    # ── Stage 9: LIME ──────────────────────────────────────
    lime_results = run_lime_explanations(
        best_model, raw_test, y_test, eval_result["y_pred"], eval_result["labels"]
    )

    # ── Save metrics JSON ──────────────────────────────────
    save_metrics_json(eval_result, winner_name, lime_results, df_errors)

    # ── Generate PDF Report ────────────────────────────────
    print("\n" + "=" * 60)
    print("  STAGE 10: GENERATING PDF REPORTS")
    print("=" * 60)
    pdf_path = build_report()
    build_metrics_report()

    elapsed = time.time() - t_total
    print(f"\n{'=' * 60}")
    print(f"  ✓  PIPELINE COMPLETE  ({elapsed:.1f}s total)")
    print(f"  Model    : {winner_name}")
    print(f"  Accuracy : {eval_result['accuracy']:.4f}  (baseline {baseline_acc:.4f})")
    print(f"  Macro-F1 : {eval_result['macro_f1']:.4f}  (baseline {baseline_f1:.4f})")
    print(f"  PDF      : {pdf_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
