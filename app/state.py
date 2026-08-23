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

    def record_analysis_result(
        self,
        confidence: Optional[float],
        decision: Optional[str] = None,
        diagnosis: Optional[str] = None,
        warning_message: Optional[str] = None,
        latency: Optional[float] = None
    ) -> None:
        """Registra el resultado entregado por VisionAI y la decisión final."""
        with self._lock:
            self._last_analysis_confidence = confidence
            self._last_decision = decision
            self._last_diagnosis = diagnosis
            self._last_warning_message = warning_message
            if latency is not None:
                self._ai_latency = latency
            self._total_events_processed += 1


# Instancia global accesible en toda la aplicación (Singleton)
system_state = SystemState()
