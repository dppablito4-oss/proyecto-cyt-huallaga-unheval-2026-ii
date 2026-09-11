"""Contratos del estado espacial actual de una cámara SIVARH."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.association import PersonObjectAssociation
from app.models.pose import PoseState
from app.models.tracking import TrackState


class NormalizedPoint(BaseModel):
    """Punto independiente de resolución, limitado al intervalo 0..1."""

    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)


class ZoneDefinition(BaseModel):
    """Polígono ambiental configurable para una cámara."""

    name: str = Field(..., min_length=1)
    polygon: list[NormalizedPoint] = Field(..., min_length=3)
    priority: int = 0


class ZoneState(BaseModel):
    """Ocupación instantánea de una zona."""

    name: str
    track_ids: list[int] = Field(default_factory=list)

    @property
    def occupancy(self) -> int:
        return len(self.track_ids)


class SceneState(BaseModel):
    """Fotografía estructurada y actualizable del contenido de una cámara."""

    camera_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    persons: dict[int, TrackState] = Field(default_factory=dict)
    objects: dict[int, TrackState] = Field(default_factory=dict)
    zones: dict[str, ZoneState] = Field(default_factory=dict)
    associations: list[PersonObjectAssociation] = Field(default_factory=list)

    def update(
        self,
        tracks: list[TrackState],
        zones: dict[str, ZoneState],
        timestamp: datetime,
    ) -> None:
        """Reemplaza el estado visible sin retener tracks expirados."""
        visible = [track.model_copy(deep=True) for track in tracks if track.visible]
        self.timestamp = timestamp
        self.persons = {
            track.track_id: track
            for track in visible
            if track.label.casefold() == "person"
        }
        self.objects = {
            track.track_id: track
            for track in visible
            if track.label.casefold() != "person"
        }
        self.zones = {
            name: state.model_copy(deep=True)
            for name, state in zones.items()
        }
        self.associations = []

    def set_associations(self, associations: list[PersonObjectAssociation]) -> None:
        self.associations = [item.model_copy(deep=True) for item in associations]

    def set_poses(self, poses: dict[int, PoseState]) -> None:
        """Adjunta únicamente poses vigentes a los tracks de persona actuales."""
        for track_id, person in self.persons.items():
            pose = poses.get(track_id)
            person.pose = pose.model_copy(deep=True) if pose is not None else None

    def association_for_object(self, track_id: int) -> Optional[PersonObjectAssociation]:
        return next(
            (
                association
                for association in self.associations
                if association.object_track_id == track_id
            ),
            None,
        )

    def zone_for_track(self, track_id: int) -> Optional[str]:
        track = self.persons.get(track_id) or self.objects.get(track_id)
        return track.current_zone if track is not None else None

    @property
    def active_tracks(self) -> int:
        return len(self.persons) + len(self.objects)
