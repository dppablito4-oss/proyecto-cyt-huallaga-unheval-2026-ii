"""Máquina de estados temporal para objetos potencialmente transportables."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import hypot
from typing import Optional

from app.models.association import PersonObjectAssociation
from app.models.reasoning import ObjectLifecycleState, ObjectStateSnapshot
from app.models.scene import SceneState
from app.models.tracking import Point, TrackState, TrajectoryPoint


@dataclass
class _ObjectMemory:
    object_track_id: int
    object_class: str
    state: ObjectLifecycleState
    last_seen: datetime
    previous_state: Optional[ObjectLifecycleState] = None
    person_track_id: Optional[int] = None
    held_probability: float = 0.0
    association_peak: float = 0.0
    object_was_carried: bool = False
    carried_since: Optional[datetime] = None
    release_detected: bool = False
    release_timestamp: Optional[datetime] = None
    release_position: Optional[Point] = None
    release_zone: Optional[str] = None
    association_below_since: Optional[datetime] = None
    stationary_since: Optional[datetime] = None
    stationary_duration: float = 0.0
    person_distance: Optional[float] = None
    person_moving_away: bool = False
    distance_samples: deque[tuple[datetime, float]] = field(default_factory=deque)


class ObjectStateMachine:
    """Aplica transiciones explícitas sin convertir desapariciones en liberaciones."""

    _ALLOWED_TRANSITIONS = {
        ObjectLifecycleState.UNKNOWN: {ObjectLifecycleState.CARRIED},
        ObjectLifecycleState.CARRIED: {ObjectLifecycleState.RELEASED},
        ObjectLifecycleState.RELEASED: {
            ObjectLifecycleState.CARRIED,
            ObjectLifecycleState.MOVING,
            ObjectLifecycleState.STATIONARY,
        },
        ObjectLifecycleState.MOVING: {
            ObjectLifecycleState.CARRIED,
            ObjectLifecycleState.STATIONARY,
        },
        ObjectLifecycleState.STATIONARY: {
            ObjectLifecycleState.CARRIED,
            ObjectLifecycleState.MOVING,
            ObjectLifecycleState.ABANDONED,
        },
        ObjectLifecycleState.ABANDONED: {
            ObjectLifecycleState.CARRIED,
            ObjectLifecycleState.MOVING,
        },
        ObjectLifecycleState.LOST: {ObjectLifecycleState.CARRIED},
    }

    def __init__(
        self,
        carried_score: float = 0.7,
        carried_seconds: float = 0.5,
        release_score: float = 0.35,
        release_grace_seconds: float = 0.3,
        stationary_seconds: float = 2.0,
        stationary_max_distance_px: float = 12.0,
        moving_away_seconds: float = 1.0,
        moving_away_min_distance_px: float = 30.0,
        state_ttl_seconds: float = 10.0,
        relevant_zones: tuple[str, ...] = ("riverbank", "river_edge", "water"),
    ):
        if not 0 <= release_score < carried_score <= 1:
            raise ValueError("Los umbrales deben cumplir 0 <= release < carried <= 1.")
        if carried_seconds < 0 or release_grace_seconds < 0:
            raise ValueError("Las duraciones de asociación no pueden ser negativas.")
        positive = (
            stationary_seconds,
            stationary_max_distance_px,
            moving_away_seconds,
            moving_away_min_distance_px,
            state_ttl_seconds,
        )
        if any(value <= 0 for value in positive):
            raise ValueError("Las ventanas y distancias temporales deben ser mayores que cero.")
        self.carried_score = float(carried_score)
        self.carried_seconds = float(carried_seconds)
        self.release_score = float(release_score)
        self.release_grace_seconds = float(release_grace_seconds)
        self.stationary_seconds = float(stationary_seconds)
        self.stationary_max_distance_px = float(stationary_max_distance_px)
        self.moving_away_seconds = float(moving_away_seconds)
        self.moving_away_min_distance_px = float(moving_away_min_distance_px)
        self.state_ttl_seconds = float(state_ttl_seconds)
        self.relevant_zones = {zone.casefold() for zone in relevant_zones}
        self._memory: dict[int, _ObjectMemory] = {}
        self.last_transitions: list[
            tuple[int, ObjectLifecycleState, ObjectLifecycleState]
        ] = []
        self.last_expired_object_ids: tuple[int, ...] = ()

    def update(self, scene: SceneState) -> dict[int, ObjectStateSnapshot]:
        self.last_transitions = []
        associations = {
            association.object_track_id: association
            for association in scene.associations
        }
        for obj in scene.objects.values():
            memory = self._memory.get(obj.track_id)
            if memory is None:
                memory = _ObjectMemory(
                    object_track_id=obj.track_id,
                    object_class=obj.label,
                    state=ObjectLifecycleState.UNKNOWN,
                    last_seen=scene.timestamp,
                )
                self._memory[obj.track_id] = memory
            memory.object_class = obj.label
            memory.last_seen = scene.timestamp
            self._update_visible(memory, obj, associations.get(obj.track_id), scene)

        expired = [
            track_id
            for track_id, memory in self._memory.items()
            if track_id not in scene.objects
            and self._seconds_between(scene.timestamp, memory.last_seen) > self.state_ttl_seconds
        ]
        for track_id in expired:
            self._memory.pop(track_id, None)
        self.last_expired_object_ids = tuple(expired)
        return {
            track_id: self._snapshot(memory, scene.timestamp)
            for track_id, memory in self._memory.items()
        }

    def _update_visible(
        self,
        memory: _ObjectMemory,
        obj: TrackState,
        association: PersonObjectAssociation | None,
        scene: SceneState,
    ) -> None:
        score = association.association_score if association is not None else 0.0
        memory.held_probability = score
        memory.association_peak = max(memory.association_peak, score)
        carried_evidence = (
            association is not None
            and association.confirmed
            and score >= self.carried_score
            and association.duration_seconds >= self.carried_seconds
        )

        if carried_evidence:
            if memory.state is not ObjectLifecycleState.CARRIED:
                self._start_or_resume_carry(memory, association, scene.timestamp)
            else:
                memory.person_track_id = association.person_track_id
                memory.association_below_since = None
            return

        if memory.state is ObjectLifecycleState.CARRIED:
            if score > self.release_score:
                memory.association_below_since = None
                return
            if memory.association_below_since is None:
                memory.association_below_since = scene.timestamp
            if (
                self._seconds_between(scene.timestamp, memory.association_below_since)
                >= self.release_grace_seconds
            ):
                self._mark_released(memory, obj, scene.timestamp)

        if memory.release_detected:
            self._update_post_release(memory, obj, scene)

    def _start_or_resume_carry(
        self,
        memory: _ObjectMemory,
        association: PersonObjectAssociation,
        timestamp: datetime,
    ) -> None:
        self._transition(memory, ObjectLifecycleState.CARRIED)
        memory.person_track_id = association.person_track_id
        memory.object_was_carried = True
        memory.carried_since = association.first_seen
        memory.association_below_since = None
        memory.release_detected = False
        memory.release_timestamp = None
        memory.release_position = None
        memory.release_zone = None
        memory.stationary_since = None
        memory.stationary_duration = 0.0
        memory.person_distance = None
        memory.person_moving_away = False
        memory.distance_samples.clear()
        memory.association_peak = association.association_score

    def _mark_released(
        self,
        memory: _ObjectMemory,
        obj: TrackState,
        timestamp: datetime,
    ) -> None:
        self._transition(memory, ObjectLifecycleState.RELEASED)
        memory.release_detected = True
        memory.release_timestamp = timestamp
        memory.release_position = obj.centroid.model_copy(deep=True)
        memory.release_zone = obj.current_zone
        memory.association_below_since = None

    def _update_post_release(
        self,
        memory: _ObjectMemory,
        obj: TrackState,
        scene: SceneState,
    ) -> None:
        person = scene.persons.get(memory.person_track_id) if memory.person_track_id is not None else None
        if person is not None:
            memory.person_distance = hypot(
                person.centroid.x - obj.centroid.x,
                person.centroid.y - obj.centroid.y,
            )
            self._record_distance(memory, scene.timestamp, memory.person_distance)
            memory.person_moving_away = (
                memory.person_moving_away or self._is_moving_away(memory, scene.timestamp)
            )

        stationary_since = self._stationary_since(obj, memory.release_timestamp, scene.timestamp)
        if stationary_since is not None:
            memory.stationary_since = stationary_since
            memory.stationary_duration = self._seconds_between(scene.timestamp, stationary_since)
            if memory.state not in (
                ObjectLifecycleState.STATIONARY,
                ObjectLifecycleState.ABANDONED,
            ):
                self._transition(memory, ObjectLifecycleState.STATIONARY)
        else:
            memory.stationary_since = None
            memory.stationary_duration = 0.0
            if memory.state in (ObjectLifecycleState.STATIONARY, ObjectLifecycleState.ABANDONED):
                self._transition(memory, ObjectLifecycleState.MOVING)
            elif (
                memory.state is ObjectLifecycleState.RELEASED
                and memory.release_position is not None
                and hypot(
                    obj.centroid.x - memory.release_position.x,
                    obj.centroid.y - memory.release_position.y,
                ) > self.stationary_max_distance_px
            ):
                self._transition(memory, ObjectLifecycleState.MOVING)

        target_zone = (obj.current_zone or memory.release_zone or "").casefold()
        if (
            memory.state is ObjectLifecycleState.STATIONARY
            and target_zone in self.relevant_zones
            and memory.person_moving_away
        ):
            self._transition(memory, ObjectLifecycleState.ABANDONED)

    def _stationary_since(
        self,
        obj: TrackState,
        release_timestamp: datetime | None,
        timestamp: datetime,
    ) -> datetime | None:
        if release_timestamp is None:
            return None
        points = [
            point
            for point in obj.trajectory
            if release_timestamp <= point.timestamp <= timestamp
        ]
        if len(points) < 2:
            return None
        cutoff = timestamp - timedelta(seconds=self.stationary_seconds)
        before = [point for point in points if point.timestamp <= cutoff]
        after = [point for point in points if point.timestamp > cutoff]
        window: list[TrajectoryPoint] = ([before[-1]] if before else []) + after
        if len(window) < 2:
            return None
        if self._seconds_between(window[-1].timestamp, window[0].timestamp) < self.stationary_seconds:
            return None
        origin = window[0].position
        maximum_displacement = max(
            hypot(point.position.x - origin.x, point.position.y - origin.y)
            for point in window[1:]
        )
        return window[0].timestamp if maximum_displacement <= self.stationary_max_distance_px else None

    def _record_distance(self, memory: _ObjectMemory, timestamp: datetime, distance: float) -> None:
        if memory.distance_samples and memory.distance_samples[-1][0] == timestamp:
            memory.distance_samples[-1] = (timestamp, distance)
        else:
            memory.distance_samples.append((timestamp, distance))
        retention = max(self.moving_away_seconds * 3.0, self.moving_away_seconds + 1.0)
        cutoff = timestamp - timedelta(seconds=retention)
        while memory.distance_samples and memory.distance_samples[0][0] < cutoff:
            memory.distance_samples.popleft()

    def _is_moving_away(self, memory: _ObjectMemory, timestamp: datetime) -> bool:
        cutoff = timestamp - timedelta(seconds=self.moving_away_seconds)
        samples = list(memory.distance_samples)
        before = [sample for sample in samples if sample[0] <= cutoff]
        after = [sample for sample in samples if sample[0] > cutoff]
        window = ([before[-1]] if before else []) + after
        if len(window) < 2:
            return False
        if self._seconds_between(window[-1][0], window[0][0]) < self.moving_away_seconds:
            return False
        if window[-1][1] - window[0][1] < self.moving_away_min_distance_px:
            return False
        non_decreasing = sum(
            current[1] >= previous[1] - 1.0
            for previous, current in zip(window, window[1:])
        )
        return non_decreasing / (len(window) - 1) >= 0.75

    def _transition(self, memory: _ObjectMemory, target: ObjectLifecycleState) -> None:
        if target is memory.state:
            return
        allowed = self._ALLOWED_TRANSITIONS[memory.state]
        if target not in allowed:
            raise ValueError(f"Transición de objeto no permitida: {memory.state} -> {target}")
        previous = memory.state
        memory.previous_state = previous
        memory.state = target
        self.last_transitions.append((memory.object_track_id, previous, target))

    def _snapshot(self, memory: _ObjectMemory, timestamp: datetime) -> ObjectStateSnapshot:
        carried_end = memory.release_timestamp or timestamp
        carried_duration = (
            self._seconds_between(carried_end, memory.carried_since)
            if memory.carried_since is not None
            else 0.0
        )
        return ObjectStateSnapshot(
            object_track_id=memory.object_track_id,
            object_class=memory.object_class,
            state=memory.state,
            previous_state=memory.previous_state,
            person_track_id=memory.person_track_id,
            held_probability=memory.held_probability,
            association_peak=memory.association_peak,
            object_was_carried=memory.object_was_carried,
            carried_since=memory.carried_since,
            carried_duration=carried_duration,
            release_detected=memory.release_detected,
            release_timestamp=memory.release_timestamp,
            release_position=memory.release_position,
            release_zone=memory.release_zone,
            stationary_since=memory.stationary_since,
            stationary_duration=memory.stationary_duration,
            person_distance=memory.person_distance,
            person_moving_away=memory.person_moving_away,
            last_seen=memory.last_seen,
            updated_at=timestamp,
        )

    @staticmethod
    def _seconds_between(current: datetime, previous: datetime | None) -> float:
        if previous is None:
            return 0.0
        return max(0.0, (current - previous).total_seconds())

    def reset(self) -> None:
        self._memory.clear()
        self.last_transitions = []
        self.last_expired_object_ids = ()
