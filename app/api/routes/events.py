"""
Módulo de Rutas de Consulta de Eventos (Events REST Routes)
==========================================================

Responsabilidad:
----------------
Permitir la consulta, filtrado y detalle de los eventos de vigilancia ambiental
guardados en la base de datos persistente.

Endpoints:
----------
- `GET /api/events`: Devuelve una lista con los eventos recientes ordenados por fecha descendente.
- `GET /api/events/{event_id}`: Devuelve el objeto `EventModel` completo asociado a un UUID específico.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import List
from app.config import settings
from app.models.event import EventModel
from app.storage.local_repository import SQLiteEventsRepository

router = APIRouter(prefix="/events")
repo = SQLiteEventsRepository()


@router.get("", response_model=List[EventModel], summary="Listar eventos recientes")
def list_events(limit: int = 20):
    """
    Retorna la lista de los últimos $limit$ eventos registrados en el repositorio local.
    """
    return repo.list_recent(limit=limit)


@router.get("/statistics", summary="Calcular eficacia observada del nudge")
def event_statistics():
    events = repo.list_recent(limit=5000)
    warned = [event for event in events if event.decision == "WARN"]
    observed = [event for event in warned if event.desistimiento_confirmado is not None]
    successful = sum(event.desistimiento_confirmado is True for event in observed)
    return {
        "total_events": len(events),
        "warn_events": len(warned),
        "observed_warn_events": len(observed),
        "desistimientos_confirmados": successful,
        "desistimiento_rate": round(successful / len(observed), 4) if observed else None,
    }


def _safe_event_file(raw_path: str, allowed_root: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = settings.BASE_DIR / path
    resolved = path.resolve()
    try:
        resolved.relative_to(allowed_root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Evidencia no disponible.") from exc
    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="Evidencia no disponible.")
    return resolved


@router.get("/{event_id}/frames/{frame_index}", summary="Ver fotograma histórico")
def get_event_frame(event_id: str, frame_index: int):
    event = repo.get_by_id(event_id)
    if not event or frame_index < 0 or frame_index >= len(event.capture.frame_paths):
        raise HTTPException(status_code=404, detail="Fotograma no encontrado.")
    path = _safe_event_file(event.capture.frame_paths[frame_index], settings.DATA_DIR / "frames")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{event_id}/audio", summary="Escuchar advertencia histórica")
def get_event_audio(event_id: str):
    event = repo.get_by_id(event_id)
    audio_path = event.metrics.get("audio_path") if event else None
    if not audio_path:
        raise HTTPException(status_code=404, detail="Audio no disponible.")
    path = _safe_event_file(str(audio_path), settings.DATA_DIR / "audio")
    media_type = "audio/wav" if path.suffix.casefold() == ".wav" else "audio/mpeg"
    return FileResponse(path, media_type=media_type)


@router.get("/{event_id}", response_model=EventModel, summary="Consultar detalle de un evento")
def get_event_detail(event_id: str):
    """
    Recupera el registro estructurado completo de un evento por su identificador UUID.
    Lanza error HTTP 404 si el evento no existe.
    """
    event = repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail=f"Evento con ID '{event_id}' no encontrado.")
    return event
