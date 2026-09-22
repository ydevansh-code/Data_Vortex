"""
make_scraper_pdf.py
Generates Round3_DataCollection_Script.pdf — a structured document
with one section per data source: heading, intro, then the Python code.
Output: round3/reports/Round3_DataCollection_Script.pdf
"""

import os
import textwrap
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    HRFlowable, Table, TableStyle, Preformatted
)
from reportlab.lib.fonts import addMapping
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT_PATH = os.path.join(os.path.dirname(__file__), "reports", "Round3_DataCollection_Script.pdf")
COLLECTORS_DIR = os.path.join(os.path.dirname(__file__), "src", "collectors")

DARK_BG   = colors.HexColor("#0f1117")
ACCENT    = colors.HexColor("#3498db")
ACCENT2   = colors.HexColor("#2ecc71")
TEXT_WHITE= colors.white
TEXT_LIGHT= colors.HexColor("#c8ccd4")
CODE_BG   = colors.HexColor("#1e2129")
CODE_FG   = colors.HexColor("#abb2bf")
HEADING_C = colors.HexColor("#61afef")

PAGE_W, PAGE_H = A4

SOURCES = [
    {
        "name": "1. GDELT Global News",
        "file": "gdelt_collector.py",
        "badge": "Live API  \u2022  No Auth Required  \u2022  7,953 articles collected across 3 runs",
        "intro": (
            "GDELT (Global Database of Events, Language, and Tone) is one of the world's largest "
            "open databases of human society, updated every 15 minutes. It indexes news articles "
            "from thousands of global sources across hundreds of languages.\n\n"
            "We used the GDELT DOC 2.0 API to pull English-language news articles mentioning "
            "WhatsApp privacy keywords across our full date window (Nov 2020 - Jul 2021). "
            "The collector queries four themed search terms in 28-day batches, enforcing GDELT's "
            "mandatory 5-second politeness delay between every request. Results are saved "
            "incrementally and de-duplicated by URL to prevent double-counting across overlapping "
            "query windows. Three collection runs were executed producing 1,953 + 2,250 + 3,750 "
            "records respectively, totalling 7,953 unique news articles."
        ),
    },
    {
        "name": "2. Hacker News (Algolia API)",
        "file": "hn_collector.py",
        "badge": "Live API  \u2022  No Auth Required  \u2022  6,149 posts collected across 4 runs",
        "intro": (
            "Hacker News is the premier tech-community discussion platform, run by Y Combinator. "
            "Its audience skews toward developers, researchers, and privacy-conscious power users "
            "making it an ideal signal source for tech-savvy sentiment around WhatsApp's policy changes.\n\n"
            "We used the free Algolia HN Search API (no authentication required) to fetch "
            "all stories and comments matching four query terms within the Jan-Jul 2021 "
            "window. HTML entities returned by the API are cleaned inline before saving. "
            "Four collection runs produced 1,538 + 1,179 + 1,539 + 1,893 records "
            "totalling 6,149 unique posts — the largest single live-scraped source in our dataset."
        ),
    },
    {
        "name": "3. Kaggle Play Store Reviews",
        "file": "kaggle_collector.py",
        "badge": "External Dataset  \u2022  Multilingual (EN + ID)  \u2022  Primary Data Source",
        "intro": (
            "Two large Kaggle datasets were ingested as primary data sources: a WhatsApp Play "
            "Store review dump and a Telegram Play Store review dump containing Indonesian-language "
            "reviews from the Jan-Jul 2021 privacy backlash period.\n\n"
            "The collector applies a five-stage pipeline: (1) strict date range filter to Jan-Jul 2021, "
            "(2) keyword noise filter in both English and Indonesian (privacy, privasi, kebijakan, "
            "telegram, signal, etc.), (3) random sampling capped at 3,000 rows per dataset to "
            "respect translation API rate limits, (4) batch translation of Indonesian text to English "
            "using deep_translator (Google Translate), and (5) schema harmonisation to our "
            "pipeline's standard column format. This source forms the backbone of our App Store "
            "sentiment layer and the Telegram migration signal."
        ),
    },
]



def read_code(filename):
    path = os.path.join(COLLECTORS_DIR, filename)
    if not os.path.exists(path):
        return f"# File not found: {path}"
    with open(path, encoding="utf-8") as f:
        return f.read()


