"""
Módulo de Gestión de Ciclo de Vida de Eventos (EventManager)
============================================================

Responsabilidad:
----------------
Coordinar la detección local, el control de cooldown, la apertura y cierre de ventanas
de eventos y la instanciación de objetos `EventModel`.

Flujo de invocación:
--------------------
1. El bucle de visión entrega los `EventCandidate` de mayor evidencia.
2. `select_candidate()` filtra estados, cooldown, duplicados y evento activo.
3. `create_event(candidate, detection_summary)` conserva evidencia local y metadata YOLO.
4. Notifica a `app.state.system_state.set_active_event(True)`.
5. Tras analizar y decidir, llama a `complete_event(event)` y lo persiste.
"""

import logging
import threading
from collections import deque
from datetime import datetime
from typing import Optional, Sequence
from app.models.event import EventModel, LocalDetectionSummary
from app.models.reasoning import EventCandidate, EventCandidateState
from app.events.cooldown import CooldownManager
from app.vision.frame_buffer import FrameBuffer

logger = logging.getLogger(__name__)


class EventManager:
    """
    Orquestador de eventos en el nodo local de vigilancia.
    """

    def __init__(
        self,
        cooldown_seconds: int = 10,
        camera_id: str = "CAM_001",
        handled_candidate_limit: int = 1000,
        minimum_context_seconds: float = 0.0,
    ):
        """
        Args:
            cooldown_seconds (int): Segundos de espera entre eventos consecutivos.
            camera_id (str): Identificador asignado a la cámara.
        """
        if handled_candidate_limit < 1:
            raise ValueError("handled_candidate_limit debe ser al menos 1.")
        if minimum_context_seconds < 0:
            raise ValueError("minimum_context_seconds no puede ser negativo.")
        self.camera_id = camera_id
        self.cooldown_manager = CooldownManager(cooldown_seconds)
        self._active_event: Optional[EventModel] = None
        self._lock = threading.RLock()
        self._handled_candidate_ids: set[str] = set()
        self._handled_order: deque[str] = deque(maxlen=handled_candidate_limit)
        self.minimum_context_seconds = float(minimum_context_seconds)

    @property
    def active_event(self) -> Optional[EventModel]:
        with self._lock:
            return self._active_event

    def should_trigger_event(self, candidate: EventCandidate) -> bool:
        """
        Evalúa una hipótesis local; la mera presencia de personas ya no dispara eventos.

        Returns:
            bool: True para candidatos inciertos/confirmados aún no procesados.
        """
        if not isinstance(candidate, EventCandidate):
            return False
        with self._lock:
            return (
                self._active_event is None
                and candidate.id not in self._handled_candidate_ids
                and candidate.state
                in (EventCandidateState.UNCERTAIN, EventCandidateState.CONFIRMED)
                and (candidate.updated_at - candidate.started_at).total_seconds()
                >= self.minimum_context_seconds
                and not self.cooldown_manager.is_in_cooldown()
            )

    def select_candidate(
        self,
        candidates: Sequence[EventCandidate],
    ) -> EventCandidate | None:
        """Selecciona primero confirmados y luego el mayor score elegible."""
        eligible = [candidate for candidate in candidates if self.should_trigger_event(candidate)]
        if not eligible:
            return None
        return max(
            eligible,
            key=lambda candidate: (
                candidate.state is EventCandidateState.CONFIRMED,
                candidate.score,
                candidate.updated_at,
            ),
        )

    def create_event(
        self,
        candidate: EventCandidate,
        detection: LocalDetectionSummary | None = None,
    ) -> EventModel:
        """
        Convierte un EventCandidate en EventModel conservando su evidencia auditable.
        """
        now = datetime.now()
        with self._lock:
            if not self.should_trigger_event(candidate):
                raise ValueError("El candidato no es elegible o ya fue procesado.")
            self.cooldown_manager.update_last_event_time(now)
            self._remember_handled(candidate.id)
            evidence = candidate.evidence
            event = EventModel(
                id=candidate.id,
                candidate_id=candidate.id,
                camera_id=candidate.camera_id or self.camera_id,
                started_at=candidate.started_at,
                status="created",
                local_detection=detection or LocalDetectionSummary(),
                person_track_id=candidate.person_track_id,
                object_track_id=candidate.object_track_id,
                object_class=candidate.object_class,
                local_event_score=candidate.score,
                local_event_state=candidate.state.value,
                release_detected=evidence.release_detected,
                release_timestamp=evidence.timestamps.get("released_at"),
                release_zone=evidence.release_zone,
                object_stationary=evidence.object_stationary,
                person_moving_away=evidence.person_moving_away,
                event_trace={
                    "association_peak": evidence.association_peak,
                    "carried_duration": evidence.carried_duration,
                    "release_detected": evidence.release_detected,
                    "release_zone": evidence.release_zone,
                    "stationary_duration": evidence.stationary_duration,
                    "person_moving_away": evidence.person_moving_away,
                    "person_distance": evidence.person_distance,
                    "local_score": candidate.score,
                    "timestamps": {
                        name: timestamp.isoformat()
                        for name, timestamp in evidence.timestamps.items()
                    },
                },
            )
            self._active_event = event
        logger.info(
            "Evento iniciado desde candidato %s (%s, score %.2f)",
            candidate.id,
            candidate.state.value,
            candidate.score,
        )
        return event

    def _remember_handled(self, candidate_id: str) -> None:
        if len(self._handled_order) == self._handled_order.maxlen:
            oldest = self._handled_order.popleft()
            self._handled_candidate_ids.discard(oldest)
        self._handled_order.append(candidate_id)
        self._handled_candidate_ids.add(candidate_id)

    def release_event(self, event: EventModel) -> None:
        """Libera el evento activo si el procesamiento terminó con un error."""
        with self._lock:
            if self._active_event is not None and self._active_event.id == event.id:
                self._active_event = None

    def complete_event(self, event: EventModel) -> EventModel:
        """
        Finaliza el ciclo de vida del evento, asigna su marca de tiempo final y limpia el estado activo.
        """
        with self._lock:
            event.ended_at = datetime.now()
            event.status = "completed"
            self._active_event = None
        logger.info(f"Evento completado: {event.id}")
        return event

    def reset(self) -> None:
        """Limpia estado efímero al reiniciar el worker."""
        with self._lock:
            self._active_event = None
            self.cooldown_manager.last_event_time = None
            self._handled_candidate_ids.clear()
            self._handled_order.clear()
