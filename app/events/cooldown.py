from datetime import datetime, timedelta
from typing import Optional

class CooldownManager:
    """
    Filtro temporal para evitar generar múltiples eventos duplicados o realizar
    llamadas excesivas a la API multimodal cuando una persona permanece continuadamente en cámara.
    """

    def __init__(self, cooldown_seconds: int = 10):
        self.cooldown_seconds = cooldown_seconds
        self.last_event_time: Optional[datetime] = None

    def is_in_cooldown(self, current_time: Optional[datetime] = None) -> bool:
        if self.last_event_time is None:
            return False
        if current_time is None:
            current_time = datetime.now()
        
        elapsed = (current_time - self.last_event_time).total_seconds()
        return elapsed < self.cooldown_seconds

    def update_last_event_time(self, event_time: Optional[datetime] = None) -> None:
        if event_time is None:
            event_time = datetime.now()
        self.last_event_time = event_time
