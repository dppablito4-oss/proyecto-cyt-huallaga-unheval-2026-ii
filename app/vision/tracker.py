"""Adaptadores intercambiables de seguimiento multiobjeto para SIVARH."""

from __future__ import annotations

import logging
from datetime import datetime
from threading import RLock
from typing import Any, Optional, Protocol, Sequence

import numpy as np

from app.models.event import BoundingBox, LocalDetection
from app.models.tracking import Point, TrackedObject, TrackState
from app.vision.track_history import TrackHistory

logger = logging.getLogger(__name__)


class MultiObjectTracker(Protocol):
    """Contrato independiente del algoritmo concreto de tracking."""

    last_created_track_ids: tuple[int, ...]
    last_expired_track_ids: tuple[int, ...]

    def update(
        self,
        detections: Sequence[LocalDetection],
        timestamp: datetime,
        frame: Any = None,
    ) -> list[TrackedObject]: ...

    def reset(self) -> None: ...

    @property
    def active_states(self) -> list[TrackState]: ...


class NullTracker:
    """Implementación segura cuando tracking está deshabilitado."""

    last_created_track_ids: tuple[int, ...] = ()
    last_expired_track_ids: tuple[int, ...] = ()

    def update(
        self,
        detections: Sequence[LocalDetection],
        timestamp: datetime,
        frame: Any = None,
    ) -> list[TrackedObject]:
        return []

    def reset(self) -> None:
        return None

    @property
    def active_states(self) -> list[TrackState]:
        return []


