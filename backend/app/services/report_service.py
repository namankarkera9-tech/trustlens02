"""JSON and printable PDF report rendering."""

from io import BytesIO
from typing import Any, Dict
from xml.sax.saxutils import escape

from fastapi import HTTPException


def render_pdf(result: Dict[str, Any]) -> bytes:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="PDF export is unavailable. Install reportlab in the backend environment.") from exc

    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch, topMargin=0.62 * inch, bottomMargin=0.62 * inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TrustlensBody", parent=styles["BodyText"], fontSize=9, leading=13, textColor=colors.HexColor("#53645f"), alignment=TA_LEFT, spaceAfter=7))
    styles.add(ParagraphStyle(name="TrustlensSmall", parent=styles["BodyText"], fontSize=7.5, leading=10, textColor=colors.HexColor("#788680"), spaceAfter=4))
    story = [Paragraph("TRUSTLENS / ANALYSIS REPORT", styles["Heading2"]), Spacer(1, 5)]
    story.append(Paragraph("Evidence for human review — not a definitive authenticity determination.", styles["TrustlensBody"]))
    state = result.get("trust_state") or "INSUFFICIENT / CONFLICTING"
    rows = [
        ["TRUSTLENS STATE", "FILE", "MEDIA TYPE"],
        [state, result.get("filename", "Unknown"), result.get("content_type", "Unknown")],
        ["ANALYSIS ID", result.get("id", ""), ""],
    ]
    table = Table(rows, colWidths=[2.15 * inch, 2.65 * inch, 1.55 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#edf5f0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#537369")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dce7e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([table, Spacer(1, 13), Paragraph("Explanation", styles["Heading3"]), Paragraph(str(result.get("explanation", "")), styles["TrustlensBody"])])

    story.append(Paragraph("Evidence", styles["Heading3"]))
    for item in result.get("evidence", []):
        source = str(item.get("source", "unknown")).upper()
        strength = str(item.get("strength", "informational"))
        timestamp = item.get("timestamp")
        when = " @ {:.2f}s".format(timestamp) if isinstance(timestamp, (int, float)) else ""
        story.append(Paragraph("<b>{}</b> · {} · {}{}<br/>{}".format(escape(source), escape(str(item.get("category", ""))), escape(strength), when, escape(str(item.get("observation", "")))), styles["TrustlensSmall"]))

    for title, key in (("Conflicts", "conflicts"), ("Limitations", "limitations")):
        story.append(Paragraph(title, styles["Heading3"]))
        values = result.get(key) or ["None explicitly reported."]
        for value in values:
            story.append(Paragraph("• {}".format(escape(str(value))), styles["TrustlensBody"]))

    metadata = result.get("metadata") or {}
    if metadata:
        story.append(Paragraph("Metadata", styles["Heading3"]))
        for key, value in metadata.items():
            story.append(Paragraph("<b>{}</b>: {}".format(escape(str(key)), escape(str(value))), styles["TrustlensSmall"]))

    provenance = result.get("provenance") or {}
    story.append(Paragraph("Provenance status: {}".format(escape(str(provenance.get("status", "not returned")))), styles["TrustlensSmall"]))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Limitations: missing metadata or C2PA is not proof of manipulation. Gemini observations are not calibrated probabilities. TrustLens is an assistive evidence review; verify important media at its source.", styles["TrustlensSmall"]))
    doc.build(story)
    return output.getvalue()
