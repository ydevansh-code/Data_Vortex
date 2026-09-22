"""
make_notebook_pdf.py
Exports Round3_RealTime_Analysis.ipynb to a polished PDF via nbconvert → HTML → wkhtmltopdf or weasyprint.
Falls back to HTML if no PDF converter is found.
"""

import os
import subprocess
import sys
import shutil

NB_PATH = os.path.join(os.path.dirname(__file__), "notebooks", "Round3_RealTime_Analysis.ipynb")
OUT_DIR  = os.path.join(os.path.dirname(__file__), "reports")
HTML_OUT = os.path.join(OUT_DIR, "Round3_Notebook.html")
PDF_OUT  = os.path.join(OUT_DIR, "Round3_Notebook_Report.pdf")

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Fira+Code:wght@400;500&display=swap');

:root {
    --bg: #0f1117;
    --bg2: #1e2129;
    --accent: #3498db;
    --accent2: #2ecc71;
    --text: #c8ccd4;
    --text-bright: #ffffff;
    --heading: #61afef;
    --border: #2d3139;
}

body {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 13px !important;
    line-height: 1.7 !important;
    margin: 0 !important;
    padding: 0 !important;
}

#notebook-container, .container, .notebook-container {
    background: var(--bg) !important;
    max-width: 1000px !important;
    margin: 0 auto !important;
    padding: 24px 32px !important;
    box-shadow: none !important;
}

.cell { border: none !important; background: transparent !important; margin: 8px 0 !important; }

.input_area, div.input_area {
    background: var(--bg2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    padding: 12px !important;
}

.output_area { background: transparent !important; }

pre, code, .CodeMirror, .CodeMirror-code {
    font-family: 'Fira Code', monospace !important;
    font-size: 12px !important;
    background: var(--bg2) !important;
    color: #abb2bf !important;
    border-radius: 4px !important;
}

.output_text pre, .output_stream pre {
    background: var(--bg2) !important;
    color: #abb2bf !important;
    border-left: 3px solid var(--accent) !important;
    padding: 10px !important;
    border-radius: 4px !important;
}

h1, h2, h3, h4 {
    color: var(--heading) !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    border-bottom: 1px solid var(--border) !important;
    padding-bottom: 8px !important;
}

h1 { font-size: 24px !important; color: var(--text-bright) !important; }
h2 { font-size: 18px !important; }
h3 { font-size: 15px !important; }

table {
    border-collapse: collapse !important;
    width: 100% !important;
    background: var(--bg2) !important;
    border-radius: 6px !important;
    overflow: hidden !important;
}

th {
    background: var(--accent) !important;
    color: white !important;
    padding: 10px 14px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
}

td {
    padding: 8px 14px !important;
    border-bottom: 1px solid var(--border) !important;
    color: var(--text) !important;
    font-size: 12px !important;
}

tr:nth-child(even) td { background: rgba(255,255,255,0.03) !important; }
tr:hover td { background: rgba(52,152,219,0.1) !important; }

blockquote {
    border-left: 4px solid var(--accent2) !important;
    background: rgba(46,204,113,0.06) !important;
    margin: 12px 0 !important;
    padding: 10px 16px !important;
    border-radius: 0 4px 4px 0 !important;
    color: #aaffcc !important;
}

img { max-width: 100% !important; border-radius: 6px !important; }

.cover-banner {
    background: linear-gradient(135deg, #1a1e2e 0%, #0f1117 50%, #1a2233 100%) !important;
    border-left: 4px solid var(--accent) !important;
    padding: 28px 32px !important;
    margin-bottom: 32px !important;
    border-radius: 0 8px 8px 0 !important;
}

.dataframe { font-size: 11px !important; }

@media print {
    body { background: #0f1117 !important; -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    .cell { page-break-inside: avoid !important; }
    h2 { page-break-before: auto !important; }
}
</style>

<div class="cover-banner">
  <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:8px;">Data Vortex A'26 — Round 3 Analysis Notebook</div>
  <div style="font-size:13px;color:#3498db;margin-bottom:4px;">WhatsApp Privacy Policy 2021: Real-Time Social Monitoring</div>
  <div style="font-size:11px;color:#888;">Team: Event Horizon &nbsp;|&nbsp; 14,891 records &nbsp;|&nbsp; 4 sources &nbsp;|&nbsp; Nov 2020 – Jul 2021</div>
</div>
"""

def run():
    os.makedirs(OUT_DIR, exist_ok=True)

    print("[1] Converting notebook to HTML via nbconvert...")
    result = subprocess.run(
        [sys.executable, "-m", "nbconvert",
         "--to", "html",
         "--no-input",
         "--output", HTML_OUT,
         NB_PATH],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"  nbconvert (no-input) failed: {result.stderr[:300]}")
        print("  Retrying with input cells included...")
        result = subprocess.run(
            [sys.executable, "-m", "nbconvert",
             "--to", "html",
             "--output", HTML_OUT,
             NB_PATH],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  ERROR: {result.stderr[:500]}")
            return

    print(f"  HTML written -> {HTML_OUT}")

    print("[2] Injecting custom dark CSS + cover banner...")
    with open(HTML_OUT, "r", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("</head>", CUSTOM_CSS + "\n</head>", 1)

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print("[3] Attempting PDF conversion...")
    # Try wkhtmltopdf first
    wk = shutil.which("wkhtmltopdf")
    if wk:
        res = subprocess.run(
            [wk,
             "--page-size", "A4",
             "--margin-top", "15mm",
             "--margin-bottom", "15mm",
             "--margin-left", "15mm",
             "--margin-right", "15mm",
             "--background",
             "--enable-local-file-access",
             HTML_OUT, PDF_OUT],
            capture_output=True, text=True
        )
        if res.returncode == 0:
            print(f"  [OK] PDF written via wkhtmltopdf -> {PDF_OUT}")
            return
        else:
            print(f"  wkhtmltopdf failed: {res.stderr[:200]}")

    # Try weasyprint
    try:
        import weasyprint
        weasyprint.HTML(filename=HTML_OUT).write_pdf(PDF_OUT)
        print(f"  [OK] PDF written via weasyprint -> {PDF_OUT}")
        return
    except ImportError:
        pass

    # Try Playwright/Chromium headless via subprocess
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             f"from playwright.sync_api import sync_playwright; "
             f"p=sync_playwright().__enter__(); b=p.chromium.launch(); pg=b.new_page(); "
             f"pg.goto('file:///{HTML_OUT.replace(chr(92), '/')}'); "
             f"pg.pdf(path='{PDF_OUT.replace(chr(92), '/')}',format='A4',print_background=True); "
             f"b.close()"],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            print(f"  [OK] PDF written via playwright -> {PDF_OUT}")
            return
    except Exception:
        pass

    print(f"  [INFO] No PDF converter found. HTML report available at:\n  {HTML_OUT}")
    print("  To generate PDF: pip install weasyprint  OR  install wkhtmltopdf")


if __name__ == "__main__":
    run()
