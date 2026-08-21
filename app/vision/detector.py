"""
Módulo de Detección Local con YOLO (LocalDetector)
==================================================

Responsabilidad:
----------------
Ejecutar detección de objetos local y ligera mediante modelos pre-entrenados de Ultralytics YOLO
(por defecto `yolov8n.pt`).
Su función fundamental dentro de la arquitectura es actuar como un **filtro económico**:
determinar si hay personas presentes en el encuadre (clase 0 de COCO).

Flujo de invocación:
--------------------
- Cada fotograma leído por `app.camera` se pasa a `detect_persons(frame)`.
- Si se detectan personas y la confianza supera `settings.YOLO_PERSON_CONFIDENCE`:
  * Se actualiza `app.state.system_state.set_persons_detected()`.
  * Se envía el resumen a `app.events.manager.EventManager.should_trigger_event()`.
- Si NO hay personas, el sistema NO envía imágenes a la IA multimodal, ahorrando ancho de banda,
  costos de API y latencia.
"""

import logging
from typing import List, Dict, Any, Optional
from app.models.event import LocalDetectionSummary, LocalDetection, BoundingBox

logger = logging.getLogger(__name__)


class LocalDetector:
    """
    Detector local basado en Ultralytics YOLO especializado en detección rápida de personas.
    Implementa carga perezosa (lazy loading) y degradación elegante si no hay modelos descargados.
    """

    def __init__(self, model_name: str = "yolov8n.pt", confidence_threshold: float = 0.50):
        """
        Args:
            model_name (str): Archivo de pesos YOLO (ej. 'yolov8n.pt', 'yolov8s.pt').
            confidence_threshold (float): Umbral mínimo de confianza para considerar válida una detección.
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._initialized = False

    def initialize(self) -> bool:
        """
        Carga el modelo YOLO en memoria. Si los pesos no existen localmente,
        la librería Ultralytics los descarga automáticamente desde GitHub.
        """
        if self._initialized:
            return True
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
            self._initialized = True
            logger.info(f"Modelo YOLO '{self.model_name}' inicializado correctamente.")
            return True
        except Exception as e:
            logger.warning(f"No se pudo cargar el modelo YOLO '{self.model_name}': {e}. Operando en modo simulación.")
            return False

    def detect_persons(self, frame: Any) -> LocalDetectionSummary:
        """
        Ejecuta la inferencia sobre una matriz de imagen OpenCV.

        Args:
            frame (np.ndarray): Imagen en formato BGR proveniente de `CameraSource.read()`.

        Returns:
            LocalDetectionSummary: Resumen estructurado con el número de personas encontradas,
                                   la confianza máxima y los cuadros delimitadores.
        """
        # Si el modelo no pudo inicializarse (modo fallback), devuelve resultado neutro
        if not self._initialized:
            return LocalDetectionSummary(persons=0, max_confidence=0.0, detections=[])

        try:
            # Filtrar inferencia exclusivamente para la clase 0 ('person' en COCO dataset)
            results = self.model(frame, classes=[0], conf=self.confidence_threshold, verbose=False)
            detections: List[LocalDetection] = []
            max_conf = 0.0

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].tolist()
                    if conf > max_conf:
                        max_conf = conf
                    
                    detections.append(
                        LocalDetection(
                            label="person",
                            confidence=conf,
                            bbox=BoundingBox(
                                x1=float(xyxy[0]),
                                y1=float(xyxy[1]),
                                x2=float(xyxy[2]),
                                y2=float(xyxy[3])
                            )
                        )
                    )

            return LocalDetectionSummary(
                persons=len(detections),
                max_confidence=max_conf,
                detections=detections
            )
        except Exception as e:
            logger.error(f"Error durante la inferencia de personas con YOLO: {e}")
            return LocalDetectionSummary(persons=0, max_confidence=0.0, detections=[])
