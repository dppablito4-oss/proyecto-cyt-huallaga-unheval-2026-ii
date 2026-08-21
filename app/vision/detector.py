import logging
from typing import List, Dict, Any, Optional
from app.models.event import LocalDetectionSummary, LocalDetection, BoundingBox

logger = logging.getLogger(__name__)

class LocalDetector:
    """
    Detector local ligero basado en Ultralytics YOLO para la detección inicial de personas (clase 0 en COCO).
    Funciona como filtro previo económico para evitar llamadas innecesarias a la API multimodal.
    """

    def __init__(self, model_name: str = "yolov8n.pt", confidence_threshold: float = 0.50):
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._initialized = False

    def initialize(self) -> bool:
        """Carga el modelo YOLO de forma perezosa."""
        if self._initialized:
            return True
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.model_name)
            self._initialized = True
            logger.info(f"Modelo YOLO '{self.model_name}' cargado exitosamente.")
            return True
        except Exception as e:
            logger.warning(f"No se pudo cargar el modelo YOLO '{self.model_name}': {e}. Operando en modo placeholder.")
            return False

    def detect_persons(self, frame: Any) -> LocalDetectionSummary:
        """
        Analiza un fotograma en busca de personas (clase 'person' / ID 0).
        Retorna un resumen con cantidad de personas, confianza máxima y bounding boxes.
        """
        if not self._initialized:
            # Placeholder seguro para arranque inicial sin modelo
            return LocalDetectionSummary(persons=0, max_confidence=0.0, detections=[])

        try:
            # Inferencia YOLO filtrada por clase 0 (persona)
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
                            bbox=BoundingBox(x1=xyxy[0], y1=xyxy[1], x2=xyxy[2], y2=xyxy[3])
                        )
                    )

            return LocalDetectionSummary(
                persons=len(detections),
                max_confidence=max_conf,
                detections=detections
            )
        except Exception as e:
            logger.error(f"Error durante la detección YOLO: {e}")
            return LocalDetectionSummary(persons=0, max_confidence=0.0, detections=[])
