#!/usr/bin/env python3
"""
article_writer.py — Generate a 1,800-word article using Claude and export as a PDF.
Called when a target replies YES to the pitch email.
"""

import io
import time
import anthropic
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from config import ANTHROPIC_API_KEY, AUTHOR_NAME, AUTHOR_BIO, GIF_CONTEXT


# ── Brand colours ──────────────────────────────────────────────────────────────
BLUE   = HexColor("#0a66c2")
DARK   = HexColor("#1a1a2e")
GREY   = HexColor("#555555")
LGREY  = HexColor("#f5f5f5")
WHITE  = HexColor("#ffffff")


def generate_article_text(topic_title: str, bullets: list, blog_name: str,
                           blog_niche: str) -> str:
    """Ask Claude to write a full 1,800-word article. Returns plain text."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    bullets_str = "\n".join(f"- {b}" for b in bullets)

    prompt = f"""Write a high-quality guest post article for "{blog_name}", a {blog_niche} blog.

ARTICLE TITLE: {topic_title}

KEY POINTS TO COVER:
{bullets_str}

About the author:
{GIF_CONTEXT}

WRITING REQUIREMENTS:
- Length: 1,600-2,000 words
- Structure: Introduction, 3-4 main sections with sub-headings, Conclusion
- Tone: Expert but accessible. Not academic. Not salesy.
- Audience: Finance/crypto enthusiasts in India, professionals and investors
- Voice: First person ("I", "we at Grade Institute") is fine but use sparingly
- Add specific data points, examples, or case studies where relevant
- Do NOT mention Grade Capital or Grade Institute of Finance more than twice total
- Do NOT end with a sales pitch or course promotion
- The article must stand alone as genuinely useful content

FORMAT (use these markers exactly):
[INTRO]
...introduction paragraphs...

[SECTION: Section Title Here]
...content...

[SECTION: Another Section Title]
...content...

[SECTION: Another Section Title]
...content...

[CONCLUSION]
...closing paragraphs...

Write the article now. No preamble — start directly with [INTRO]."""

    for attempt in range(3):
        try:
            resp = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=3000,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text.strip()
        except anthropic.RateLimitError:
            wait = 40 * (attempt + 1)
            print(f"    Rate limit — waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            print(f"    Claude error: {e}")
            raise
    raise RuntimeError("Article generation failed after 3 attempts")


def parse_article(raw: str) -> list:
    """
    Parse the structured article text into sections.
    Returns list of dicts: {"type": "intro"|"section"|"conclusion", "title": str, "body": str}
    """
    sections = []
    current_type  = None
    current_title = ""
    current_lines = []

    for line in raw.split("\n"):
        stripped = line.strip()

        if stripped.startswith("[INTRO]"):
            if current_type:
                sections.append({"type": current_type, "title": current_title,
                                  "body": "\n".join(current_lines).strip()})
            current_type, current_title, current_lines = "intro", "Introduction", []

        elif stripped.startswith("[SECTION:"):
            if current_type:
                sections.append({"type": current_type, "title": current_title,
                                  "body": "\n".join(current_lines).strip()})
            title = stripped.replace("[SECTION:", "").replace("]", "").strip()
            current_type, current_title, current_lines = "section", title, []

        elif stripped.startswith("[CONCLUSION]"):
            if current_type:
                sections.append({"type": current_type, "title": current_title,
                                  "body": "\n".join(current_lines).strip()})
            current_type, current_title, current_lines = "conclusion", "Conclusion", []

        else:
            current_lines.append(line)

    if current_type:
        sections.append({"type": current_type, "title": current_title,
                          "body": "\n".join(current_lines).strip()})

    return sections


def build_pdf(topic_title: str, article_text: str, blog_name: str) -> bytes:
    """
    Build a branded PDF from the article text.
    Returns raw PDF bytes.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.5*cm,  bottomMargin=2.5*cm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ArticleTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        textColor=DARK,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    meta_style = ParagraphStyle(
        "Meta",
        fontName="Helvetica",
        fontSize=10,
        textColor=GREY,
        spaceAfter=4,
    )
    section_style = ParagraphStyle(
        "SectionHeading",
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        textColor=BLUE,
        spaceBefore=18,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=11,
        leading=18,
        textColor=DARK,
        alignment=TA_JUSTIFY,
        spaceAfter=10,
    )
    bio_style = ParagraphStyle(
        "Bio",
        fontName="Helvetica",
        fontSize=10,
        leading=15,
        textColor=GREY,
        alignment=TA_LEFT,
    )

    elements = []

    # ── Header banner ──────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"<font color='white'><b>Guest Article — {blog_name}</b></font>", meta_style),
        Paragraph("<font color='#cce4ff'>Grade Institute of Finance</font>", meta_style),
    ]]
    header_table = Table(header_data, colWidths=["60%", "40%"])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), BLUE),
        ("PADDING",     (0, 0), (-1, -1), 10),
        ("ALIGN",       (1, 0), (1, 0),   "RIGHT"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 0.6*cm))

    # ── Title ──────────────────────────────────────────────────────────────────
    elements.append(Paragraph(topic_title, title_style))
    elements.append(Paragraph(f"By <b>{AUTHOR_NAME}</b> · Grade Capital & Grade Institute of Finance",
                               meta_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=BLUE, spaceAfter=12))

    # ── Article body ───────────────────────────────────────────────────────────
    sections = parse_article(article_text)

    for section in sections:
        # Section heading (skip for intro)
        if section["type"] in ("section", "conclusion"):
            elements.append(Paragraph(section["title"], section_style))

        # Body paragraphs
        for para in section["body"].split("\n\n"):
            para = para.strip()
            if not para:
                continue
            # Escape XML special chars
            para = para.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            elements.append(Paragraph(para, body_style))

    # ── Author bio ─────────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GREY))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph("<b>About the Author</b>", section_style))

    bio_text = AUTHOR_BIO.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    elements.append(Paragraph(bio_text, bio_style))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        "LinkedIn: linkedin.com/in/mahaveersoni · Website: grade.capital",
        bio_style
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.read()


def generate_article_pdf(topic_title: str, bullets: list,
                         blog_name: str, blog_niche: str) -> bytes:
    """
    Full pipeline: generate article text with Claude → build PDF.
    Returns PDF bytes ready to attach to an email.
    """
    print(f"    Generating article: {topic_title[:60]}...")
    article_text = generate_article_text(topic_title, bullets, blog_name, blog_niche)
    print(f"    Article generated ({len(article_text.split())} words). Building PDF...")
    pdf_bytes = build_pdf(topic_title, article_text, blog_name)
    print(f"    PDF built ({len(pdf_bytes)//1024} KB)")
    return pdf_bytes
