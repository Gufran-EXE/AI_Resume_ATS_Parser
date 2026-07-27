# ============================================================
# modules/pdf_generator.py
#
# Responsibility: Generate a clean, professional, downloadable
# PDF report summarizing the ATS analysis and AI feedback.
# Uses reportlab.
# ============================================================

from __future__ import annotations

import io
import re
import datetime
from typing import TYPE_CHECKING

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
)
from reportlab.pdfgen import canvas

if TYPE_CHECKING:
    from modules.ats_scoring import ATSResult
    from modules.keyword_matcher import MatchResult, KeywordResult
    from modules.llm_analyzer import LLMReport
    from modules.skill_recommender import SkillRecommendations
    from modules.section_analyzer import SectionAnalysis
    from modules.resume_parser import ParseResult


# ─────────────────────────────────────────────────────────────────────────────
# Custom Canvas for Headers, Footers, and Page Numbers
# ─────────────────────────────────────────────────────────────────────────────

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total page counts and render
    consistent headers, footers, and page numbers on all pages.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict] = []

    def showPage(self):
        # Save page state for the second pass
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        
        # Color definitions
        muted_grey = colors.HexColor("#64748B")
        border_color = colors.HexColor("#E2E8F0")
        
        # Printable limits for Letter with 36pt margins: Width 612, Height 792
        left_margin = 36
        right_margin = 576
        top_line_y = 756
        bottom_line_y = 44
        
        # Header (on all pages)
        self.setStrokeColor(border_color)
        self.setLineWidth(0.5)
        self.line(left_margin, top_line_y, right_margin, top_line_y)
        
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#1E1B4B"))
        self.drawString(left_margin, top_line_y + 6, "AI RESUME OPTIMIZER & ATS ANALYZER")
        
        self.setFont("Helvetica", 8)
        self.setFillColor(muted_grey)
        self.drawRightString(right_margin, top_line_y + 6, "Detailed Evaluation Report")
        
        # Footer (on all pages)
        self.line(left_margin, bottom_line_y, right_margin, bottom_line_y)
        
        # Footer text
        self.drawString(left_margin, bottom_line_y - 14, "Confidential · Evaluated Locally using Llama3")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(right_margin, bottom_line_y - 14, page_text)
        
        self.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions for formatting and parsing text
# ─────────────────────────────────────────────────────────────────────────────

def markdown_to_html(text: str) -> str:
    """Translate basic markdown (bold, italic, code) into reportlab HTML-like tags."""
    if not text:
        return ""
    # XML escaping
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Restore HTML-like tag compatibility for reportlab formatting if we use them later
    text = text.replace("&amp;lt;", "&lt;").replace("&amp;gt;", "&gt;")
    # Bold **text** -> <b>text</b>
    text = re.compile(r"\*\*(.*?)\*\*").sub(r"<b>\1</b>", text)
    # Italic *text* -> <i>text</i>
    text = re.compile(r"\*(.*?)\*").sub(r"<i>\1</i>", text)
    # Inline code `code` -> <font name="Courier">code</font>
    text = re.compile(r"`(.*?)`").sub(r'<font name="Courier">\1</font>', text)
    return text


def add_formatted_content(story: list, text: str, body_style: ParagraphStyle, bullet_style: ParagraphStyle):
    """
    Split Llama3 generated text block into separate Flowables (Paragraphs/Bullets),
    translating inline markdown elements.
    """
    if not text or not text.strip():
        story.append(Paragraph("<i>No content generated for this section.</i>", body_style))
        return

    lines = text.split("\n")
    for line in lines:
        cleaned = line.strip()
        if not cleaned:
            continue
        
        # Check if it is a bullet point
        is_bullet = False
        bullet_text = cleaned
        
        if cleaned.startswith("- "):
            is_bullet = True
            bullet_text = cleaned[2:]
        elif cleaned.startswith("* "):
            is_bullet = True
            bullet_text = cleaned[2:]
        elif re.match(r"^\d+\.\s+", cleaned):
            match = re.match(r"^(\d+\.\s+)(.*)", cleaned)
            if match:
                is_bullet = True
                # Format as numbered bullet
                bullet_text = f"<b>{match.group(1)}</b>{match.group(2)}"
        
        html_text = markdown_to_html(bullet_text)
        if is_bullet:
            bullet_char = "&bull; " if not cleaned[0].isdigit() else ""
            story.append(Paragraph(f"{bullet_char}{html_text}", bullet_style))
        else:
            story.append(Paragraph(html_text, body_style))


# ─────────────────────────────────────────────────────────────────────────────
# Main PDF Generator Function
# ─────────────────────────────────────────────────────────────────────────────

