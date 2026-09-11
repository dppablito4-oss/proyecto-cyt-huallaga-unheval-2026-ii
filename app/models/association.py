"""Contratos explicables para asociaciones temporales persona–objeto."""

from datetime import datetime

from pydantic import BaseModel, Field


class AssociationSignals(BaseModel):
    """Señales normalizadas que contribuyen al puntaje final."""

    bbox_proximity: float = Field(..., ge=0.0, le=1.0)
    centroid_proximity: float = Field(..., ge=0.0, le=1.0)
    trajectory_similarity: float = Field(..., ge=0.0, le=1.0)
    temporal_consistency: float = Field(..., ge=0.0, le=1.0)
    hand_proximity: float | None = Field(None, ge=0.0, le=1.0)


class PersonObjectAssociation(BaseModel):
    """Mejor relación observada entre un objeto y una persona."""

    person_track_id: int = Field(..., ge=0)
    object_track_id: int = Field(..., ge=0)
    association_score: float = Field(..., ge=0.0, le=1.0)
    signals: AssociationSignals
    first_seen: datetime
    last_seen: datetime
    duration_seconds: float = Field(..., ge=0.0)
    confirmed: bool = False

    @property
    def key(self) -> str:
        return f"{self.person_track_id}:{self.object_track_id}"
