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


def _build_header(styles: Any) -> list:
    base_dir = Path(__file__).resolve().parent.parent.parent
    sivarh_logo = base_dir / "assets" / "imagotipo_sivarh.png"
    if not sivarh_logo.is_file():
        sivarh_logo = base_dir / "assets" / "logotipo_sivarh.png"
    unheval_logo = base_dir / "assets" / "logo_unheval.png"

    left_cell = ""
    if sivarh_logo.is_file():
        try:
            left_cell = _scaled_image(sivarh_logo, 45 * mm, 20 * mm)
        except Exception:
            left_cell = ""

    right_cell = ""
    if unheval_logo.is_file():
        try:
            right_cell = _scaled_image(unheval_logo, 35 * mm, 20 * mm)
        except Exception:
            right_cell = ""

    title_p = Paragraph("SIVARH", styles["SivarhTitle"])
    subtitle_p = Paragraph(
        "Sistema Inteligente de Vigilancia Ambiental para las Riberas del Río Huallaga - Sector Puente Huallaga, UNHEVAL",
        styles["SivarhSubtitle"],
    )
    center_cell = [title_p, subtitle_p]

    header_table = Table([[left_cell, center_cell, right_cell]], colWidths=[45 * mm, 90 * mm, 35 * mm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (0, 0), "LEFT"),
        ("ALIGN", (1, 0), (1, 0), "CENTER"),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [header_table, Spacer(1, 4 * mm)]


def build_evidence_pdf(
    output_path: Path,
    state: dict[str, Any],
    image_paths: Iterable[Path],
    generated_at: datetime | None = None,
) -> Path:
    """Crea un PDF con resumen operativo, fotogramas y logs de la sesión en vivo."""
    generated_at = generated_at or datetime.now()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images = [Path(path) for path in image_paths if Path(path).is_file()]

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SivarhTitle", parent=styles["Title"], fontName=FONT_BOLD, fontSize=20, leading=24, textColor=DARK, alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle(name="SivarhSubtitle", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=8.5, leading=12, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="SivarhHeading", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=12, leading=15, textColor=GREEN, spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="SivarhBody", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=DARK))
    styles.add(ParagraphStyle(name="SivarhSmall", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=7.5, leading=10, textColor=DARK))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title="SIVARH - Reporte de evidencia",
        author="SIVARH - UNHEVAL",
    )
    story = []
    story.extend(_build_header(styles))
    story.append(Paragraph("Reporte de evidencia experimental en vivo", styles["SivarhHeading"]))

    confidence = state.get("last_analysis_confidence")
    confidence_text = f"{float(confidence) * 100:.1f}%" if confidence is not None else "No registrada"
    summary = [
        ["Fecha de exportación", generated_at.strftime("%d/%m/%Y %H:%M:%S")],
        ["Modelo de IA", _text(state.get("ai_model"))],
        ["Decisión", _text(state.get("last_decision"), "Pendiente")],
        ["Confianza IA", confidence_text],
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
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([summary_table, Spacer(1, 5 * mm)])

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
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
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
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(log_table)
    else:
        story.append(Paragraph("No había registros disponibles al momento de exportar.", styles["SivarhBody"]))

    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return output_path


def build_event_pdf(
    output_path: Path,
    event: Any,
    generated_at: datetime | None = None,
) -> Path:
    """Crea un PDF detallado de una incidencia histórica registrada en la base de datos."""
    generated_at = generated_at or datetime.now()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_dir = Path(__file__).resolve().parent.parent.parent
    raw_paths = getattr(getattr(event, "capture", None), "frame_paths", []) or []
    images = []
    for raw_p in raw_paths:
        p = Path(raw_p)
        if not p.is_absolute():
            p = base_dir / p
        if p.is_file():
            images.append(p)

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SivarhTitle", parent=styles["Title"], fontName=FONT_BOLD, fontSize=20, leading=24, textColor=DARK, alignment=TA_CENTER, spaceAfter=4))
    styles.add(ParagraphStyle(name="SivarhSubtitle", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=8.5, leading=12, textColor=MUTED, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="SivarhHeading", parent=styles["Heading2"], fontName=FONT_BOLD, fontSize=12, leading=15, textColor=GREEN, spaceBefore=8, spaceAfter=6))
    styles.add(ParagraphStyle(name="SivarhBody", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=9, leading=13, textColor=DARK))
    styles.add(ParagraphStyle(name="SivarhSmall", parent=styles["BodyText"], fontName=FONT_REGULAR, fontSize=7.5, leading=10, textColor=DARK))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
        title=f"SIVARH - Incidencia {event.id[:8]}",
        author="SIVARH - UNHEVAL",
    )
    story = []
    story.extend(_build_header(styles))
    story.append(Paragraph(f"Reporte de Incidencia Histórica - ID: {escape(event.id[:13])}…", styles["SivarhHeading"]))

    started_str = event.started_at.strftime("%d/%m/%Y %H:%M:%S") if getattr(event, "started_at", None) else "No registrada"
    ai_confidence = getattr(event, "openai_confidence", None)
    ai_conf_str = f"{float(ai_confidence) * 100:.1f}%" if ai_confidence is not None else "N/A"
    
    local_score = getattr(event, "local_event_score", None)
    local_score_str = f"{float(local_score) * 100:.1f}%" if local_score is not None else "N/A"

    nudge_status = "No evaluado"
    if getattr(event, "desistimiento_confirmado", None) is True:
        nudge_status = "Desistimiento confirmado (Residuo recogido)"
    elif getattr(event, "desistimiento_confirmado", None) is False:
        nudge_status = "No recogió el residuo"
    elif getattr(event, "decision", None) == "WARN":
        nudge_status = "Alerta acústica emitida (Sin observación posterior)"

    metrics = getattr(event, "metrics", {}) or {}
    ai_model = metrics.get("ai_model") or "OpenAI Vision"
    ai_lat = metrics.get("ai_latency_ms")
    ai_lat_str = f"{float(ai_lat)/1000.0:.2f} s" if ai_lat is not None else "N/A"

    summary = [
        ["ID del Evento", _text(event.id)],
        ["Cámara / Origen", _text(getattr(event, "camera_id", "CAM_001"))],
        ["Fecha y Hora", started_str],
        ["Decisión Ejecutada", _text(getattr(event, "decision", None), "PENDIENTE")],
        ["Residuo / Objeto", _text(getattr(event, "object_class", None), "No identificado")],
        ["Confianza Local (YOLO)", local_score_str],
        ["Confianza IA Multimodal", ai_conf_str],
        ["Modelo de IA", _text(ai_model)],
        ["Latencia de IA", ai_lat_str],
        ["Resultado Nudge Acústico", nudge_status],
        ["Fotogramas Adjuntos", str(len(images))],
    ]
    summary_table = Table(summary, colWidths=[52 * mm, 114 * mm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("TEXTCOLOR", (0, 0), (0, -1), DARK),
        ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
        ("FONTNAME", (1, 0), (1, -1), FONT_REGULAR),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    story.extend([summary_table, Spacer(1, 5 * mm)])

    analysis = getattr(event, "analysis", {}) or {}
    description = analysis.get("description") or "Sin diagnóstico multimodal detallado."
    warning_msg = analysis.get("warning_message") or "Sin advertencia acústica personalizada."

    story.append(Paragraph("Diagnóstico y Análisis de Vigilancia", styles["SivarhHeading"]))
    story.append(Paragraph(f"<b>Diagnóstico de IA:</b> {escape(str(description))}", styles["SivarhBody"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"<b>Advertencia Emita:</b> {escape(str(warning_msg))}", styles["SivarhBody"]))

    story.append(Paragraph("Secuencia de Fotogramas de Evidencia", styles["SivarhHeading"]))
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
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(image_table)
    else:
        story.append(Paragraph("No hay fotogramas guardados disponibles para esta incidencia.", styles["SivarhBody"]))

    # Sección de logs del evento
    logs = metrics.get("logs") or (getattr(event, "event_trace", {}) or {}).get("logs") or []
    story.extend([PageBreak(), Paragraph("Registros Cronológicos del Evento", styles["SivarhHeading"])])
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
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(log_table)
    else:
        story.append(Paragraph("<i>No se registraron logs de sistema específicos para este evento histórico en la base de datos. Los metadatos y fotogramas anteriores constituyen la evidencia guardada.</i>", styles["SivarhBody"]))

    doc.build(story, onFirstPage=_page_decor, onLaterPages=_page_decor)
    return output_path

