"""Contratos tipados para el seguimiento temporal y anónimo de objetos."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.event import BoundingBox
from app.models.pose import PoseState


class Point(BaseModel):
    """Coordenada bidimensional expresada en píxeles."""

    x: float
    y: float


class TrajectoryPoint(BaseModel):
    """Observación temporal compacta de la posición de un track."""

    position: Point
    timestamp: datetime
    zone: Optional[str] = None


class TrackedObject(BaseModel):
    """Detección asociada a un identificador temporal y anónimo."""

    track_id: int = Field(..., ge=0)
    class_id: int = Field(..., ge=0)
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    bbox: BoundingBox
    centroid: Point
    first_seen: datetime
    last_seen: datetime


class TrackState(BaseModel):
    """Estado actual de un track junto con su memoria temporal acotada."""

    track_id: int = Field(..., ge=0)
    class_id: int = Field(..., ge=0)
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    first_seen: datetime
    last_seen: datetime
    bbox: BoundingBox
    centroid: Point
    trajectory: list[TrajectoryPoint] = Field(default_factory=list)
    current_zone: Optional[str] = None
    previous_zone: Optional[str] = None
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    speed: float = Field(0.0, ge=0.0)
    distance_travelled: float = Field(0.0, ge=0.0)
    visible: bool = True
    pose: Optional[PoseState] = None
