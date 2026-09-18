"""
generate_metrics_report.py - Standalone Evaluation Metrics Report Generator
Data Vortex A'26 | Team: Event Horizon

Reads metrics.json (produced by evaluate.py) and generates Evaluation_Metrics_Report.pdf.
All values are read dynamically - no hardcoded numbers.
"""
import os
import json
import sys
from fpdf import FPDF

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
FIGURES_DIR = os.path.join(REPORTS_DIR, "figures")
METRICS_PATH = os.path.join(REPORTS_DIR, "metrics.json")
OUTPUT_PDF = os.path.join(REPORTS_DIR, "Evaluation_Metrics_Report.pdf")

_BT_BENCH_NEW = os.path.join(os.path.dirname(__file__), "..", "benchmarks", "bertweet", "bertweet_benchmark.json")
_BT_BENCH_OLD = os.path.join(REPORTS_DIR, "bertweet_benchmark.json")
BT_PATH = _BT_BENCH_NEW if os.path.exists(_BT_BENCH_NEW) else _BT_BENCH_OLD

class MetricsPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, "Evaluation Metrics Report - Data Vortex A'26", ln=True, align="C")
        self.set_font("Helvetica", "I", 9)
        self.cell(0, 6, "Team: Event Horizon | Round 2: Sentiment Classification", ln=True, align="C")
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()} | All values sourced live from metrics.json - no hardcoded numbers", align="C")

