"""Motor local que convierte estados de objetos en hipótesis explicables."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.events.object_state import ObjectStateMachine
from app.models.reasoning import (
    EventCandidate,
    EventCandidateState,
    EventEvidence,
    ObjectLifecycleState,
    ObjectStateSnapshot,
)
from app.models.scene import SceneState


@dataclass(frozen=True)
class EventScoreWeights:
    carried: float = 0.25
    release: float = 0.25
    target_zone: float = 0.20
    stationary: float = 0.15
    moving_away: float = 0.15
    throw: float = 0.25

    def __post_init__(self) -> None:
        values = (
            self.carried,
            self.release,
            self.target_zone,
            self.stationary,
            self.moving_away,
            self.throw,
        )
        if any(value < 0 for value in values) or sum(values) <= 0:
            raise ValueError("Los pesos de eventos deben ser no negativos y sumar más que cero.")


class EventEngine:
    """Evalúa continuamente SceneState sin persistir ni emitir alertas."""

    def __init__(
        self,
        object_state_machine: ObjectStateMachine,
        ignore_threshold: float = 0.35,
        confirm_threshold: float = 0.75,
        relevant_zones: tuple[str, ...] = ("riverbank", "river_edge", "water"),
        weights: EventScoreWeights | None = None,
    ):
        if not 0 <= ignore_threshold < confirm_threshold <= 1:
            raise ValueError("Los umbrales locales deben cumplir 0 <= ignore < confirm <= 1.")
        self.object_state_machine = object_state_machine
        self.ignore_threshold = float(ignore_threshold)
        self.confirm_threshold = float(confirm_threshold)
        self.relevant_zones = {zone.casefold() for zone in relevant_zones}
        self.weights = weights or EventScoreWeights()
        self._candidate_cycles: dict[int, tuple[datetime | None, str]] = {}
        self._candidate_states: dict[str, EventCandidateState] = {}
        self.object_states: dict[int, ObjectStateSnapshot] = {}
        self.last_created_candidate_ids: tuple[str, ...] = ()
        self.last_confirmed_candidate_ids: tuple[str, ...] = ()

    def update(self, scene: SceneState) -> list[EventCandidate]:
        self.object_states = self.object_state_machine.update(scene)
        candidates: list[EventCandidate] = []
        created: list[str] = []
        confirmed: list[str] = []
        active_objects: set[int] = set()

        for object_track_id, snapshot in sorted(self.object_states.items()):
            if not snapshot.object_was_carried or not snapshot.release_detected:
                continue
            active_objects.add(object_track_id)
            candidate_id, is_new = self._candidate_id(snapshot)
            if is_new:
                created.append(candidate_id)
            obj = scene.objects.get(object_track_id)
            current_zone = obj.current_zone if obj is not None else None
            evidence = self._build_evidence(snapshot, scene, current_zone)
            score = self._score(evidence)
            state = self._classify(score, snapshot.state, evidence)
            previous_state = self._candidate_states.get(candidate_id)
            if state is EventCandidateState.CONFIRMED and previous_state is not state:
                confirmed.append(candidate_id)
            self._candidate_states[candidate_id] = state
            candidates.append(
                EventCandidate(
                    id=candidate_id,
                    camera_id=scene.camera_id,
                    person_track_id=snapshot.person_track_id,
                    object_track_id=object_track_id,
                    object_class=snapshot.object_class,
                    event_type=(
                        "WASTE_DISPOSAL"
                        if state is EventCandidateState.CONFIRMED
                        else "OBJECT_RELEASE_CANDIDATE"
                    ),
                    score=score,
                    state=state,
                    evidence=evidence,
                    started_at=snapshot.release_timestamp or scene.timestamp,
                    updated_at=scene.timestamp,
                )
            )

        inactive = set(self._candidate_cycles) - active_objects
        for object_track_id in inactive:
            _, candidate_id = self._candidate_cycles.pop(object_track_id)
            self._candidate_states.pop(candidate_id, None)
        self.last_created_candidate_ids = tuple(created)
        self.last_confirmed_candidate_ids = tuple(confirmed)
        return candidates

    def _candidate_id(self, snapshot: ObjectStateSnapshot) -> tuple[str, bool]:
        cycle = snapshot.release_timestamp
        existing = self._candidate_cycles.get(snapshot.object_track_id)
        if existing is not None and existing[0] == cycle:
            return existing[1], False
        candidate_id = str(uuid.uuid4())
        self._candidate_cycles[snapshot.object_track_id] = (cycle, candidate_id)
        return candidate_id, True

    def _build_evidence(
        self,
        snapshot: ObjectStateSnapshot,
        scene: SceneState,
        current_zone: str | None,
    ) -> EventEvidence:
        timestamps = {}
        if snapshot.carried_since is not None:
            timestamps["carried_since"] = snapshot.carried_since
        if snapshot.release_timestamp is not None:
            timestamps["released_at"] = snapshot.release_timestamp
        if snapshot.stationary_since is not None:
            timestamps["stationary_since"] = snapshot.stationary_since
        return EventEvidence(
            person_present=snapshot.person_track_id in scene.persons,
            object_present=snapshot.object_track_id in scene.objects,
            object_was_carried=snapshot.object_was_carried,
            release_detected=snapshot.release_detected,
            release_zone=snapshot.release_zone,
            throw_detected=snapshot.throw_detected,
            object_stationary=snapshot.state
            in (ObjectLifecycleState.STATIONARY, ObjectLifecycleState.ABANDONED),
            stationary_duration=snapshot.stationary_duration,
            person_moving_away=snapshot.person_moving_away,
            person_distance=snapshot.person_distance,
            object_current_zone=current_zone,
            association_peak=snapshot.association_peak,
            carried_duration=snapshot.carried_duration,
            timestamps=timestamps,
        )

    def _score(self, evidence: EventEvidence) -> float:
        target_zone = (
            evidence.object_current_zone or evidence.release_zone or ""
        ).casefold()
        weighted_sum = (
            float(evidence.object_was_carried) * self.weights.carried
            + float(evidence.release_detected) * self.weights.release
            + float(target_zone in self.relevant_zones) * self.weights.target_zone
            + float(evidence.object_stationary) * self.weights.stationary
            + float(evidence.person_moving_away) * self.weights.moving_away
            + float(evidence.throw_detected) * self.weights.throw
        )
        total = sum(
            (
                self.weights.carried,
                self.weights.release,
                self.weights.target_zone,
                self.weights.stationary,
                self.weights.moving_away,
                self.weights.throw,
            )
        )
        return max(0.0, min(1.0, weighted_sum / total))

    def _classify(
        self,
        score: float,
        object_state: ObjectLifecycleState,
        evidence: EventEvidence,
    ) -> EventCandidateState:
        if score < self.ignore_threshold:
            return EventCandidateState.IGNORE
        if (
            score >= self.confirm_threshold
            and (
                object_state is ObjectLifecycleState.ABANDONED
                or evidence.throw_detected
            )
        ):
            return EventCandidateState.CONFIRMED
        return EventCandidateState.UNCERTAIN

    def reset(self) -> None:
        self.object_state_machine.reset()
        self._candidate_cycles.clear()
        self._candidate_states.clear()
        self.object_states = {}
        self.last_created_candidate_ids = ()
        self.last_confirmed_candidate_ids = ()
