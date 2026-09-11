"""
Módulo de Modelos de Eventos (Event Data Models)
================================================

Responsabilidad:
----------------
Definir la estructura de datos tipada con Pydantic para representar las detecciones
locales, cajas delimitadoras (Bounding Boxes), metadata de captura temporal
y el ciclo de vida completo de un evento sospechoso.

Flujo de invocación:
--------------------
- Creado inicialmente por `app.events.manager.EventManager` cuando YOLO detecta una persona.
- Enriquecido por `app.vision.frame_selector.FrameSelector` y `app.vision.image_processor.ImageProcessor`.
- Actualizado con el resultado de `app.ai.vision_client.VisionAI` y la decisión de `app.events.rules.DecisionEngine`.
- Persistido en base de datos mediante `app.storage.local_repository.SQLiteEventsRepository`.
- Servido al frontend mediante `app.api.routes.events`.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    """
    Coordenadas rectangulares normalizadas o en píxeles que delimitan un objeto/persona en el frame.
    Generado por `app.vision.detector.LocalDetector` a partir de la salida de Ultralytics YOLO.
    """
    x1: float = Field(..., description="Coordenada X superior izquierda.")
    y1: float = Field(..., description="Coordenada Y superior izquierda.")
    x2: float = Field(..., description="Coordenada X inferior derecha.")
    y2: float = Field(..., description="Coordenada Y inferior derecha.")


class LocalDetection(BaseModel):
    """
    Representa una detección individual generada por el detector local (YOLO).
    """
    label: str = Field("person", description="Etiqueta de la clase detectada (por defecto 'person').")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Nivel de certeza de la detección (0.00 a 1.00).")
    bbox: Optional[BoundingBox] = Field(None, description="Caja delimitadora de la detección.")


class LocalDetectionSummary(BaseModel):
    """
    Resumen consolidado de todas las detecciones encontradas en un cuadro específico.
    Se conserva como metadata compatible; ya no dispara eventos por presencia.
    """
    persons: int = Field(0, description="Cantidad total de personas identificadas en el encuadre.")
    max_confidence: float = Field(0.0, description="Máxima confianza encontrada entre todas las personas detectadas.")
    detections: List[LocalDetection] = Field(default_factory=list, description="Lista detallada de detecciones.")


class CaptureMetadata(BaseModel):
    """
    Información técnica sobre los fotogramas capturados durante el evento.
    """
    total_frames: int = Field(0, description="Número de frames acumulados en la ventana de captura.")
    selected_frames: int = Field(0, description="Número de frames clave seleccionados para enviar a la IA.")
    jpeg_quality: int = Field(70, description="Calidad de compresión JPEG aplicada (1-100).")
    frame_paths: List[str] = Field(default_factory=list, description="Rutas en disco de los frames guardados para auditoría.")


class EventModel(BaseModel):
    """
    Modelo principal que representa la entidad completa de un Evento de Vigilancia Ambiental.
    Sigue el contrato conceptual especificado en la sección 47 de `documentacio.md`.
    """
    id: str = Field(..., description="Identificador único universal (UUID v4) del evento.")
    camera_id: str = Field("CAM_001", description="Identificador de la cámara que originó el evento.")
    started_at: datetime = Field(default_factory=datetime.now, description="Marca temporal de inicio de la detección.")
    ended_at: Optional[datetime] = Field(None, description="Marca temporal de finalización de captura del evento.")
    status: str = Field("created", description="Estado del ciclo de vida: created, capturing, analyzing, completed, failed.")
    
    # Resumen de detección económica inicial (YOLO)
    local_detection: LocalDetectionSummary = Field(default_factory=LocalDetectionSummary)

    # Evidencia local espacio-temporal (SIVARH v2). Los campos son opcionales
    # para seguir leyendo eventos históricos creados por el flujo anterior.
    candidate_id: Optional[str] = None
    person_track_id: Optional[int] = Field(None, ge=0)
    object_track_id: Optional[int] = Field(None, ge=0)
    object_class: Optional[str] = None
    local_event_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    local_event_state: Optional[str] = None
    release_detected: bool = False
    release_timestamp: Optional[datetime] = None
    release_zone: Optional[str] = None
    throw_detected: bool = False
    object_stationary: bool = False
    person_moving_away: bool = False
    event_trace: Dict[str, Any] = Field(default_factory=dict)
    openai_used: bool = False
    openai_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    final_decision: Optional[str] = None
    
    # Metadatos de compresión y fotogramas
    capture: CaptureMetadata = Field(default_factory=CaptureMetadata)
    
    # Resultado estructurado proveniente de la IA Multimodal (OpenAI)
    analysis: Optional[Dict[str, Any]] = Field(None, description="Resultado serializado de AIAnalysisResult.")
    
    # Decisión final emitida por el DecisionEngine ('IGNORE', 'LOG_ONLY', 'WARN')
    decision: Optional[str] = Field(None, description="Acción final ejecutada por el sistema.")
    
    # Métricas técnicas de latencia, red y ejecución
    metrics: Dict[str, Any] = Field(default_factory=dict, description="Métricas de rendimiento asociadas al evento.")

    def openai_metadata(self) -> Dict[str, Any]:
        """Contexto local mínimo que acompaña a los keyframes de verificación."""
        return {
            "candidate_id": self.candidate_id,
            "camera_id": self.camera_id,
            "person_track_id": self.person_track_id,
            "object_track_id": self.object_track_id,
            "object_class": self.object_class,
            "local_event_score": self.local_event_score,
            "local_event_state": self.local_event_state,
            "release_detected": self.release_detected,
            "release_timestamp": (
                self.release_timestamp.isoformat() if self.release_timestamp else None
            ),
            "release_zone": self.release_zone,
            "throw_detected": self.throw_detected,
            "object_stationary": self.object_stationary,
            "person_moving_away": self.person_moving_away,
            "event_trace": self.event_trace,
        }
