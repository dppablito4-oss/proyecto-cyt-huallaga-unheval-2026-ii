"""Construcción del reporte PDF de evidencia de una sesión de SIVARH."""

from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Iterable

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


GREEN = colors.HexColor("#167A58")
DARK = colors.HexColor("#163028")
MUTED = colors.HexColor("#5E7069")
LIGHT = colors.HexColor("#EAF4EF")
LINE = colors.HexColor("#C9D9D2")


def _register_fonts() -> tuple[str, str]:
    candidates = [
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")),
    ]
    for regular_path, bold_path in candidates:
        if regular_path.is_file() and bold_path.is_file():
            pdfmetrics.registerFont(TTFont("SivarhRegular", str(regular_path)))
            pdfmetrics.registerFont(TTFont("SivarhBold", str(bold_path)))
            return "SivarhRegular", "SivarhBold"
    return "Helvetica", "Helvetica-Bold"


FONT_REGULAR, FONT_BOLD = _register_fonts()


def _text(value: Any, fallback: str = "No registrado") -> str:
    if value is None or value == "":
        return fallback
    return escape(str(value))


def _page_decor(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "SIVARH - Reporte de evidencia experimental")
    canvas.drawRightString(192 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def _scaled_image(path: Path, max_width: float, max_height: float) -> Image:
    image = Image(str(path))
    ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * ratio
    image.drawHeight = image.imageHeight * ratio
    return image


def build_evidence_pdf(
    output_path: Path,
    state: dict[str, Any],
    image_paths: Iterable[Path],
    generated_at: datetime | None = None,
) -> Path:
    """Crea un PDF con resumen operativo, fotogramas y logs de la sesión."""
    generated_at = generated_at or datetime.now()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = [Path(path) for path in image_paths if Path(path).is_file()]

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SivarhTitle", parent=styles["Title"], fontName=FONT_BOLD, fontSize=22, leading=26, textColor=DARK, alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name="SivarhSubtitle", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=MUTED, alignment=TA_CENTER, spaceAfter=14))
    styles.add(ParagraphStyle(name="SivarhHeading", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=13, leading=16, textColor=GREEN, spaceBefore=10, spaceAfter=7))
    styles.add(ParagraphStyle(name="SivarhBody", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=DARK))
    styles.add(ParagraphStyle(name="SivarhSmall", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=7.5, leading=10, textColor=DARK))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title="SIVARH - Reporte de evidencia",
        author="SIVARH - UNHEVAL",
    )
    story = [
        Paragraph("SIVARH", styles["SivarhTitle"]),
        Paragraph(
            "Sistema Inteligente de Vigilancia Ambiental para las Riberas del Río Huallaga - sector Puente Huallaga, UNHEVAL",
            styles["SivarhSubtitle"],
        ),
        Paragraph("Reporte de evidencia experimental", styles["SivarhHeading"]),
    ]

    confidence = state.get("last_analysis_confidence")
    confidence_text = f"{float(confidence) * 100:.1f}%" if confidence is not None else "No registrada"
    summary = [
        ["Fecha de exportación", generated_at.strftime("%d/%m/%Y %H:%M:%S")],
        ["Modelo de IA", _text(state.get("ai_model"))],
        ["Decisión", _text(state.get("last_decision"), "Pendiente")],
        ["Confianza", confidence_text],
        ["Latencia de IA", f"{float(state['ai_latency']):.2f} s" if state.get("ai_latency") is not None else "No registrada"],
        ["Fotogramas incluidos", str(len(images))],
    ]
    summary_table = Table(summary, colWidths=[48 * mm, 118 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([summary_table, Spacer(1, 6 * mm)])

    story.append(Paragraph("Resultado del análisis", styles["SivarhHeading"]))
    story.append(Paragraph(f"<b>Diagnóstico:</b> {_text(state.get('last_diagnosis'))}", styles["SivarhBody"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"<b>Advertencia emitida:</b> {_text(state.get('last_warning_message'))}", styles["SivarhBody"]))

    story.append(Paragraph("Secuencia de fotogramas", styles["SivarhHeading"]))
    if images:
        cells = []
        for index, path in enumerate(images, start=1):
            cells.append([_scaled_image(path, 78 * mm, 48 * mm), Paragraph(f"Fotograma {index}", styles["SivarhSmall"])])
        rows = [cells[index:index + 2] for index in range(0, len(cells), 2)]
        if len(rows[-1]) == 1:
            rows[-1].append("")
        image_table = Table(rows, colWidths=[84 * mm, 84 * mm], hAlign="LEFT")
        image_table.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.5, LINE),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(image_table)
    else:
        story.append(Paragraph("No había fotogramas disponibles al momento de exportar.", styles["SivarhBody"]))

    story.extend([PageBreak(), Paragraph("Registro cronológico de la sesión", styles["SivarhHeading"])])
    logs = state.get("logs") or []
    if logs:
        log_rows = [["Hora", "Tipo", "Mensaje"]]
        for log in logs:
            log_rows.append([
                Paragraph(_text(log.get("time"), "--:--:--"), styles["SivarhSmall"]),
                Paragraph(_text(log.get("level"), "INFO"), styles["SivarhSmall"]),
                Paragraph(_text(log.get("message"), ""), styles["SivarhSmall"]),
            ])
        log_table = Table(log_rows, colWidths=[20 * mm, 24 * mm, 124 * mm], repeatRows=1)
        log_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
            ("GRID", (0, 0), (-1, -1), 0.4, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(log_table)
    else:
        story.append(Paragraph("No había registros disponibles al momento de exportar.", styles["SivarhBody"]))

    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return output_path
