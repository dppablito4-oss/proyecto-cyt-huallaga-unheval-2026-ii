"""
Módulo de Gestión de Ciclo de Vida de Eventos (EventManager)
============================================================

Responsabilidad:
----------------
Coordinar la detección local, el control de cooldown, la apertura y cierre de ventanas
de eventos y la instanciación de objetos `EventModel`.

Flujo de invocación:
--------------------
1. El bucle de visión consulta `should_trigger_event(detection_summary)`.
2. Si es afirmativo, llama a `create_event(detection_summary)`.
3. Notifica a `app.state.system_state.set_active_event(True)`.
4. Tras recolectar los fotogramas y ejecutar la inferencia de IA, llama a `complete_event(event)`.
5. El evento finalizado se guarda en el repositorio `app.storage.local_repository.SQLiteEventsRepository`.
"""

import uuid
import logging
from datetime import datetime
from typing import Optional, List, Tuple, Any
from app.models.event import EventModel, LocalDetectionSummary
from app.events.cooldown import CooldownManager
from app.vision.frame_buffer import FrameBuffer

logger = logging.getLogger(__name__)


class EventManager:
    """
    Orquestador de eventos en el nodo local de vigilancia.
    """

    def __init__(self, cooldown_seconds: int = 10, camera_id: str = "CAM_001"):
        """
        Args:
            cooldown_seconds (int): Segundos de espera entre eventos consecutivos.
            camera_id (str): Identificador asignado a la cámara.
        """
        self.camera_id = camera_id
        self.cooldown_manager = CooldownManager(cooldown_seconds)
        self.active_event: Optional[EventModel] = None

    def should_trigger_event(self, detection: LocalDetectionSummary) -> bool:
        """
        Evalúa si la detección actual de YOLO justifica iniciar la captura de un nuevo evento.

        Returns:
            bool: True si hay al menos una persona y el sistema no está en cooldown.
        """
        if detection.persons > 0:
            if not self.cooldown_manager.is_in_cooldown():
                return True
        return False

    def create_event(self, detection: LocalDetectionSummary) -> EventModel:
        """
        Instancia un nuevo objeto `EventModel` con UUID v4 único y registra el inicio del evento.
        """
        event_id = str(uuid.uuid4())
        now = datetime.now()
        self.cooldown_manager.update_last_event_time(now)
        
        event = EventModel(
            id=event_id,
            camera_id=self.camera_id,
            started_at=now,
            status="created",
            local_detection=detection
        )
        self.active_event = event
        logger.info(f"Evento iniciado: {event_id} (Personas detectadas: {detection.persons})")
        return event

    def complete_event(self, event: EventModel) -> EventModel:
        """
        Finaliza el ciclo de vida del evento, asigna su marca de tiempo final y limpia el estado activo.
        """
        event.ended_at = datetime.now()
        event.status = "completed"
        self.active_event = None
        logger.info(f"Evento completado: {event.id}")
        return event
