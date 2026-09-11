"""Asociación persona–objeto con pose opcional y sin biometría."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import hypot

from app.models.association import AssociationSignals, PersonObjectAssociation
from app.models.scene import SceneState
from app.models.tracking import Point, TrackState


@dataclass(frozen=True)
class AssociationWeights:
    bbox_proximity: float = 0.35
    centroid_proximity: float = 0.25
    trajectory_similarity: float = 0.25
    temporal_consistency: float = 0.15
    hand_proximity: float = 0.25

    def __post_init__(self) -> None:
        values = (
            self.bbox_proximity,
            self.centroid_proximity,
            self.trajectory_similarity,
            self.temporal_consistency,
            self.hand_proximity,
        )
        if any(value < 0 for value in values) or sum(values) <= 0:
            raise ValueError("Los pesos de asociación deben ser no negativos y sumar más que cero.")


class AssociationScorer:
    """Calcula un score configurable a partir de geometría y movimiento."""

    def __init__(
        self,
        weights: AssociationWeights | None = None,
        max_distance_ratio: float = 1.5,
        hand_distance_ratio: float = 0.5,
        trajectory_points: int = 5,
    ):
        if max_distance_ratio <= 0:
            raise ValueError("max_distance_ratio debe ser mayor que cero.")
        if hand_distance_ratio <= 0:
            raise ValueError("hand_distance_ratio debe ser mayor que cero.")
        if trajectory_points < 2:
            raise ValueError("trajectory_points debe ser al menos 2.")
        self.weights = weights or AssociationWeights()
        self.max_distance_ratio = float(max_distance_ratio)
        self.hand_distance_ratio = float(hand_distance_ratio)
        self.trajectory_points = trajectory_points

    def score(
        self,
        person: TrackState,
        obj: TrackState,
        temporal_consistency: float,
    ) -> tuple[float, AssociationSignals]:
        signals = AssociationSignals(
            bbox_proximity=self._bbox_proximity(person, obj.centroid),
            centroid_proximity=self._centroid_proximity(person, obj),
            trajectory_similarity=self._trajectory_similarity(person, obj),
            temporal_consistency=max(0.0, min(1.0, temporal_consistency)),
            hand_proximity=self._hand_proximity(person, obj),
        )
        weighted_sum = (
            signals.bbox_proximity * self.weights.bbox_proximity
            + signals.centroid_proximity * self.weights.centroid_proximity
            + signals.trajectory_similarity * self.weights.trajectory_similarity
            + signals.temporal_consistency * self.weights.temporal_consistency
        )
        total_weight = (
            self.weights.bbox_proximity
            + self.weights.centroid_proximity
            + self.weights.trajectory_similarity
            + self.weights.temporal_consistency
        )
        if signals.hand_proximity is not None:
            weighted_sum += signals.hand_proximity * self.weights.hand_proximity
            total_weight += self.weights.hand_proximity
        return max(0.0, min(1.0, weighted_sum / total_weight)), signals

    def instantaneous_score(self, person: TrackState, obj: TrackState) -> float:
        """Score sin premio temporal, normalizado sobre señales instantáneas."""
        bbox_score = self._bbox_proximity(person, obj.centroid)
        centroid_score = self._centroid_proximity(person, obj)
        trajectory_score = self._trajectory_similarity(person, obj)
        hand_score = self._hand_proximity(person, obj)
        instant_weight = (
            self.weights.bbox_proximity
            + self.weights.centroid_proximity
            + self.weights.trajectory_similarity
        )
        if instant_weight <= 0:
            base_sum = 0.0
        else:
            base_sum = (
                bbox_score * self.weights.bbox_proximity
                + centroid_score * self.weights.centroid_proximity
                + trajectory_score * self.weights.trajectory_similarity
            )
        if hand_score is not None:
            base_sum += hand_score * self.weights.hand_proximity
            instant_weight += self.weights.hand_proximity
        if instant_weight <= 0:
            return 0.0
        return base_sum / instant_weight

    def _hand_proximity(self, person: TrackState, obj: TrackState) -> float | None:
        if person.pose is None or not person.pose.visible_wrists:
            return None
        distance = min(
            hypot(wrist.x - obj.centroid.x, wrist.y - obj.centroid.y)
            for wrist in person.pose.visible_wrists
        )
        diagonal = hypot(
            person.bbox.x2 - person.bbox.x1,
            person.bbox.y2 - person.bbox.y1,
        )
        normalization = max(1.0, diagonal * self.hand_distance_ratio)
        return max(0.0, 1.0 - distance / normalization)

    def _normalization_distance(self, person: TrackState) -> float:
        diagonal = hypot(
            person.bbox.x2 - person.bbox.x1,
            person.bbox.y2 - person.bbox.y1,
        )
        return max(1.0, diagonal * self.max_distance_ratio)

    def _bbox_proximity(self, person: TrackState, point: Point) -> float:
        horizontal = max(person.bbox.x1 - point.x, 0.0, point.x - person.bbox.x2)
        vertical = max(person.bbox.y1 - point.y, 0.0, point.y - person.bbox.y2)
        distance = hypot(horizontal, vertical)
        return max(0.0, 1.0 - distance / self._normalization_distance(person))

    def _centroid_proximity(self, person: TrackState, obj: TrackState) -> float:
        distance = hypot(
            person.centroid.x - obj.centroid.x,
            person.centroid.y - obj.centroid.y,
        )
        return max(0.0, 1.0 - distance / self._normalization_distance(person))

    def _trajectory_similarity(self, person: TrackState, obj: TrackState) -> float:
        person_vector = self._trajectory_vector(person)
        object_vector = self._trajectory_vector(obj)
        person_magnitude = hypot(*person_vector)
        object_magnitude = hypot(*object_vector)
        if person_magnitude == 0 and object_magnitude == 0:
            return 1.0
        if person_magnitude == 0 or object_magnitude == 0:
            return 0.0
        cosine = (
            person_vector[0] * object_vector[0]
            + person_vector[1] * object_vector[1]
        ) / (person_magnitude * object_magnitude)
        direction_similarity = max(0.0, min(1.0, cosine))
        speed_similarity = min(person_magnitude, object_magnitude) / max(
            person_magnitude,
            object_magnitude,
        )
        return direction_similarity * 0.65 + speed_similarity * 0.35

    def _trajectory_vector(self, track: TrackState) -> tuple[float, float]:
        points = track.trajectory[-self.trajectory_points :]
        if len(points) < 2:
            return 0.0, 0.0
        first = points[0].position
        last = points[-1].position
        return last.x - first.x, last.y - first.y


@dataclass
class _CandidateMemory:
    first_seen: datetime
    last_seen: datetime


class PersonObjectAssociationEngine:
    """Selecciona un posible dueño por objeto y exige persistencia temporal."""

    def __init__(
        self,
        enabled: bool = True,
        minimum_score: float = 0.65,
        minimum_duration: float = 0.5,
        scorer: AssociationScorer | None = None,
    ):
        if not 0.0 <= minimum_score <= 1.0:
            raise ValueError("minimum_score debe estar entre 0 y 1.")
        if minimum_duration < 0:
            raise ValueError("minimum_duration no puede ser negativa.")
        self.enabled = enabled
        self.minimum_score = float(minimum_score)
        self.minimum_duration = float(minimum_duration)
        self.scorer = scorer or AssociationScorer()
        self._memory: dict[tuple[int, int], _CandidateMemory] = {}

    def update(self, scene: SceneState) -> list[PersonObjectAssociation]:
        if not self.enabled or not scene.persons or not scene.objects:
            self._memory.clear()
            return []

        selected_pairs: list[tuple[TrackState, TrackState, float]] = []
        for obj in scene.objects.values():
            candidates = [
                (person, self.scorer.instantaneous_score(person, obj))
                for person in scene.persons.values()
            ]
            person, instant_score = max(candidates, key=lambda candidate: candidate[1])
            if instant_score >= self.minimum_score:
                selected_pairs.append((person, obj, instant_score))

        active_keys = {
            (person.track_id, obj.track_id)
            for person, obj, _ in selected_pairs
        }
        self._memory = {
            key: memory
            for key, memory in self._memory.items()
            if key in active_keys
        }

        associations: list[PersonObjectAssociation] = []
        for person, obj, _ in selected_pairs:
            key = (person.track_id, obj.track_id)
            memory = self._memory.get(key)
            if memory is None or scene.timestamp < memory.last_seen:
                memory = _CandidateMemory(scene.timestamp, scene.timestamp)
                self._memory[key] = memory
            else:
                memory.last_seen = scene.timestamp
            duration = max(0.0, (memory.last_seen - memory.first_seen).total_seconds())
            temporal = (
                1.0
                if self.minimum_duration == 0
                else min(1.0, duration / self.minimum_duration)
            )
            score, signals = self.scorer.score(person, obj, temporal)
            associations.append(
                PersonObjectAssociation(
                    person_track_id=person.track_id,
                    object_track_id=obj.track_id,
                    association_score=score,
                    signals=signals,
                    first_seen=memory.first_seen,
                    last_seen=memory.last_seen,
                    duration_seconds=duration,
                    confirmed=duration >= self.minimum_duration and score >= self.minimum_score,
                )
            )
        return associations

    def reset(self) -> None:
        self._memory.clear()
