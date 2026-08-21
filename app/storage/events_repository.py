from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.event import EventModel

class EventsRepository(ABC):
    """
    Interfaz de repositorio para la persistencia de eventos.
    Abstrae el motor de almacenamiento (SQLite local / Supabase cloud).
    """

    @abstractmethod
    def save(self, event: EventModel) -> bool:
        pass

    @abstractmethod
    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        pass

    @abstractmethod
    def list_recent(self, limit: int = 20) -> List[EventModel]:
        pass
