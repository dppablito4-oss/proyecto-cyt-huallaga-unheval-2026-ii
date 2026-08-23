"""
Módulo de Gestión de Cooldown Temporal (CooldownManager)
========================================================

Responsabilidad:
----------------
Evitar la saturación del sistema y costos innecesarios de API impidiendo que se disparen
múltiples análisis continuos mientras una persona permanece en el campo de visión.

Flujo de invocación:
--------------------
- Invocado por `app.events.manager.EventManager.should_trigger_event()` antes de iniciar un evento.
- Si el tiempo transcurrido desde el último evento es menor a `settings.EVENT_COOLDOWN_SECONDS` (ej. 10 s),
  la solicitud de análisis se bloquea temporalmente.
"""

from datetime import datetime, timedelta
from typing import Optional


class CooldownManager:
    """
    Controlador de ventana de enfriamiento (Cooldown) temporal entre eventos consecutivos.
    """

    def __init__(self, cooldown_seconds: int = 10):
        """
        Args:
            cooldown_seconds (int): Segundos mínimos que deben transcurrir entre eventos sucesivos.
        """
        self.cooldown_seconds = cooldown_seconds
        self.last_event_time: Optional[datetime] = None

    def is_in_cooldown(self, current_time: Optional[datetime] = None) -> bool:
        """
        Determina si el sistema se encuentra en periodo de enfriamiento.

        Returns:
            bool: True si aún no ha expirado el tiempo de espera, False si está listo para un nuevo evento.
        """
        if self.last_event_time is None:
            return False
        if current_time is None:
            current_time = datetime.now()
        
        elapsed = (current_time - self.last_event_time).total_seconds()
        return elapsed < self.cooldown_seconds

    def remaining_seconds(self, current_time: Optional[datetime] = None) -> float:
        """
        Calcula los segundos restantes del periodo de enfriamiento activo.
        """
        if self.last_event_time is None:
            return 0.0
        if current_time is None:
            current_time = datetime.now()
        elapsed = (current_time - self.last_event_time).total_seconds()
        remaining = self.cooldown_seconds - elapsed
        return max(0.0, round(remaining, 1))

    def update_last_event_time(self, event_time: Optional[datetime] = None) -> None:
        """
        Actualiza la marca temporal del último evento procesado.
        """
        if event_time is None:
            event_time = datetime.now()
        self.last_event_time = event_time
