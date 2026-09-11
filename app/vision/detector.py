"""Detector YOLO multiclase con salida tipada y compatibilidad heredada."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional, Protocol, Sequence

from app.models.detection import Detection, DetectionFrame
from app.models.event import BoundingBox, LocalDetectionSummary
from app.models.tracking import Point

logger = logging.getLogger(__name__)


class ObjectDetector(Protocol):
    """Contrato independiente del modelo concreto de detección."""

    def detect(self, frame: Any, timestamp: Optional[datetime] = None) -> DetectionFrame: ...


class LocalDetector:
    """Detector local YOLO limitado a las clases configuradas por nombre."""

    def __init__(
        self,
        model_name: str = "yolov8n.pt",
        confidence_threshold: float = 0.5,
        monitored_classes: Sequence[str] = ("person",),
    ):
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold debe estar entre 0 y 1.")
        normalized = tuple(
            dict.fromkeys(
                name.strip().casefold()
                for name in monitored_classes
                if name.strip()
            )
        )
        if not normalized:
            raise ValueError("Debe configurarse al menos una clase de detección.")
        self.model_name = model_name
        self.confidence_threshold = float(confidence_threshold)
        self.monitored_classes = normalized
        self.model = None
        self._initialized = False
        self._unknown_classes_reported: tuple[str, ...] = ()

    def initialize(self) -> bool:
        """Carga YOLO de forma perezosa y permite degradación segura."""
        if self._initialized:
            return True
        try:
            from ultralytics import YOLO

            self.model = YOLO(self.model_name)
            self._initialized = True
            self._resolve_class_filter()
            logger.info(
                "Modelo YOLO '%s' inicializado para clases: %s.",
                self.model_name,
                ", ".join(self.monitored_classes),
            )
            return True
        except Exception as exc:
            logger.warning(
                "No se pudo cargar el modelo YOLO '%s': %s. Operando sin detecciones.",
                self.model_name,
                exc,
            )
            return False

    def _model_class_names(self) -> dict[int, str]:
        names = getattr(self.model, "names", {}) if self.model is not None else {}
        if isinstance(names, dict):
            return {int(class_id): str(label) for class_id, label in names.items()}
        return {class_id: str(label) for class_id, label in enumerate(names)}

    def _resolve_class_filter(self) -> tuple[list[int], dict[int, str]]:
        names = self._model_class_names()
        monitored = set(self.monitored_classes)
        selected = {
            class_id: label
            for class_id, label in names.items()
            if label.casefold() in monitored
        }
        available = {label.casefold() for label in selected.values()}
        unknown = tuple(sorted(monitored - available))
        if unknown and unknown != self._unknown_classes_reported:
            logger.warning(
                "Clases configuradas ausentes en el modelo '%s': %s.",
                self.model_name,
                ", ".join(unknown),
            )
            self._unknown_classes_reported = unknown
        return list(selected), selected

    def detect(self, frame: Any, timestamp: Optional[datetime] = None) -> DetectionFrame:
        """Detecta todas las clases monitoreadas y conserva sus IDs del modelo."""
        captured_at = timestamp or datetime.now()
        if not self._initialized:
            self.initialize()
        if not self._initialized or self.model is None:
            return DetectionFrame(timestamp=captured_at)

        class_ids, class_names = self._resolve_class_filter()
        if not class_ids:
            return DetectionFrame(timestamp=captured_at)

        try:
            results = self.model(
                frame,
                classes=class_ids,
                conf=self.confidence_threshold,
                verbose=False,
            )
            detections: list[Detection] = []
            for result in results:
                for box in result.boxes:
                    class_id = int(box.cls[0])
                    label = class_names.get(class_id)
                    if label is None:
                        continue
                    confidence = float(box.conf[0])
                    x1, y1, x2, y2 = (float(value) for value in box.xyxy[0].tolist())
                    bbox = BoundingBox(x1=x1, y1=y1, x2=x2, y2=y2)
                    detections.append(
                        Detection(
                            class_id=class_id,
                            label=label,
                            confidence=confidence,
                            bbox=bbox,
                            centroid=Point(x=(x1 + x2) / 2.0, y=(y1 + y2) / 2.0),
                        )
                    )
            return DetectionFrame(timestamp=captured_at, detections=detections)
        except Exception as exc:
            logger.error("Error durante la inferencia YOLO multiclase: %s", exc)
            return DetectionFrame(timestamp=captured_at)

    def detect_persons(self, frame: Any) -> LocalDetectionSummary:
        """Compatibilidad temporal para consumidores del detector anterior."""
        return self.detect(frame).to_local_summary()
