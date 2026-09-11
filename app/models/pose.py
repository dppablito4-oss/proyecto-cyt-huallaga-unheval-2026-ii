"""Contratos compactos para pose corporal efímera y no biométrica."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PosePoint(BaseModel):
    """Landmark útil expresado en píxeles del frame original."""

    x: float
    y: float
    visibility: float = Field(1.0, ge=0.0, le=1.0)


class PoseState(BaseModel):
    """Subconjunto corporal actual; no conserva el esqueleto completo."""

    track_id: int = Field(..., ge=0)
    timestamp: datetime
    confidence: float = Field(..., ge=0.0, le=1.0)
    left_wrist: Optional[PosePoint] = None
    right_wrist: Optional[PosePoint] = None
    left_elbow: Optional[PosePoint] = None
    right_elbow: Optional[PosePoint] = None
    left_shoulder: Optional[PosePoint] = None
    right_shoulder: Optional[PosePoint] = None
    left_hip: Optional[PosePoint] = None
    right_hip: Optional[PosePoint] = None

    @property
    def visible_wrists(self) -> list[PosePoint]:
        return [
            point
            for point in (self.left_wrist, self.right_wrist)
            if point is not None
        ]
