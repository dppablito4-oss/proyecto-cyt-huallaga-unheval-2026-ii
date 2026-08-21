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
    Coordinador local de eventos. Detecta cuándo inicia una situación de interés
    (persona presente + cooldown libre), reúne el contexto temporal desde el FrameBuffer
    y gestiona la creación de objetos EventModel.
    """

    def __init__(self, cooldown_seconds: int = 10, camera_id: str = "CAM_001"):
        self.camera_id = camera_id
        self.cooldown_manager = CooldownManager(cooldown_seconds)
        self.active_event: Optional[EventModel] = None

    def should_trigger_event(self, detection: LocalDetectionSummary) -> bool:
        if detection.persons > 0:
            if not self.cooldown_manager.is_in_cooldown():
                return True
        return False

    def create_event(self, detection: LocalDetectionSummary) -> EventModel:
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
        logger.info(f"Nuevo evento creado: {event_id} (Personas detectadas: {detection.persons})")
        return event

    def complete_event(self, event: EventModel) -> EventModel:
        event.ended_at = datetime.now()
        event.status = "completed"
        self.active_event = None
        return event
