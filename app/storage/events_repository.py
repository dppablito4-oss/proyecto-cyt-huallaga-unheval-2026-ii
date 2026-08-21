"""
Módulo de Interfaz de Repositorio de Eventos (EventsRepository Interface)
========================================================================

Responsabilidad:
----------------
Definir el patrón Repositorio para el almacenamiento persistente de eventos de vigilancia ambiental.
Garantiza el desacoplamiento entre las reglas del dominio y el motor de base de datos específico.

Flujo de invocación:
--------------------
- Implementado por `app.storage.local_repository.SQLiteEventsRepository` (Fase 0/1 local).
- Podrá implementarse mediante `SupabaseEventsRepository` o PostgreSQL en fases en la nube
  sin modificar los controladores de la API ni el `EventManager`.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from app.models.event import EventModel


class EventsRepository(ABC):
    """
    Contrato abstracto para operaciones CRUD sobre la colección de eventos.
    """

    @abstractmethod
    def save(self, event: EventModel) -> bool:
        """Guarda o actualiza un evento en el repositorio."""
        pass

    @abstractmethod
    def get_by_id(self, event_id: str) -> Optional[EventModel]:
        """Recupera un evento individual por su UUID."""
        pass

    @abstractmethod
    def list_recent(self, limit: int = 20) -> List[EventModel]:
        """Devuelve los $N$ eventos más recientes ordenados por fecha descendente."""
        pass