def build_styles():
    styles = getSampleStyleSheet()

    cover_title = ParagraphStyle(
        "CoverTitle", parent=styles["Normal"],
        fontSize=28, leading=36, textColor=TEXT_WHITE,
        alignment=TA_CENTER, spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    cover_sub = ParagraphStyle(
        "CoverSub", parent=styles["Normal"],
        fontSize=14, leading=18, textColor=ACCENT,
        alignment=TA_CENTER, spaceAfter=4,
        fontName="Helvetica",
    )
    cover_meta = ParagraphStyle(
        "CoverMeta", parent=styles["Normal"],
        fontSize=10, leading=14, textColor=TEXT_LIGHT,
        alignment=TA_CENTER,
        fontName="Helvetica",
    )
    section_head = ParagraphStyle(
        "SectionHead", parent=styles["Normal"],
        fontSize=18, leading=24, textColor=HEADING_C,
        spaceBefore=18, spaceAfter=6,
        fontName="Helvetica-Bold",
    )
    badge_style = ParagraphStyle(
        "Badge", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=ACCENT2,
        spaceAfter=10, fontName="Helvetica-Oblique",
    )
    body_style = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=15, textColor=TEXT_LIGHT,
        alignment=TA_JUSTIFY, spaceAfter=12,
        fontName="Helvetica",
    )
    code_label = ParagraphStyle(
        "CodeLabel", parent=styles["Normal"],
        fontSize=9, leading=12, textColor=ACCENT,
        spaceBefore=8, spaceAfter=4,
        fontName="Helvetica-Bold",
    )
    toc_style = ParagraphStyle(
        "TocStyle", parent=styles["Normal"],
        fontSize=11, leading=20, textColor=TEXT_LIGHT,
        fontName="Helvetica",
    )
    return {
        "cover_title": cover_title,
        "cover_sub": cover_sub,
        "cover_meta": cover_meta,
        "section_head": section_head,
        "badge": badge_style,
        "body": body_style,
        "code_label": code_label,
        "toc": toc_style,
    }


def dark_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(ACCENT)
    canvas.rect(0, 0, PAGE_W, 3, fill=1, stroke=0)
    canvas.setFillColor(TEXT_LIGHT)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(20*mm, 10*mm, "Data Vortex A'26  |  Team: Event Horizon  |  Round 3 — Data Collection")
    canvas.drawRightString(PAGE_W - 20*mm, 10*mm, f"Page {doc.page}")
    canvas.restoreState()


def make_preformatted(code_text):
    MAX_LINE = 95
    wrapped_lines = []
    for line in code_text.split("\n"):
        if len(line) <= MAX_LINE:
            wrapped_lines.append(line)
        else:
            indent = len(line) - len(line.lstrip())
            cont_indent = " " * (indent + 4)
            chunks = textwrap.wrap(line, width=MAX_LINE, subsequent_indent=cont_indent)
            wrapped_lines.extend(chunks)

    return Preformatted(
        "\n".join(wrapped_lines),
        ParagraphStyle(
            "Code", fontSize=7, leading=9.5,
            fontName="Courier", textColor=CODE_FG,
            backColor=CODE_BG,
            leftIndent=8, rightIndent=8,
            spaceBefore=4, spaceAfter=12,
        ),
    )


def build_pdf():
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    doc = SimpleDocTemplate(
        OUT_PATH, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=22*mm,
    )
    S = build_styles()
    story = []

    story.append(Spacer(1, 40*mm))
    story.append(Paragraph("Data Vortex A'26", S["cover_title"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Round 3 — Data Collection Scripts", S["cover_sub"]))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="60%", thickness=1, color=ACCENT, spaceAfter=10))
    story.append(Paragraph("WhatsApp Privacy Policy 2021: Backlash, Sentiment &amp; Migration Analysis", S["cover_meta"]))
    story.append(Spacer(1, 4*mm))
    story.append(Paragraph("Team: Event Horizon", S["cover_meta"]))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Total Records Collected: 14,891 across 4 sources", S["cover_meta"]))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph("Date Coverage: Nov 2020 – Jul 2021", S["cover_meta"]))

    story.append(Spacer(1, 20*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceAfter=12))
    story.append(Paragraph("Table of Contents", ParagraphStyle(
        "TOCTitle", fontSize=13, textColor=HEADING_C,
        fontName="Helvetica-Bold", spaceAfter=8,
    )))
    for s in SOURCES:
        story.append(Paragraph(f"  {s['name']}", S["toc"]))
    story.append(PageBreak())

    for s in SOURCES:
        story.append(Paragraph(s["name"], S["section_head"]))
        story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceAfter=8))
        story.append(Paragraph(f"◆  {s['badge']}", S["badge"]))

        for para in s["intro"].split("\n\n"):
            story.append(Paragraph(para.strip(), S["body"]))

        story.append(Paragraph(f"▶  Collector Script: {s['file']}", S["code_label"]))
        code_text = read_code(s["file"])
        story.append(make_preformatted(code_text))
        story.append(PageBreak())

    doc.build(story, onFirstPage=dark_page, onLaterPages=dark_page)
    print(f"[OK] PDF written -> {OUT_PATH}")


if __name__ == "__main__":
    build_pdf()
