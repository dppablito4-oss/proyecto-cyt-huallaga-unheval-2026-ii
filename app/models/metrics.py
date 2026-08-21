"""
Módulo de Métricas Experimentales (System Metrics Model)
========================================================

Responsabilidad:
----------------
Modelar los datos cuantitativos y parámetros experimentales asociados a cada evento procesado.
Esencial para la investigación académica, benchmarking y evaluación de rendimiento del sistema.

Flujo de invocación:
--------------------
- Construido al finalizar el pipeline de un evento combinando datos de `app.metrics.latency.LatencyTimer`,
  `app.metrics.network.NetworkMetrics`, `app.vision.image_processor.ImageProcessor` y `app.ai.vision_client.VisionAI`.
- Registrado por `app.metrics.collector.MetricsCollector` y guardado dentro de `EventModel.metrics`.
"""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class SystemMetrics(BaseModel):
    """
    Entidad que agrupa las mediciones de rendimiento, latencias y pesos de datos de un evento.
    """
    event_id: str = Field(..., description="UUID del evento correspondiente.")
    timestamp: datetime = Field(default_factory=datetime.now, description="Fecha y hora del registro.")
    camera_id: str = Field("CAM_001", description="Identificador de la cámara origen.")
    
    # Métricas de fotogramas y resolución
    frames_captured: int = Field(0, description="Total de frames recopilados en la ventana de captura.")
    frames_sent: int = Field(0, description="Cantidad de frames seleccionados y enviados a la API de visión.")
    image_resolution: str = Field("1280x720", description="Resolución aplicada a las imágenes enviadas.")
    jpeg_quality: int = Field(70, description="Nivel de compresión JPEG utilizado (1-100).")
    payload_bytes: int = Field(0, description="Tamaño total del payload en bytes transferido a la API.")
    
    # Métricas de confianza de detección e inferencia
    local_detection_confidence: float = Field(0.0, description="Confianza máxima obtenida por YOLO local.")
    ai_confidence: Optional[float] = Field(None, description="Confianza devuelta por la IA multimodal.")
    ai_model: str = Field("gpt-4o", description="Nombre del modelo de visión utilizado en la inferencia.")
    
    # Latencias y tiempos de respuesta (en milisegundos)
    ai_latency_ms: float = Field(0.0, description="Tiempo que tardó la llamada de red a la API de visión.")
    tts_latency_ms: float = Field(0.0, description="Tiempo de generación del archivo de audio por TTS.")
    total_latency_ms: float = Field(0.0, description="Tiempo total desde la detección inicial de YOLO hasta la decisión/audio.")
    
    # Decisión adoptada por el sistema
    decision: str = Field("IGNORE", description="Decisión final tomada por el DecisionEngine ('IGNORE', 'LOG_ONLY', 'WARN').")