class ByteTrackAdapter:
    """ByteTrack de Roboflow aislado tras el contrato interno de SIVARH."""

    def __init__(
        self,
        history_seconds: float = 15.0,
        track_ttl_seconds: float = 5.0,
        frame_rate: float = 30.0,
        track_activation_threshold: float = 0.5,
        lost_track_buffer: int = 30,
        minimum_consecutive_frames: int = 2,
        minimum_iou_threshold: float = 0.1,
    ):
        if history_seconds <= 0 or track_ttl_seconds <= 0:
            raise ValueError("Las ventanas temporales de tracking deben ser mayores que cero.")
        self.history_seconds = float(history_seconds)
        self.track_ttl_seconds = float(track_ttl_seconds)
        self._backend_options = {
            "frame_rate": frame_rate,
            "track_activation_threshold": track_activation_threshold,
            "high_conf_det_threshold": track_activation_threshold,
            "lost_track_buffer": lost_track_buffer,
            "minimum_consecutive_frames": minimum_consecutive_frames,
            "minimum_iou_threshold": minimum_iou_threshold,
        }
        self._backend = None
        self._backend_initialization_attempted = False
        self._histories: dict[int, TrackHistory] = {}
        self._states: dict[int, TrackState] = {}
        self._first_seen: dict[int, datetime] = {}
        self._last_seen: dict[int, datetime] = {}
        self._lock = RLock()
        self.last_created_track_ids: tuple[int, ...] = ()
        self.last_expired_track_ids: tuple[int, ...] = ()

    def _ensure_backend(self):
        if self._backend is None and not self._backend_initialization_attempted:
            self._backend_initialization_attempted = True
            try:
                from trackers import ByteTrackTracker

                self._backend = ByteTrackTracker(**self._backend_options)
            except Exception as exc:
                logger.error("ByteTrack no pudo inicializarse; tracking deshabilitado: %s", exc)
        return self._backend

    @staticmethod
    def _to_supervision(detections: Sequence[LocalDetection]):
        import supervision as sv

        usable = [detection for detection in detections if detection.bbox is not None]
        if not usable:
            return sv.Detections.empty()
        return sv.Detections(
            xyxy=np.asarray(
                [[d.bbox.x1, d.bbox.y1, d.bbox.x2, d.bbox.y2] for d in usable],
                dtype=np.float32,
            ),
            confidence=np.asarray([d.confidence for d in usable], dtype=np.float32),
            # Fase 1 conserva el detector de personas actual. Fase 3 generalizará estos IDs.
            class_id=np.zeros(len(usable), dtype=np.int32),
            data={"class_name": np.asarray([d.label for d in usable])},
        )

    def update(
        self,
        detections: Sequence[LocalDetection],
        timestamp: datetime,
        frame: Any = None,
    ) -> list[TrackedObject]:
        backend = self._ensure_backend()
        if backend is None:
            return []
        tracked = backend.update(
            self._to_supervision(detections),
            frame=frame,
            timestamp=timestamp.timestamp(),
        )

        created: list[int] = []
        result: list[TrackedObject] = []
        with self._lock:
            for state in self._states.values():
                state.visible = False

            tracker_ids = tracked.tracker_id
            if tracker_ids is not None:
                labels = tracked.data.get("class_name")
                for index, raw_track_id in enumerate(tracker_ids):
                    track_id = int(raw_track_id)
                    if track_id < 0:
                        continue
                    coordinates = tracked.xyxy[index]
                    bbox = BoundingBox(
                        x1=float(coordinates[0]),
                        y1=float(coordinates[1]),
                        x2=float(coordinates[2]),
                        y2=float(coordinates[3]),
                    )
                    centroid = Point(
                        x=(bbox.x1 + bbox.x2) / 2.0,
                        y=(bbox.y1 + bbox.y2) / 2.0,
                    )
                    if track_id not in self._histories:
                        self._histories[track_id] = TrackHistory(track_id, self.history_seconds)
                        self._first_seen[track_id] = timestamp
                        created.append(track_id)
                    history = self._histories[track_id]
                    history.add(centroid, timestamp)
                    self._last_seen[track_id] = timestamp

                    class_id = int(tracked.class_id[index]) if tracked.class_id is not None else 0
                    confidence = (
                        float(tracked.confidence[index]) if tracked.confidence is not None else 1.0
                    )
                    label = str(labels[index]) if labels is not None else str(class_id)
                    tracked_object = TrackedObject(
                        track_id=track_id,
                        class_id=class_id,
                        label=label,
                        confidence=confidence,
                        bbox=bbox,
                        centroid=centroid,
                        first_seen=self._first_seen[track_id],
                        last_seen=timestamp,
                    )
                    velocity_x, velocity_y = history.velocity
                    self._states[track_id] = TrackState(
                        **tracked_object.model_dump(),
                        trajectory=history.trajectory,
                        current_zone=history.current_zone,
                        previous_zone=history.previous_zone,
                        velocity_x=velocity_x,
                        velocity_y=velocity_y,
                        speed=history.speed,
                        distance_travelled=history.distance_travelled,
                        visible=True,
                    )
                    result.append(tracked_object)

            expired = self._expire_stale(timestamp)
            self.last_created_track_ids = tuple(created)
            self.last_expired_track_ids = tuple(expired)
        return result

    def _expire_stale(self, timestamp: datetime) -> list[int]:
        expired = [
            track_id
            for track_id, last_seen in self._last_seen.items()
            if (timestamp - last_seen).total_seconds() > self.track_ttl_seconds
        ]
        for track_id in expired:
            self._histories.pop(track_id, None)
            self._states.pop(track_id, None)
            self._first_seen.pop(track_id, None)
            self._last_seen.pop(track_id, None)
        return expired

    @property
    def active_states(self) -> list[TrackState]:
        with self._lock:
            return [
                state.model_copy(deep=True)
                for state in self._states.values()
                if state.visible
            ]

    @property
    def retained_states(self) -> list[TrackState]:
        """Incluye tracks temporalmente perdidos que todavía no superaron el TTL."""
        with self._lock:
            return [state.model_copy(deep=True) for state in self._states.values()]

    def reset(self) -> None:
        with self._lock:
            if self._backend is not None:
                self._backend.reset()
            self._backend_initialization_attempted = False
            self._backend = None
            self._histories.clear()
            self._states.clear()
            self._first_seen.clear()
            self._last_seen.clear()
            self.last_created_track_ids = ()
            self.last_expired_track_ids = ()


def create_tracker(
    tracker_type: str = "bytetrack",
    enabled: bool = True,
    **kwargs,
) -> MultiObjectTracker:
    """Fábrica que evita acoplar el worker a un algoritmo concreto."""
    if not enabled:
        return NullTracker()
    normalized = tracker_type.strip().lower()
    if normalized == "bytetrack":
        return ByteTrackAdapter(**kwargs)
    raise ValueError(f"Tracker no soportado: {tracker_type!r}.")


# Alias temporal para importaciones antiguas. El comportamiento placeholder se elimina.
Tracker = ByteTrackAdapter
