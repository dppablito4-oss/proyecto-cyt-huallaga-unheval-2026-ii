"""Endpoints para exportar evidencia experimental de SIVARH."""

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.config import settings
from app.reports import build_evidence_pdf
from app.state import system_state

router = APIRouter(prefix="/reports")


@router.get("/evidence.pdf", summary="Exportar fotogramas y logs como PDF")
def export_evidence_pdf():
    """Genera un reporte PDF con el estado, la secuencia visible y los logs actuales."""
    system_state.add_log("INFO", "Exportando reporte PDF de evidencia.")
    snapshot = system_state.to_dict()
    image_paths = []
    allowed_prefixes = ("ai-preview-", "manual-preview-")
    for url in snapshot.get("analysis_preview_urls", []):
        filename = Path(url.split("?", 1)[0]).name
        candidate = settings.DATA_DIR / "frames" / filename
        if filename.startswith(allowed_prefixes) and candidate.is_file():
            image_paths.append(candidate)

    generated_at = datetime.now()
    output_dir = settings.BASE_DIR / "output" / "pdf"
    output_path = output_dir / f"SIVARH_reporte_evidencia_{generated_at:%Y%m%d_%H%M%S}.pdf"
    build_evidence_pdf(output_path, snapshot, image_paths, generated_at)

    return FileResponse(
        output_path,
        media_type="application/pdf",
        filename=output_path.name,
    )