def generate_pdf():
    try:
        if not os.path.exists(METRICS_PATH):
            raise FileNotFoundError(f"CRITICAL: metrics.json not found at {METRICS_PATH}. Run run_pipeline.py first.")
        with open(METRICS_PATH, "r") as f:
            metrics = json.load(f)
    except Exception as e:
        print(f"ERROR loading metrics.json: {e}")
        sys.exit(1)

    bt = None
    if os.path.exists(BT_PATH):
        try:
            with open(BT_PATH, "r") as f:
                bt = json.load(f)
        except Exception:
            bt = None

    cr = metrics.get("per_class", {})
    pdf = MetricsPDF()

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 10, "Page Map", ln=True)
    pdf.set_font("Helvetica", "", 10)
    page_map = [
        ("1", "Page Map (this page)"),
        ("2", "Overall Performance Metrics (Accuracy, Macro-F1, Weighted-F1, Precision, Recall)"),
        ("2", "Per-Class Breakdown Table (Negative / Neutral / Positive)"),
        ("2", "BERTweet Benchmark Comparison (if available)"),
        ("3", "Confusion Matrix Visualization"),
        ("3", "Per-Class Metrics Visualization"),
    ]
    col_w = [15, 155]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(col_w[0], 8, "Page", border=1, align="C")
    pdf.cell(col_w[1], 8, "Section", border=1)
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    for pg, sec in page_map:
        pdf.cell(col_w[0], 8, pg, border=1, align="C")
        pdf.cell(col_w[1], 8, sec, border=1)
        pdf.ln(8)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "1. Overall Performance Metrics", ln=True)
    pdf.set_font("Helvetica", "", 11)

    model_name = metrics.get("model", "Unknown")
    accuracy   = metrics.get("accuracy", 0)
    macro_f1   = metrics.get("macro_f1", 0)
    w_f1       = metrics.get("weighted_f1", 0)
    m_prec     = metrics.get("macro_precision", cr.get("macro avg", {}).get("precision", 0))
    m_rec      = metrics.get("macro_recall", cr.get("macro avg", {}).get("recall", 0))
    bl_acc     = metrics.get("baseline_accuracy", 0)
    bl_f1      = metrics.get("baseline_macro_f1", 0)

    rows = [
        ("Model", model_name),
        ("Test Accuracy", f"{accuracy:.4f}  (baseline: {bl_acc:.4f}  |  lift: +{accuracy-bl_acc:.4f})"),
        ("Macro-F1", f"{macro_f1:.4f}  (baseline: {bl_f1:.4f}  |  lift: +{macro_f1-bl_f1:.4f})"),
        ("Weighted-F1", f"{w_f1:.4f}"),
        ("Macro Precision", f"{m_prec:.4f}"),
        ("Macro Recall", f"{m_rec:.4f}"),
    ]
    lw, vw = 55, 115
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(lw, 8, "Metric", border=1)
    pdf.cell(vw, 8, "Value", border=1)
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 10)
    for label, val in rows:
        pdf.cell(lw, 8, label, border=1)
        pdf.cell(vw, 8, str(val), border=1)
        pdf.ln(8)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "2. Per-Class Breakdown", ln=True)

    col_w2 = [35, 35, 35, 35, 30]
    pdf.set_font("Helvetica", "B", 10)
    for h, w in zip(["Class", "Precision", "Recall", "F1-Score", "Support"], col_w2):
        pdf.cell(w, 8, h, border=1, align="C")
    pdf.ln(8)

    pdf.set_font("Helvetica", "", 10)
    for cls in ["Negative", "Neutral", "Positive"]:
        cd = cr.get(cls, {})
        pdf.cell(col_w2[0], 8, cls, border=1, align="C")
        pdf.cell(col_w2[1], 8, f"{cd.get('precision', 0):.4f}", border=1, align="C")
        pdf.cell(col_w2[2], 8, f"{cd.get('recall', 0):.4f}", border=1, align="C")
        pdf.cell(col_w2[3], 8, f"{cd.get('f1-score', 0):.4f}", border=1, align="C")
        pdf.cell(col_w2[4], 8, str(int(cd.get("support", 0))), border=1, align="C")
        pdf.ln(8)

    for avg_label in ["macro avg", "weighted avg"]:
        ad = cr.get(avg_label, {})
        if ad:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(col_w2[0], 8, avg_label, border=1, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(col_w2[1], 8, f"{ad.get('precision', 0):.4f}", border=1, align="C")
            pdf.cell(col_w2[2], 8, f"{ad.get('recall', 0):.4f}", border=1, align="C")
            pdf.cell(col_w2[3], 8, f"{ad.get('f1-score', 0):.4f}", border=1, align="C")
            pdf.cell(col_w2[4], 8, str(int(ad.get("support", 0))), border=1, align="C")
            pdf.ln(8)

    if bt:
        pdf.ln(6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "3. BERTweet Benchmark Comparison [PRE-COMPUTED, GPU-TRAINED]", ln=True)
        pdf.set_font("Helvetica", "I", 9)
        pdf.multi_cell(0, 6,
            "BERTweet was fine-tuned on Google Colab T4 GPU (not locally reproduced). "
            "Verify metrics independently: python benchmarks/bertweet/verify_benchmark.py")
        pdf.ln(3)
        comp_rows = [
            ("Model", model_name, bt.get("model", "vinai/bertweet-base")),
            ("Macro-F1", f"{macro_f1:.4f}", f"{bt.get('macro_f1', 0):.4f}"),
            ("Accuracy", f"{accuracy:.4f}", f"{bt.get('accuracy', 0):.4f}"),
            ("Kappa", "N/A", f"{bt.get('kappa', 0):.4f}"),
            ("Split", "80/20 train/test", bt.get("split", "70/10/20")),
        ]
        cw3 = [45, 70, 70]
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(cw3[0], 8, "Metric", border=1, align="C")
        pdf.cell(cw3[1], 8, f"Local Model ({model_name})", border=1, align="C")
        pdf.set_fill_color(220, 240, 255)
        pdf.cell(cw3[2], 8, "BERTweet (Colab GPU)", border=1, align="C", fill=True)
        pdf.ln(8)
        
        for r in comp_rows:
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(cw3[0], 8, str(r[0]), border=1, align="C")
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(cw3[1], 8, str(r[1]), border=1, align="C")
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_fill_color(240, 248, 255)
            pdf.cell(cw3[2], 8, str(r[2]), border=1, align="C", fill=True)
            pdf.ln(8)

    cm_path = os.path.join(FIGURES_DIR, "confusion_matrix.png")
    if os.path.exists(cm_path):
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "4. Confusion Matrix (Visualized)", ln=True)
        pdf.image(cm_path, w=150)

    per_class_path = os.path.join(FIGURES_DIR, "per_class_metrics.png")
    if os.path.exists(per_class_path):
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 10, "5. Per-Class Metrics (Visualized)", ln=True)
        pdf.image(per_class_path, w=150)

    try:
        pdf.output(OUTPUT_PDF)
        print(f"Metrics report saved: {OUTPUT_PDF}")
    except PermissionError:
        alt_pdf = OUTPUT_PDF.replace(".pdf", "_v2.pdf")
        pdf.output(alt_pdf)
        print(f"Metrics report saved: {alt_pdf} (Original was locked)")

if __name__ == "__main__":
    generate_pdf()