def generate_pdf_report(
    parsed: ParseResult,
    ats: ATSResult,
    match: MatchResult,
    resume_kw: KeywordResult,
    jd_kw: KeywordResult,
    report: LLMReport,
    recs: SkillRecommendations,
    section_analysis: SectionAnalysis,
    filename: str = "ATS_Resume_Analysis_Report.pdf"
) -> bytes:
    """
    Generate the full PDF report and return the raw bytes.
    """
    buffer = io.BytesIO()
    
    # Page setup - Letter with 36pt (0.5 inch) margins
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )
    
    # ─────────────────────────────────────────────────────────────────────────
    # Design System & Styling
    # ─────────────────────────────────────────────────────────────────────────
    primary_color = colors.HexColor("#0F0C29")      # Dark Navy
    secondary_color = colors.HexColor("#7C3AED")    # Purple
    text_color = colors.HexColor("#1F2937")         # Dark Grey
    light_bg = colors.HexColor("#F9FAFB")           # Muted light grey
    border_color = colors.HexColor("#E5E7EB")       # Soft grey border
    
    # Determine color for score
    score = ats["total_score"]
    if score >= 75:
        score_color = colors.HexColor("#10B981")     # Green
    elif score >= 50:
        score_color = colors.HexColor("#F59E0B")     # Orange
    else:
        score_color = colors.HexColor("#EF4444")     # Red

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=primary_color,
        spaceAfter=4
    )
    
    meta_style = ParagraphStyle(
        'DocMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#6B7280"),
        spaceAfter=15
    )
    
    h1_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    
    h2_style = ParagraphStyle(
        'SubsectionHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=text_color,
        spaceAfter=5
    )
    
    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=text_color,
        leftIndent=15,
        firstLineIndent=-8,
        spaceAfter=4
    )

    tag_style = ParagraphStyle(
        'TagText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_color
    )
    
    story = []
    
    # ─────────────────────────────────────────────────────────────────────────
    # 1. Document Title & Header
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("ATS Resume Optimization Report", title_style))
    date_str = datetime.date.today().strftime("%B %d, %Y")
    filename_clean = filename.replace("_", " ").replace(".pdf", "")
    story.append(Paragraph(f"<b>Evaluated Date:</b> {date_str} &nbsp;|&nbsp; <b>Resume:</b> {filename_clean}", meta_style))
    story.append(Spacer(1, 4))
    
    # ─────────────────────────────────────────────────────────────────────────
    # 2. Score Banner and Breakdown Row
    # ─────────────────────────────────────────────────────────────────────────
    # Left Box: Score details
    score_html = f"""
    <font size="10" color="#6B7280">ATS COMPATIBILITY SCORE</font><br/>
    <font size="32" color="{score_color.hexval()}"><b>{score}</b></font><font size="14" color="#9CA3AF">/100</font><br/>
    <font size="12" color="{score_color.hexval()}"><b>Grade: {ats['grade']} &nbsp;·&nbsp; {ats['status']}</b></font>
    """
    score_p = Paragraph(score_html, ParagraphStyle('ScoreP', parent=styles['Normal'], leading=18))
    
    # Right Box: Breakdown values
    bd = ats["breakdown"]
    breakdown_data = [
        [Paragraph("<b>Scoring Metric</b>", tag_style), Paragraph("<b>Score</b>", tag_style), Paragraph("<b>Max</b>", tag_style)],
        [Paragraph("Keyword Match", tag_style), f"{bd['keyword_score']:.0f}", f"{bd['keyword_max']}"],
        [Paragraph("Category Coverage", tag_style), f"{bd['coverage_score']:.0f}", f"{bd['coverage_max']}"],
        [Paragraph("Keyword Depth", tag_style), f"{bd['depth_score']:.0f}", f"{bd['depth_max']}"],
        [Paragraph("Soft Skills", tag_style), f"{bd['soft_score']:.0f}", f"{bd['soft_max']}"]
    ]
    breakdown_table = Table(breakdown_data, colWidths=[150, 60, 60])
    breakdown_table.setStyle(TableStyle([
        ('TEXTCOLOR', (0,0), (-1,-1), text_color),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,0), (-1,0), 0.5, border_color),
        ('LINEBELOW', (0,1), (-1,-1), 0.25, colors.HexColor("#F3F4F6")),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
    ]))
    
    # Combined Row Table
    summary_table_data = [[score_p, breakdown_table]]
    # printable width is 540. Let's split 220 / 320
    summary_table = Table(summary_table_data, colWidths=[220, 320])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), light_bg),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (0,0), 1.5, score_color),
        ('PADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (0,0), 12),
        ('BOTTOMPADDING', (0,0), (0,0), 12),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Resume Section Audit & Completeness
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Resume Section Audit", h1_style))
    
    # Split section results in columns or Table
    audit_header = [Paragraph("<b>Section</b>", tag_style), Paragraph("<b>Status</b>", tag_style), Paragraph("<b>Word Count</b>", tag_style)]
    audit_rows = [audit_header]
    for s_name, s_info in section_analysis["sections"].items():
        status_label = s_info["status"].replace("_", " ").title()
        if s_info["status"] == "present":
            status_html = f'<font color="#10B981"><b>{status_label}</b></font>'
        elif s_info["status"] == "needs_improvement":
            status_html = f'<font color="#F59E0B"><b>Needs Improvement</b></font>'
        else:
            status_html = f'<font color="#EF4444"><b>{status_label}</b></font>'
            
        wc_label = str(s_info["word_count"]) if s_info["word_count"] > 0 else "—"
        audit_rows.append([
            Paragraph(s_name, tag_style),
            Paragraph(status_html, tag_style),
            Paragraph(wc_label, tag_style)
        ])
    
    # 3 columns table: 540 width -> 200, 200, 140
    audit_table = Table(audit_rows, colWidths=[200, 200, 140])
    audit_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,0), 0.75, primary_color),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('LINEBELOW', (0,1), (-1,-1), 0.25, border_color),
        ('ALIGN', (1,0), (2,-1), 'CENTER'),
    ]))
    story.append(audit_table)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Keyword Match Analysis (Skills)
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Paragraph("Keyword Match Analysis", h1_style))
    
    # Limit number of tags to avoid overflowing
    matched_list = match["matched"][:25]
    missing_list = match["missing"][:25]
    
    matched_html = " &nbsp;·&nbsp; ".join(matched_list) if matched_list else "None matched."
    missing_html = " &nbsp;·&nbsp; ".join(missing_list) if missing_list else "None missing."
    
    # Create paragraphs with tags
    m_p = Paragraph(f'<font color="#047857">{matched_html}</font>', body_style)
    ms_p = Paragraph(f'<font color="#B91C1C">{missing_html}</font>', body_style)
    
    skills_table_data = [
        [Paragraph("<b>✅ Matched Skills</b>", h2_style), Paragraph("<b>❌ Missing Skills</b>", h2_style)],
        [m_p, ms_p]
    ]
    # col widths: 270, 270
    skills_table = Table(skills_table_data, colWidths=[270, 270])
    skills_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.5, border_color),
        ('BACKGROUND', (0,0), (-1,-1), light_bg),
        ('PADDING', (0,0), (-1,-1), 8),
        ('LINEBELOW', (0,0), (-1,0), 0.5, border_color),
    ]))
    story.append(skills_table)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────────────────────
    # 5. AI-Powered Analysis Report
    # ─────────────────────────────────────────────────────────────────────────
    # Force a page break here to keep the report neat
    story.append(PageBreak())
    
    story.append(Paragraph("AI-Powered Detailed Feedback", ParagraphStyle('AiTitle', parent=title_style, fontSize=16, leading=20)))
    story.append(Spacer(1, 6))
    
    # Ordered display of LLM sections
    sections_order = [
        "Overall Resume Review",
        "Strengths",
        "Weaknesses",
        "Missing Technical Skills",
        "Suggestions for Improvement",
        "Resume Summary",
        "Improved Bullet Points",
        "Interview Questions",
        "Career Advice"
    ]
    
    for key in sections_order:
        content = report["sections"].get(key, "").strip()
        if content:
            story.append(Paragraph(key, h1_style))
            add_formatted_content(story, content, body_style, bullet_style)
            story.append(Spacer(1, 4))
            
    # ─────────────────────────────────────────────────────────────────────────
    # 6. Structured Skill Recommendations
    # ─────────────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 8))
    story.append(Paragraph("Targeted Action Plan", ParagraphStyle('PlanTitle', parent=title_style, fontSize=16, leading=20)))
    story.append(Spacer(1, 6))
    
    rec_sections = [
        ("Technologies to Learn", recs["technologies"]),
        ("Frameworks to Learn", recs["frameworks"]),
        ("Certifications to Pursue", recs["certifications"]),
        ("Project Ideas", recs["projects"])
    ]
    
    for title, items in rec_sections:
        if items:
            story.append(Paragraph(title, h1_style))
            for item in items:
                priority_html = ""
                if item["priority"] == "High":
                    priority_html = '<font color="#EF4444"><b>[High]</b></font>'
                elif item["priority"] == "Medium":
                    priority_html = '<font color="#F59E0B"><b>[Medium]</b></font>'
                else:
                    priority_html = '<font color="#10B981"><b>[Low]</b></font>'
                
                desc_html = f"&bull; <b>{item['name']}</b> &mdash; {priority_html} {item['reason']}"
                story.append(Paragraph(markdown_to_html(desc_html), bullet_style))
            story.append(Spacer(1, 4))
            
    # Build Document using NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
