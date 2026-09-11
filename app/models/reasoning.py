"""Contratos explicables para razonamiento temporal y eventos candidatos."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.models.tracking import Point


class ObjectLifecycleState(str, Enum):
    UNKNOWN = "UNKNOWN"
    CARRIED = "CARRIED"
    RELEASED = "RELEASED"
    MOVING = "MOVING"
    STATIONARY = "STATIONARY"
    ABANDONED = "ABANDONED"
    LOST = "LOST"


class EventCandidateState(str, Enum):
    IGNORE = "IGNORE"
    UNCERTAIN = "UNCERTAIN"
    CONFIRMED = "CONFIRMED"


class ObjectStateSnapshot(BaseModel):
    """Estado local auditable de un objeto con memoria de su ciclo actual."""

    object_track_id: int = Field(..., ge=0)
    object_class: str
    state: ObjectLifecycleState = ObjectLifecycleState.UNKNOWN
    previous_state: Optional[ObjectLifecycleState] = None
    person_track_id: Optional[int] = Field(None, ge=0)
    held_probability: float = Field(0.0, ge=0.0, le=1.0)
    association_peak: float = Field(0.0, ge=0.0, le=1.0)
    object_was_carried: bool = False
    carried_since: Optional[datetime] = None
    carried_duration: float = Field(0.0, ge=0.0)
    release_detected: bool = False
    release_timestamp: Optional[datetime] = None
    release_position: Optional[Point] = None
    release_zone: Optional[str] = None
    throw_detected: bool = False
    stationary_since: Optional[datetime] = None
    stationary_duration: float = Field(0.0, ge=0.0)
    person_distance: Optional[float] = Field(None, ge=0.0)
    person_moving_away: bool = False
    last_seen: datetime
    updated_at: datetime


class EventEvidence(BaseModel):
    """Evidencia local estructurada que explica el score del candidato."""

    person_present: bool
    object_present: bool
    object_was_carried: bool
    release_detected: bool
    release_zone: Optional[str] = None
    throw_detected: bool = False
    object_stationary: bool
    stationary_duration: float = Field(0.0, ge=0.0)
    person_moving_away: bool
    person_distance: Optional[float] = Field(None, ge=0.0)
    object_current_zone: Optional[str] = None
    association_peak: float = Field(0.0, ge=0.0, le=1.0)
    carried_duration: float = Field(0.0, ge=0.0)
    timestamps: dict[str, datetime] = Field(default_factory=dict)


class EventCandidate(BaseModel):
    """Hipótesis local; todavía no representa un evento persistido ni una alerta."""

    id: str
    camera_id: str
    person_track_id: Optional[int] = Field(None, ge=0)
    object_track_id: Optional[int] = Field(None, ge=0)
    object_class: Optional[str] = None
    event_type: str
    score: float = Field(..., ge=0.0, le=1.0)
    state: EventCandidateState
    evidence: EventEvidence
    started_at: datetime
    updated_at: datetime
