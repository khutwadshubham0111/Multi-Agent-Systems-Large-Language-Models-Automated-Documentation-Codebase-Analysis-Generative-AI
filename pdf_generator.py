import io
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and print 'Page X of Y'."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748b"))

        # Header (pages after cover/first page)
        if self._pageNumber > 1:
            self.drawString(54, 755, "AI Codebase Documentation Generator")
            self.setStrokeColor(colors.HexColor("#e2e8f0"))
            self.setLineWidth(0.5)
            self.line(54, 747, 558, 747)

        # Footer on all pages
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_str)
        self.drawString(
            54,
            36,
            "Confidential - Generated automatically by Multi-Agent AI System",
        )
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 48, 558, 48)

        self.restoreState()


def format_inline_markdown(text: str) -> str:
    """Escapes XML and converts markdown bold, italic, and inline code to ReportLab tags."""
    # First escape basic XML characters
    text = escape(text)

    # Inline bold: **bold**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Inline italic: *italic*
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)

    # Inline code: `code`
    text = re.sub(
        r"`([^`]+)`",
        r'<font face="Courier" color="#4338ca"><b>\1</b></font>',
        text,
    )

    return text


def generate_pdf(
    project_name: str,
    documentation_text: str,
    author_username: str = "Administrator",
) -> bytes:
    """Converts documentation markdown text into a styled, professional PDF document."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1e1b4b"),
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "H1Style",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )

    h2_style = ParagraphStyle(
        "H2Style",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )

    h3_style = ParagraphStyle(
        "H3Style",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4338ca"),
        spaceBefore=8,
        spaceAfter=3,
        keepWithNext=True,
    )

    body_style = ParagraphStyle(
        "BodyStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "BulletStyle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        "CodeStyle",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f172a"),
    )

    story = []

    # Title Banner Block
    story.append(Paragraph(format_inline_markdown(f"Technical Documentation: {project_name}"), title_style))
    story.append(Paragraph("Automated Analysis generated by Multi-Agent AI System", subtitle_style))

    # Metadata summary box
    now_str = datetime.now().strftime("%B %d, %Y - %H:%M:%S")
    meta_data = [
        [
            Paragraph(f"<b>Project:</b> {escape(project_name)}", body_style),
            Paragraph(f"<b>Date:</b> {now_str}", body_style),
        ],
        [
            Paragraph(f"<b>Generated By:</b> {escape(author_username)}", body_style),
            Paragraph("<b>Status:</b> Completed", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[250, 254])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#f1f5f9")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Parse documentation markdown lines
    lines = documentation_text.splitlines()
    in_code_block = False
    code_lines = []

    for line in lines:
        stripped = line.strip()

        # Handle code blocks
        if stripped.startswith("```"):
            if in_code_block:
                # Close code block
                in_code_block = False
                code_text = "\n".join(code_lines)
                code_lines = []
                p_code = Paragraph(
                    "<br/>".join(escape(cl) for cl in code_text.split("\n")),
                    code_style,
                )
                code_table = Table([[p_code]], colWidths=[504])
                code_table.setStyle(
                    TableStyle(
                        [
                            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                            ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                            ("TOPPADDING", (0, 0), (-1, -1), 6),
                            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ]
                    )
                )
                story.append(code_table)
                story.append(Spacer(1, 8))
            else:
                in_code_block = True
                code_lines = []
            continue

        if in_code_block:
            code_lines.append(line)
            continue

        if not stripped:
            story.append(Spacer(1, 4))
            continue

        # Headers
        if stripped.startswith("### "):
            header_text = stripped[4:]
            story.append(Paragraph(format_inline_markdown(header_text), h3_style))
        elif stripped.startswith("## "):
            header_text = stripped[3:]
            story.append(
                KeepTogether(
                    [
                        Spacer(1, 4),
                        Paragraph(format_inline_markdown(header_text), h1_style),
                        HRFlowable(
                            width="100%",
                            thickness=1,
                            color=colors.HexColor("#6366f1"),
                            spaceBefore=2,
                            spaceAfter=6,
                        ),
                    ]
                )
            )
        elif stripped.startswith("# "):
            header_text = stripped[2:]
            story.append(
                KeepTogether(
                    [
                        Spacer(1, 6),
                        Paragraph(format_inline_markdown(header_text), h1_style),
                        HRFlowable(
                            width="100%",
                            thickness=1.5,
                            color=colors.HexColor("#4f46e5"),
                            spaceBefore=3,
                            spaceAfter=8,
                        ),
                    ]
                )
            )
        # Bullet list items
        elif stripped.startswith(("- ", "* ")):
            bullet_content = stripped[2:]
            story.append(
                Paragraph(
                    f"&bull; {format_inline_markdown(bullet_content)}",
                    bullet_style,
                )
            )
        # Numbered list items
        elif re.match(r"^\d+\.\s+", stripped):
            num_content = re.sub(r"^\d+\.\s+", "", stripped)
            story.append(
                Paragraph(
                    format_inline_markdown(stripped),
                    bullet_style,
                )
            )
        # Standard paragraph
        else:
            story.append(Paragraph(format_inline_markdown(line), body_style))

    # Build the document with running numbered canvas
    doc.build(story, canvasmaker=NumberedCanvas)

    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
