#!/usr/bin/env python3
"""
build_pdf.py — Converts Phase2_Submission.md to a styled PDF using fpdf2 + Pillow.
Run from repo root: python build_pdf.py
"""
import re, textwrap, os
from pathlib import Path
from fpdf import FPDF
from PIL import Image

MD = Path("phase2/Phase2_Submission.md")
OUT = Path("phase2/Phase2_Submission.pdf")
SCREENSHOTS = Path("phase2/screenshots")

def sanitize(s):
    """Replace non-latin-1 characters with ASCII equivalents."""
    return (s.replace('\u2014', '--').replace('\u2013', '-')
             .replace('\u2019', "'").replace('\u2018', "'")
             .replace('\u201c', '"').replace('\u201d', '"')
             .replace('\u00b7', '*').replace('\u2022', '-')
             .replace('\u2026', '...').encode('latin-1', errors='replace').decode('latin-1'))


# ── Read markdown ────────────────────────────────────────────────────────────
text = sanitize(MD.read_text(encoding='utf-8'))

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, 'Data Vortex 2026 -- Phase 2 Submission -- Team: Event Horizon', align='C')
        self.ln(2)
        self.set_draw_color(200, 200, 200)
        self.line(18, self.get_y(), self.w - 18, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(130, 130, 130)
        self.cell(0, 8, f'Page {self.page_no()}', align='C')


pdf = PDF()
pdf.add_page()

def strip_inline(s):
    """Remove inline markdown like `code`, **bold**, *italic*."""
    s = re.sub(r'\*\*(.+?)\*\*', r'\1', s)
    s = re.sub(r'\*(.+?)\*', r'\1', s)
    s = re.sub(r'`([^`]+)`', r'\1', s)
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', s)
    return s

def embed_image(pdf, img_path, max_w=170):
    """Add image centered on page, skip if not valid."""
    try:
        with Image.open(img_path) as im:
            w_px, h_px = im.size
        ratio = h_px / w_px
        img_w = min(max_w, pdf.w - 36)
        img_h = img_w * ratio
        x = (pdf.w - img_w) / 2
        if pdf.get_y() + img_h + 10 > pdf.h - 20:
            pdf.add_page()
        pdf.image(str(img_path), x=x, y=pdf.get_y(), w=img_w)
        pdf.ln(img_h + 4)
    except Exception as e:
        pdf.set_font('Helvetica', 'I', 8)
        pdf.set_text_color(180, 60, 60)
        pdf.cell(0, 6, f'[Image load error: {e}]', ln=True)
        pdf.set_text_color(30, 30, 30)

lines = text.splitlines()
i = 0
code_block = False
code_lines = []
table_rows = []
in_table = False

while i < len(lines):
    line = lines[i]

    # ── Code block ────────────────────────────────────────────────────────────
    if line.strip().startswith('```'):
        if not code_block:
            code_block = True
            code_lines = []
        else:
            code_block = False
            pdf.set_font('Courier', '', 7.5)
            pdf.set_fill_color(240, 240, 245)
            pdf.set_text_color(30, 30, 80)
            block = '\n'.join(code_lines)
            # Wrap long lines
            wrapped = []
            for cl in code_lines:
                if len(cl) > 100:
                    wrapped.extend(textwrap.wrap(cl, 100, subsequent_indent='    '))
                else:
                    wrapped.append(cl)
            pdf.set_x(18)
            pdf.multi_cell(0, 4.5, '\n'.join(wrapped), fill=True, border=0)
            pdf.ln(3)
            pdf.set_text_color(30, 30, 30)
        i += 1
        continue
    if code_block:
        code_lines.append(line)
        i += 1
        continue

    # ── Embedded image ────────────────────────────────────────────────────────
    img_match = re.match(r'!\[([^\]]*)\]\(([^\)]+)\)', line.strip())
    if img_match:
        img_rel = img_match.group(2)
        img_path = Path('phase2') / img_rel.lstrip('./')
        embed_image(pdf, img_path)
        i += 1
        continue

    # ── Table ─────────────────────────────────────────────────────────────────
    if line.strip().startswith('|'):
        # Collect full table
        tbl_lines = []
        while i < len(lines) and lines[i].strip().startswith('|'):
            tbl_lines.append(lines[i])
            i += 1
        # Parse
        rows = []
        for tl in tbl_lines:
            if re.match(r'\|[-| :]+\|', tl):
                continue
            cols = [c.strip() for c in tl.strip('|').split('|')]
            cols = [strip_inline(c) for c in cols]
            rows.append(cols)
        if not rows:
            continue
        n_cols = len(rows[0])
        col_w = (pdf.w - 36) / n_cols
        pdf.set_font('Helvetica', 'B', 8)
        pdf.set_fill_color(220, 230, 245)
        for c in rows[0]:
            pdf.cell(col_w, 7, c[:25], border=1, fill=True, align='C')
        pdf.ln()
        pdf.set_font('Helvetica', '', 7.5)
        for r_idx, row in enumerate(rows[1:]):
            fill = r_idx % 2 == 0
            pdf.set_fill_color(248, 248, 252) if fill else pdf.set_fill_color(255, 255, 255)
            for c in row:
                pdf.cell(col_w, 6.5, c[:25], border=1, fill=True)
            pdf.ln()
        pdf.ln(3)
        continue

    # ── Headings ──────────────────────────────────────────────────────────────
    h1 = re.match(r'^# (.+)', line)
    h2 = re.match(r'^## (.+)', line)
    h3 = re.match(r'^### (.+)', line)
    h4 = re.match(r'^#### (.+)', line)

    if h1:
        pdf.set_font('Helvetica', 'B', 18)
        pdf.set_text_color(20, 60, 130)
        pdf.ln(4)
        pdf.multi_cell(0, 10, strip_inline(h1.group(1)), align='C')
        pdf.set_draw_color(20, 60, 130)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(30, 30, 30)
    elif h2:
        pdf.ln(4)
        pdf.set_font('Helvetica', 'B', 13)
        pdf.set_text_color(20, 80, 160)
        pdf.multi_cell(0, 8, strip_inline(h2.group(1)))
        pdf.set_draw_color(180, 200, 230)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(2)
        pdf.set_text_color(30, 30, 30)
    elif h3:
        pdf.ln(3)
        pdf.set_font('Helvetica', 'B', 11)
        pdf.set_text_color(40, 100, 180)
        pdf.multi_cell(0, 7, strip_inline(h3.group(1)))
        pdf.ln(1)
        pdf.set_text_color(30, 30, 30)
    elif h4:
        pdf.ln(2)
        pdf.set_font('Helvetica', 'BI', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.multi_cell(0, 6, strip_inline(h4.group(1)))
        pdf.set_text_color(30, 30, 30)
    elif line.strip() == '---':
        pdf.ln(2)
        pdf.set_draw_color(200, 200, 200)
        pdf.line(18, pdf.get_y(), pdf.w - 18, pdf.get_y())
        pdf.ln(3)
    elif line.strip().startswith('**') and line.strip().endswith('**'):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.multi_cell(0, 6, strip_inline(line.strip()))
        pdf.set_font('Helvetica', '', 10)
    elif line.strip().startswith('- ') or line.strip().startswith('* '):
        pdf.set_font('Helvetica', '', 9.5)
        content = strip_inline(line.strip()[2:])
        pdf.set_x(18)
        pdf.cell(5, 5.5, '-')
        pdf.set_x(24)
        pdf.multi_cell(pdf.w - 24 - 18, 5.5, content)
    elif line.strip() == '':
        pdf.ln(2)
    else:
        pdf.set_font('Helvetica', '', 9.5)
        pdf.set_x(18)
        clean = strip_inline(line)
        if clean.strip():
            pdf.multi_cell(pdf.w - 36, 5.5, clean)

    i += 1

pdf.output(str(OUT))
print(f"PDF written: {OUT} ({os.path.getsize(OUT):,} bytes)")
