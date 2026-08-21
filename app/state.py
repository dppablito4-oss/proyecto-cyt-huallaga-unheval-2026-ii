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

from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


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
    last_event_time: Optional[str] = Field(None, description="Marca de tiempo ISO del último evento detectado.")
    last_analysis_confidence: Optional[float] = Field(None, description="Confianza (0.0 - 1.0) de la última inferencia de IA.")
    last_warning_message: Optional[str] = Field(None, description="Último mensaje de advertencia verbal generado.")
    ai_model: str = Field("gpt-4o", description="Nombre del modelo multimodal en uso.")
    frames_per_analysis: int = Field(5, description="Número de fotogramas enviados por análisis.")
    total_events_processed: int = Field(0, description="Contador histórico de eventos analizados en la sesión.")


class SystemState:
    """
    Gestor en memoria del estado reactivo del sistema.
    Thread-safe para lecturas y actualizaciones directas desde los diferentes módulos.
    """

    def __init__(self):
        self._running = True
        self._camera_connected = False
        self._camera_source = "0"
        self._fps = 0.0
        self._persons_detected = 0
        self._active_event = False
        self._last_event_time: Optional[datetime] = None
        self._last_analysis_confidence: Optional[float] = None
        self._last_warning_message: Optional[str] = None
        self._ai_model = "gpt-4o"
        self._frames_per_analysis = 5
        self._total_events_processed = 0

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializa el estado actual a un diccionario Python estándar.
        Llamado por `app.api.routes.status` y `app.api.websocket`.
        """
        return {
            "running": self._running,
            "camera_connected": self._camera_connected,
            "camera_source": self._camera_source,
            "fps": self._fps,
            "persons_detected": self._persons_detected,
            "active_event": self._active_event,
            "last_event_time": self._last_event_time.isoformat() if self._last_event_time else None,
            "last_analysis_confidence": self._last_analysis_confidence,
            "last_warning_message": self._last_warning_message,
            "ai_model": self._ai_model,
            "frames_per_analysis": self._frames_per_analysis,
            "total_events_processed": self._total_events_processed
        }

    def set_camera_status(self, connected: bool, source: str = "0", fps: float = 0.0) -> None:
        """
        Actualiza el estado de la cámara y los FPS medidos.
        Invocado por el worker de captura en `app.camera`.
        """
        self._camera_connected = connected
        self._camera_source = source
        self._fps = fps

    def set_persons_detected(self, count: int) -> None:
        """
        Actualiza la cantidad de personas observadas en el último frame.
        Invocado por `app.vision.detector.LocalDetector` tras procesar un cuadro.
        """
        self._persons_detected = count

    def set_active_event(self, active: bool) -> None:
        """
        Marca el inicio o fin de una ventana de captura de evento.
        Invocado por `app.events.manager.EventManager`.
        """
        self._active_event = active
        if active:
            self._last_event_time = datetime.now()

    def record_analysis_result(self, confidence: Optional[float], warning_message: Optional[str]) -> None:
        """
        Registra el resultado entregado por `app.ai.vision_client.VisionAI` y la decisión
        tomada por `app.events.rules.DecisionEngine`.
        """
        self._last_analysis_confidence = confidence
        self._last_warning_message = warning_message
        self._total_events_processed += 1


# Instancia global accesible en toda la aplicación (Singleton)
system_state = SystemState()
