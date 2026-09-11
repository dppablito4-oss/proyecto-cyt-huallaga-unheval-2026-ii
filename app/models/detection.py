"""Contratos generales para detecciones locales multiclase."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.models.event import BoundingBox, LocalDetection, LocalDetectionSummary
from app.models.tracking import Point


class Detection(BaseModel):
    """Objeto observado por el detector en un único fotograma."""

    class_id: int = Field(..., ge=0)
    label: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BoundingBox
    centroid: Point


class DetectionFrame(BaseModel):
    """Salida completa del detector para un instante de cámara."""

    timestamp: datetime
    detections: list[Detection] = Field(default_factory=list)

    @property
    def persons(self) -> list[Detection]:
        return [item for item in self.detections if item.label.casefold() == "person"]

    @property
    def objects(self) -> list[Detection]:
        return [item for item in self.detections if item.label.casefold() != "person"]

    @property
    def counts_by_label(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.detections:
            counts[item.label] = counts.get(item.label, 0) + 1
        return counts

    def to_local_summary(self) -> LocalDetectionSummary:
        """Adapta solo personas al contrato heredado usado por EventManager."""
        persons = self.persons
        return LocalDetectionSummary(
            persons=len(persons),
            max_confidence=max((item.confidence for item in persons), default=0.0),
            detections=[
                LocalDetection(
                    label=item.label,
                    confidence=item.confidence,
                    bbox=item.bbox.model_copy(deep=True),
                )
                for item in persons
            ],
        )
