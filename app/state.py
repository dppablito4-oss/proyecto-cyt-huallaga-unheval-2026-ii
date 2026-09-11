"""
Módulo de Estado Global del Sistema (SystemState)
=================================================

Responsabilidad:
----------------
Mantener la única fuente de verdad (Single Source of Truth) del estado operativo
en memoria en tiempo real. Este estado refleja si la cámara está activa, los FPS,
las personas detectadas por YOLO, los eventos en curso, la última inferencia de IA
y la última advertencia de voz emitida.

Flujo de invocación:
--------------------
1. Los workers de visión y detección actualizan las métricas mediante `set_camera_status()`,
   `set_persons_detected()`, `set_active_event()` y `record_analysis_result()`.
2. El endpoint REST `/api/status` en `app.api.routes.status` lee este estado para clientes HTTP.
3. El canal WebSocket `/ws` en `app.api.websocket` transmite periódicamente este estado en JSON
   al frontend para refrescar el dashboard en tiempo real sin recargar la página.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import deque
import threading
from pydantic import BaseModel, Field

from app.config import settings


class SystemLogEntry(BaseModel):
    """Estructura de un mensaje de log transmitido al frontend."""
    time: str
    level: str
    message: str


class SystemStatusModel(BaseModel):
    """
    Modelo de validación Pydantic que describe la estructura del estado
    entregado a clientes HTTP o WebSockets.
    """
    running: bool = Field(True, description="Indica si el bucle del sistema está activo.")
    camera_connected: bool = Field(False, description="Estado de conexión con el dispositivo de video.")
    camera_source: str = Field("0", description="Identificador o URL de la fuente de cámara.")
    fps: float = Field(0.0, description="Cuadros por segundo de procesamiento en tiempo real.")
    persons_detected: int = Field(0, description="Cantidad de personas detectadas actualmente por YOLO.")
    objects_detected: int = Field(0, description="Cantidad de objetos no personales detectados por YOLO.")
    detection_counts: Dict[str, int] = Field(default_factory=dict, description="Detecciones actuales agrupadas por clase.")
    active_tracks: int = Field(0, description="Cantidad de tracks confirmados visibles en el frame actual.")
    active_track_ids: List[int] = Field(default_factory=list, description="Identificadores temporales anónimos visibles.")
    active_person_tracks: int = Field(0, description="Personas con track confirmado actualmente visibles.")
    active_objects: int = Field(0, description="Objetos no personales actualmente visibles.")
    zone_occupancy: Dict[str, int] = Field(default_factory=dict, description="Tracks presentes por zona ambiental.")
    scene_timestamp: Optional[str] = Field(None, description="Última actualización del estado espacial.")
    vision_debug_overlay: bool = Field(False, description="Indica si el stream muestra el overlay de visión.")
    association_candidates: int = Field(0, description="Relaciones persona-objeto actualmente evaluadas.")
    confirmed_associations: int = Field(0, description="Relaciones que cumplieron score y persistencia mínimos.")
    active_pose_tracks: int = Field(0, description="Personas con una pose reciente disponible.")
    pose_enabled: bool = Field(False, description="Indica si el análisis selectivo de pose fue habilitado.")
    pose_available: bool = Field(False, description="Indica si el runtime de pose fue inicializado correctamente.")
    local_event_candidates: int = Field(0, description="Hipótesis espacio-temporales activas.")
    confirmed_local_events: int = Field(0, description="Hipótesis confirmadas por evidencia local.")
    openai_fallback_enabled: bool = Field(False, description="OpenAI se reserva para casos ambiguos.")
    events_sent_openai: int = Field(0, description="Eventos enviados a verificación externa en la sesión.")
    events_confirmed_local: int = Field(0, description="Eventos resueltos localmente sin OpenAI.")
    local_warning_audio_enabled: bool = Field(False, description="Prioriza advertencias WAV locales.")
    last_audio_source: Optional[str] = Field(None, description="Última fuente de audio utilizada.")
    performance: Dict[str, Any] = Field(default_factory=dict, description="Métricas agregadas del nodo edge.")
    active_event: bool = Field(False, description="Indica si existe una ventana de captura de evento activa.")
    cooldown_remaining: float = Field(0.0, description="Segundos restantes de enfriamiento activo.")
    last_event_time: Optional[str] = Field(None, description="Marca de tiempo ISO del último evento detectado.")
    ai_status: str = Field("idle", description="Estado de la IA: 'idle', 'sending', 'analyzing', 'completed'.")
    ai_latency: Optional[float] = Field(None, description="Tiempo en segundos que tardó la última llamada a la IA.")
    last_analysis_confidence: Optional[float] = Field(None, description="Confianza (0.0 - 1.0) de la última inferencia de IA.")
    last_decision: Optional[str] = Field(None, description="Última decisión del motor: 'IGNORE', 'LOG_ONLY', 'WARN'.")
    last_diagnosis: Optional[str] = Field(None, description="Descripción textual emitida por la IA.")
    last_warning_message: Optional[str] = Field(None, description="Último mensaje de advertencia verbal generado.")
    ai_model: str = Field(default_factory=lambda: settings.OPENAI_VISION_MODEL, description="Nombre del modelo multimodal en uso.")
    frames_per_analysis: int = Field(5, description="Número de fotogramas enviados por análisis.")
    total_events_processed: int = Field(0, description="Contador histórico de eventos analizados en la sesión.")
    analysis_preview_urls: List[str] = Field(default_factory=list, description="Rutas de los fotogramas preparados para la consulta actual o más reciente a la IA.")
    manual_recognition_mode: bool = Field(False, description="Captura y envío controlados desde la interfaz.")
    manual_frames_captured: int = Field(0, description="Fotogramas capturados de la secuencia manual actual.")
    manual_sequence_ready: bool = Field(False, description="La secuencia manual está lista para análisis.")
    alert_pending: bool = Field(False, description="Hay una advertencia de Luna pendiente de emisión manual.")
    logs: List[Dict[str, str]] = Field(default_factory=list, description="Lista de logs recientes del sistema.")


class SystemState:
    """
    Gestor en memoria del estado reactivo del sistema con logs en tiempo real.
    Thread-safe para lecturas y actualizaciones directas desde los diferentes módulos.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._running = True
        self._camera_connected = False
        self._camera_source = settings.CAMERA_SOURCE
        self._fps = 0.0
        self._persons_detected = 0
        self._objects_detected = 0
        self._detection_counts: Dict[str, int] = {}
        self._active_tracks = 0
        self._active_track_ids: List[int] = []
        self._active_person_tracks = 0
        self._active_objects = 0
        self._zone_occupancy: Dict[str, int] = {}
        self._scene_timestamp: Optional[datetime] = None
        self._association_candidates = 0
        self._confirmed_associations = 0
        self._active_pose_tracks = 0
        self._pose_available = False
        self._local_event_candidates = 0
        self._confirmed_local_events = 0
        self._events_sent_openai = 0
        self._events_confirmed_local = 0
        self._last_audio_source: Optional[str] = None
        self._performance: Dict[str, Any] = {}
        self._active_event = False
        self._cooldown_remaining = 0.0
        self._last_event_time: Optional[datetime] = None
        self._ai_status = "idle"
        self._ai_latency: Optional[float] = None
        self._last_analysis_confidence: Optional[float] = None
        self._last_decision: Optional[str] = None
        self._last_diagnosis: Optional[str] = None
        self._last_warning_message: Optional[str] = None
        self._ai_model = settings.OPENAI_VISION_MODEL
        self._frames_per_analysis = settings.FRAMES_PER_ANALYSIS
        self._total_events_processed = 0
        self._analysis_preview_urls: List[str] = []
        self._manual_recognition_mode = settings.MANUAL_RECOGNITION_MODE
        self._manual_frames_captured = 0
        self._manual_sequence_ready = False
        self._alert_pending = False
        self._logs = deque(maxlen=100)

        # Log inicial de arranque
        self.add_log("INFO", f"Sistema {settings.APP_NAME} iniciado en modo {settings.APP_ENV}.")

    def add_log(self, level: str, message: str) -> None:
        """Agrega un mensaje con timestamp al buffer de logs en tiempo real."""
        now_str = datetime.now().strftime("%H:%M:%S")
        with self._lock:
            self._logs.append({
                "time": now_str,
                "level": level,
                "message": message
            })

    def clear_logs(self) -> None:
        """Limpia el buffer de logs."""
        with self._lock:
            self._logs.clear()
            self._logs.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "level": "INFO",
                "message": "Logs limpiados por el usuario."
            })

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el estado actual a un diccionario Python estándar.
        """
        with self._lock:
            return {
                "running": self._running,
                "camera_connected": self._camera_connected,
                "camera_source": self._camera_source,
                "fps": self._fps,
                "persons_detected": self._persons_detected,
                "objects_detected": self._objects_detected,
                "detection_counts": dict(self._detection_counts),
                "active_tracks": self._active_tracks,
                "active_track_ids": list(self._active_track_ids),
                "active_person_tracks": self._active_person_tracks,
                "active_objects": self._active_objects,
                "zone_occupancy": dict(self._zone_occupancy),
                "scene_timestamp": self._scene_timestamp.isoformat() if self._scene_timestamp else None,
                "vision_debug_overlay": settings.VISION_DEBUG_OVERLAY,
                "association_candidates": self._association_candidates,
                "confirmed_associations": self._confirmed_associations,
                "active_pose_tracks": self._active_pose_tracks,
                "pose_enabled": settings.POSE_ENABLED,
                "pose_available": self._pose_available,
                "local_event_candidates": self._local_event_candidates,
                "confirmed_local_events": self._confirmed_local_events,
                "openai_fallback_enabled": settings.OPENAI_FALLBACK_ENABLED,
                "events_sent_openai": self._events_sent_openai,
                "events_confirmed_local": self._events_confirmed_local,
                "local_warning_audio_enabled": settings.USE_LOCAL_WARNING_AUDIO,
                "last_audio_source": self._last_audio_source,
                "performance": dict(self._performance),
                "active_event": self._active_event,
                "cooldown_remaining": self._cooldown_remaining,
                "last_event_time": self._last_event_time.isoformat() if self._last_event_time else None,
                "ai_status": self._ai_status,
                "ai_latency": self._ai_latency,
                "last_analysis_confidence": self._last_analysis_confidence,
                "last_decision": self._last_decision,
                "last_diagnosis": self._last_diagnosis,
                "last_warning_message": self._last_warning_message,
                "ai_model": self._ai_model,
                "frames_per_analysis": self._frames_per_analysis,
                "total_events_processed": self._total_events_processed,
                "analysis_preview_urls": list(self._analysis_preview_urls),
                "manual_recognition_mode": self._manual_recognition_mode,
                "manual_frames_captured": self._manual_frames_captured,
                "manual_sequence_ready": self._manual_sequence_ready,
                "alert_pending": self._alert_pending,
                "logs": list(self._logs)
            }

    def set_camera_status(self, connected: bool, source: str = "0", fps: float = 0.0) -> None:
        """Actualiza el estado de la cámara y los FPS medidos."""
        with self._lock:
            self._camera_connected = connected
            self._camera_source = source
            self._fps = fps

    def set_persons_detected(self, count: int) -> None:
        """Actualiza la cantidad de personas observadas en el último frame."""
        with self._lock:
            self._persons_detected = count

    def set_detection_status(
        self,
        persons: int,
        objects: int,
        counts_by_label: Dict[str, int],
    ) -> None:
        """Publica el resultado multiclase sin retirar el contador heredado."""
        with self._lock:
            self._persons_detected = persons
            self._objects_detected = objects
            self._detection_counts = dict(counts_by_label)

    def set_tracking_status(self, active_tracks: int, track_ids: List[int]) -> None:
        """Publica un resumen compatible del tracking sin exponer datos biométricos."""
        with self._lock:
            self._active_tracks = active_tracks
            self._active_track_ids = list(track_ids)

    def set_scene_status(
        self,
        active_persons: int,
        active_objects: int,
        track_ids: List[int],
        zone_occupancy: Dict[str, int],
        timestamp: datetime,
        association_candidates: int = 0,
        confirmed_associations: int = 0,
        active_pose_tracks: int = 0,
        pose_available: bool = False,
        local_event_candidates: int = 0,
        confirmed_local_events: int = 0,
    ) -> None:
        """Publica el resumen espacial derivado de SceneState."""
        with self._lock:
            self._active_person_tracks = active_persons
            self._active_objects = active_objects
            self._active_tracks = active_persons + active_objects
            self._active_track_ids = list(track_ids)
            self._zone_occupancy = dict(zone_occupancy)
            self._scene_timestamp = timestamp
            self._association_candidates = association_candidates
            self._confirmed_associations = confirmed_associations
            self._active_pose_tracks = active_pose_tracks
            self._pose_available = pose_available
            self._local_event_candidates = local_event_candidates
            self._confirmed_local_events = confirmed_local_events

    def set_cooldown_remaining(self, seconds: float) -> None:
        """Actualiza el tiempo restante de enfriamiento."""
        with self._lock:
            self._cooldown_remaining = seconds

    def set_active_event(self, active: bool) -> None:
        """Marca el inicio o fin de una ventana de captura de evento."""
        with self._lock:
            self._active_event = active
            if active:
                self._last_event_time = datetime.now()

    def set_ai_status(self, status: str, latency: Optional[float] = None) -> None:
        """Actualiza el estado de procesamiento de la IA ('idle', 'sending', 'analyzing', 'completed')."""
        with self._lock:
            self._ai_status = status
            if latency is not None:
                self._ai_latency = latency

    def set_analysis_preview_urls(self, urls: List[str]) -> None:
        """Publica los fotogramas JPEG seleccionados para su vista previa en el dashboard."""
        with self._lock:
            self._analysis_preview_urls = list(urls)

    def set_frames_per_analysis(self, count: int) -> None:
        """Sincroniza la cantidad de fotogramas configurada para cada análisis."""
        with self._lock:
            self._frames_per_analysis = count

    def set_manual_sequence_status(self, captured: int, ready: bool) -> None:
        """Actualiza el avance de la secuencia manual visible en el panel."""
        with self._lock:
            self._manual_frames_captured = captured
            self._manual_sequence_ready = ready

    def record_analysis_result(
        self,
        confidence: Optional[float],
        decision: Optional[str] = None,
        diagnosis: Optional[str] = None,
        warning_message: Optional[str] = None,
        latency: Optional[float] = None,
        openai_used: bool = False,
        local_confirmed: bool = False,
    ) -> None:
        """Registra el resultado entregado por VisionAI y la decisión final."""
        with self._lock:
            self._last_analysis_confidence = confidence
            self._last_decision = decision
            self._last_diagnosis = diagnosis
            self._last_warning_message = warning_message
            self._alert_pending = decision == "WARN" and bool(warning_message)
            if latency is not None:
                self._ai_latency = latency
            self._total_events_processed += 1
            if openai_used:
                self._events_sent_openai += 1
            if local_confirmed:
                self._events_confirmed_local += 1

    def mark_alert_emitted(self) -> None:
        """Marca como atendida la advertencia que estaba pendiente de emisión manual."""
        with self._lock:
            self._alert_pending = False

    def set_audio_source(self, source: Optional[str]) -> None:
        """Publica si la advertencia provino de plantilla, caché, TTS o falló."""
        with self._lock:
            self._last_audio_source = source

    def set_performance(self, performance: Dict[str, Any]) -> None:
        """Publica un snapshot agregado listo para REST y WebSocket."""
        with self._lock:
            self._performance = dict(performance)


# Instancia global accesible en toda la aplicación (Singleton)
system_state = SystemState()
