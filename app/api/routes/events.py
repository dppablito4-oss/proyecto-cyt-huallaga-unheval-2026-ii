from fastapi import APIRouter, HTTPException
from typing import List
from app.models.event import EventModel
from app.storage.local_repository import SQLiteEventsRepository

router = APIRouter(prefix="/events")
repo = SQLiteEventsRepository()

@router.get("", response_model=List[EventModel])
def list_events(limit: int = 20):
    """Lista los eventos más recientes."""
    return repo.list_recent(limit=limit)

@router.get("/{event_id}", response_model=EventModel)
def get_event_detail(event_id: str):
    """Obtiene el detalle de un evento por ID."""
    event = repo.get_by_id(event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return event
