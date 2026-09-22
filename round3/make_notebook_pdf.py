"""
make_notebook_pdf.py - light theme, fully readable PDF export
"""
import os, subprocess, sys, shutil

NB_PATH = os.path.join(os.path.dirname(__file__), "notebooks", "Round3_RealTime_Analysis.ipynb")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "reports")
HTML_OUT = os.path.join(OUT_DIR, "Round3_Notebook.html")
PDF_OUT  = os.path.join(OUT_DIR, "Round3_Notebook_Report.pdf")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Fira+Code&display=swap');

* { box-sizing: border-box; }

body, html {
    background: #ffffff !important;
    color: #1a1a2e !important;
    font-family: 'Inter', -apple-system, sans-serif !important;
    font-size: 13px !important;
    line-height: 1.75 !important;
    margin: 0 !important; padding: 0 !important;
}

#notebook-container, .container, .notebook-container, #notebook {
    background: #ffffff !important;
    max-width: 980px !important;
    margin: 0 auto !important;
    padding: 20px 36px !important;
    box-shadow: none !important; border: none !important;
}

.cell { border: none !important; background: transparent !important; margin: 8px 0 !important; }
.inner_cell { background: transparent !important; }

.input_area, div.input_area {
    background: #f5f7fc !important;
    border: 1px solid #d8e0f0 !important;
    border-left: 4px solid #3498db !important;
    border-radius: 0 6px 6px 0 !important;
    padding: 12px 14px !important;
}

.output_area, .output_subarea { background: #ffffff !important; color: #1a1a2e !important; }

pre, code, .CodeMirror, .CodeMirror-code, .CodeMirror-line {
    font-family: 'Fira Code', 'Courier New', monospace !important;
    font-size: 11.5px !important;
    background: #f5f7fc !important;
    color: #2d3748 !important;
    border-radius: 4px !important;
}

.output_text pre, .output_stream pre {
    background: #eef3ff !important;
    color: #1a1a2e !important;
    border-left: 3px solid #3498db !important;
    padding: 10px 14px !important;
    border-radius: 0 4px 4px 0 !important;
    font-size: 11px !important;
}

h1, h2, h3, h4, h5 {
    color: #0d1b4b !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    border-bottom: 2px solid #e2e8f4 !important;
    padding-bottom: 6px !important;
    margin-top: 22px !important;
    margin-bottom: 10px !important;
    page-break-after: avoid !important;
}
h1 { font-size: 22px !important; border-bottom-color: #3498db !important; }
h2 { font-size: 17px !important; }
h3 { font-size: 14px !important; }

p, li, span { color: #1a1a2e !important; }
strong, b   { color: #0d1b4b !important; font-weight: 700 !important; }
a           { color: #2563eb !important; }

table, .dataframe {
    border-collapse: collapse !important;
    width: 100% !important;
    background: #ffffff !important;
    border: 1px solid #dce3f0 !important;
    border-radius: 6px !important;
    margin: 14px 0 !important;
}

th, .dataframe th {
    background: #1a2a5e !important;
    color: #ffffff !important;
    padding: 9px 13px !important;
    font-weight: 600 !important;
    font-size: 11.5px !important;
    text-align: left !important;
    border: none !important;
}

td, .dataframe td {
    padding: 7px 13px !important;
    border-bottom: 1px solid #e8edf6 !important;
    color: #1a1a2e !important;
    font-size: 11.5px !important;
    background: #ffffff !important;
}
tr:nth-child(even) td, .dataframe tr:nth-child(even) td { background: #f8fafd !important; }

blockquote {
    border-left: 4px solid #3498db !important;
    background: #eef6ff !important;
    margin: 12px 0 !important;
    padding: 10px 16px !important;
    border-radius: 0 5px 5px 0 !important;
    color: #1a2a5e !important;
}

img { max-width: 100% !important; border-radius: 5px !important; }

hr { border: none !important; border-top: 1px solid #e2e8f4 !important; margin: 18px 0 !important; }

@media print {
    body { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    .cell { page-break-inside: avoid !important; }
    h2 { page-break-after: avoid !important; }
    table { page-break-inside: avoid !important; }
}
</style>

<div style="background:linear-gradient(135deg,#0d1b4b 0%,#1a2a5e 100%);border-radius:10px;padding:30px 36px;margin-bottom:30px;">
  <div style="font-size:24px;font-weight:700;color:#ffffff;margin-bottom:8px;">Data Vortex A'26 &mdash; Round 3 Analysis Notebook</div>
  <div style="font-size:14px;color:#90caf9;margin-bottom:6px;">WhatsApp Privacy Policy 2021: Backlash, Sentiment Shifts &amp; Migration Analysis</div>
  <div style="font-size:11px;color:#b0bec5;">Team: Event Horizon &nbsp;|&nbsp; 14,891 records &nbsp;|&nbsp; 4 sources &nbsp;|&nbsp; Nov 2020 &ndash; Jul 2021</div>
</div>
"""

def run():
    os.makedirs(OUT_DIR, exist_ok=True)
    print("[1] Converting notebook to HTML...")
    result = subprocess.run(
        [sys.executable, "-m", "nbconvert", "--to", "html", "--output", HTML_OUT, NB_PATH],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr[:400]}")
        return
    print(f"  HTML -> {HTML_OUT}")

    print("[2] Injecting light CSS + cover banner...")
    with open(HTML_OUT, "r", encoding="utf-8") as f:
        html = f.read()
    html = html.replace("</head>", CUSTOM_CSS + "\n</head>", 1)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print("[3] PDF conversion...")
    wk = shutil.which("wkhtmltopdf")
    if wk:
        res = subprocess.run([wk, "--page-size", "A4", "--margin-top", "15mm",
                              "--margin-bottom", "15mm", "--margin-left", "15mm",
                              "--margin-right", "15mm", "--background",
                              "--enable-local-file-access", HTML_OUT, PDF_OUT],
                             capture_output=True, text=True)
        if res.returncode == 0:
            print(f"  [OK] PDF via wkhtmltopdf -> {PDF_OUT}"); return
    try:
        import weasyprint
        weasyprint.HTML(filename=HTML_OUT).write_pdf(PDF_OUT)
        print(f"  [OK] PDF via weasyprint -> {PDF_OUT}"); return
    except ImportError:
        pass
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             f"from playwright.sync_api import sync_playwright; "
             f"p=sync_playwright().__enter__(); b=p.chromium.launch(); pg=b.new_page(); "
             f"pg.goto('file:///{HTML_OUT.replace(chr(92),'/')}'); "
             f"pg.pdf(path='{PDF_OUT.replace(chr(92),'/')}',format='A4',print_background=True); "
             f"b.close()"],
            capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print(f"  [OK] PDF via playwright -> {PDF_OUT}"); return
    except Exception:
        pass
    print(f"  HTML only: {HTML_OUT}")

if __name__ == "__main__":
    run()
