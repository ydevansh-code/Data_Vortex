import os
import re
from fpdf import FPDF, XPos, YPos

C_BG     = (15,  17,  23)
C_CARD   = (26,  29,  46)
C_ACCENT = (52, 152, 219)
C_GREEN  = (46, 204, 113)
C_RED    = (231, 76,  60)
C_ORANGE = (230, 126,  34)
C_WHITE  = (255, 255, 255)
C_GRAY   = (170, 170, 170)
C_DARK   = ( 30,  30,  45)
C_YELLOW = (241, 196,  15)

class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)

    def normalize_text(self, txt):
        replacements = {
            "—": "-", "≈": "~", "–": "-", "▸": ">", "•": "-",
            "★": "*", "≤": "<=", "×": "x", "→": "->", "±": "+/-",
            "✅": "[YES]", "❌": "[NO]", "≥": ">="
        }
        for k, v in replacements.items():
            txt = str(txt).replace(k, v)
        try:
            return super().normalize_text(txt)
        except Exception:
            return txt.encode("latin-1", "replace").decode("latin-1")

    def header(self):
        self.set_fill_color(*C_BG)
        self.rect(0, 0, 210, 297, "F")
        self.set_fill_color(*C_ACCENT)
        self.rect(0, 0, 210, 6, "F")

    def footer(self):
        self.set_y(-14)
        self.set_fill_color(*C_ACCENT)
        self.rect(0, 283, 210, 6, "F")
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*C_GRAY)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")

    def h1(self, title):
        self.ln(6)
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(*C_ACCENT)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
        self.ln(3)

    def h2(self, title):
        self.ln(6)
        self.set_fill_color(*C_ACCENT)
        self.rect(14, self.get_y(), 182, 8, "F")
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*C_WHITE)
        self.set_x(16)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def h3(self, title):
        self.ln(4)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_ORANGE)
        self.cell(0, 6, f"> {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*C_WHITE)

    def body(self, text, is_bold=False):
        if not text.strip():
            self.ln(2)
            return
        self.set_font("Helvetica", "B" if is_bold else "", 9)
        self.set_text_color(*C_WHITE)
        self.set_x(14)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'`(.*?)`', r'\1', text)
        self.multi_cell(182, 5, text)
        self.ln(1)
        
    def alert(self, text, color):
        self.ln(2)
        self.set_fill_color(*color)
        self.rect(14, self.get_y(), 182, 7, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*C_WHITE)
        self.set_x(16)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        self.cell(0, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def img(self, path):
        if os.path.exists(path):
            self.ln(4)
            self.image(path, x=(210-170)/2, w=170)
            self.ln(4)

pdf = ReportPDF()
pdf.add_page()
pdf.set_y(15)

with open('round2/reports/Final_Technical_Report.md', 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_table = False
table_data = []

for line in lines:
    line = line.strip()
    if line.startswith('|'):
        in_table = True
        if "---" not in line:
            row = [x.strip() for x in line.split('|') if x.strip()]
            table_data.append(row)
        continue
    else:
        if in_table:
            # Render table
            pdf.ln(3)
            col_w = 182 / len(table_data[0])
            for i, row in enumerate(table_data):
                pdf.set_x(14)
                pdf.set_fill_color(*(C_ACCENT if i == 0 else (C_CARD if i % 2 == 0 else C_DARK)))
                pdf.set_font("Helvetica", "B" if i == 0 else "", 8)
                pdf.set_text_color(*C_WHITE)
                for cell in row:
                    cell = re.sub(r'\*\*(.*?)\*\*', r'\1', cell)
                    pdf.cell(col_w, 6, cell, border=1, fill=True)
                pdf.ln()
            pdf.ln(3)
            in_table = False
            table_data = []

    if line.startswith('# '):
        pdf.h1(line[2:])
    elif line.startswith('## '):
        pdf.h2(line[3:])
    elif line.startswith('### '):
        pdf.h3(line[4:])
    elif line.startswith('![') and '](' in line:
        path = line.split('](')[1].split(')')[0]
        # path is relative to markdown file, so we need round2/reports/...
        full_path = os.path.join('round2', 'reports', path)
        pdf.img(full_path)
    elif line.startswith('> [!IMPORTANT]'):
        pdf.alert("IMPORTANT / CRITICAL INFO", C_RED)
    elif line.startswith('> [!WARNING]'):
        pdf.alert("WARNING / AUDIT FINDING", C_ORANGE)
    elif line.startswith('> [!NOTE]'):
        pdf.alert("NOTE", C_ACCENT)
    elif line.startswith('>'):
        pdf.body(line[1:].strip(), is_bold=True)
    elif line.startswith('* '):
        pdf.set_x(18)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(178, 5, "- " + re.sub(r'\*\*(.*?)\*\*', r'\1', line[2:]))
    elif line == '---':
        pdf.ln(3)
    else:
        pdf.body(line)

pdf.output('round2/reports/Round2_Technical_Report.pdf')
print("Saved to round2/reports/Round2_Technical_Report.pdf")
