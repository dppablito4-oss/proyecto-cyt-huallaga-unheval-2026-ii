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

from fastapi import APIRouter, HTTPException
from typing import List
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
