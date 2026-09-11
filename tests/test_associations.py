from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.models.event import BoundingBox
from app.models.pose import PosePoint, PoseState
from app.models.scene import SceneState
from app.models.tracking import Point, TrackState, TrajectoryPoint
from app.vision.associations import (
    AssociationScorer,
    AssociationWeights,
    PersonObjectAssociationEngine,
)


def make_track(
    track_id: int,
    label: str,
    bbox: BoundingBox,
    timestamp: datetime,
    movement: tuple[float, float] = (10.0, 0.0),
) -> TrackState:
    centroid = Point(x=(bbox.x1 + bbox.x2) / 2, y=(bbox.y1 + bbox.y2) / 2)
    previous = Point(x=centroid.x - movement[0], y=centroid.y - movement[1])
    return TrackState(
        track_id=track_id,
        class_id=0 if label == "person" else 39,
        label=label,
        confidence=0.9,
        first_seen=timestamp - timedelta(seconds=1),
        last_seen=timestamp,
        bbox=bbox,
        centroid=centroid,
        trajectory=[
            TrajectoryPoint(position=previous, timestamp=timestamp - timedelta(seconds=0.1)),
            TrajectoryPoint(position=centroid, timestamp=timestamp),
        ],
    )


def make_scene(timestamp: datetime, persons: list[TrackState], objects: list[TrackState]):
    return SceneState(
        camera_id="CAM_TEST",
        timestamp=timestamp,
        persons={track.track_id: track for track in persons},
        objects={track.track_id: track for track in objects},
    )


def test_association_requires_temporal_persistence_before_confirmation():
    started = datetime(2026, 9, 10, 12, 0, 0)
    engine = PersonObjectAssociationEngine(minimum_score=0.65, minimum_duration=0.5)
    person = make_track(1, "person", BoundingBox(x1=0, y1=0, x2=100, y2=200), started)
    bottle = make_track(8, "bottle", BoundingBox(x1=65, y1=80, x2=85, y2=120), started)

    initial = engine.update(make_scene(started, [person], [bottle]))
    confirmed = engine.update(
        make_scene(started + timedelta(seconds=0.6), [person], [bottle])
    )

    assert len(initial) == 1
    assert initial[0].confirmed is False
    assert initial[0].duration_seconds == 0
    assert confirmed[0].confirmed is True
    assert confirmed[0].duration_seconds == pytest.approx(0.6)
    assert confirmed[0].signals.temporal_consistency == 1.0


def test_association_rejects_spatially_distant_object():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    engine = PersonObjectAssociationEngine(minimum_score=0.65)
    person = make_track(1, "person", BoundingBox(x1=0, y1=0, x2=100, y2=200), timestamp)
    bottle = make_track(
        8,
        "bottle",
        BoundingBox(x1=900, y1=80, x2=920, y2=120),
        timestamp,
    )

    assert engine.update(make_scene(timestamp, [person], [bottle])) == []


def test_association_selects_best_person_and_resets_duration_when_owner_changes():
    started = datetime(2026, 9, 10, 12, 0, 0)
    engine = PersonObjectAssociationEngine(minimum_score=0.65, minimum_duration=0.5)
    left = make_track(1, "person", BoundingBox(x1=0, y1=0, x2=100, y2=200), started)
    right = make_track(2, "person", BoundingBox(x1=300, y1=0, x2=400, y2=200), started)
    bottle_left = make_track(8, "bottle", BoundingBox(x1=65, y1=80, x2=85, y2=120), started)
    first = engine.update(make_scene(started, [left, right], [bottle_left]))

    changed_at = started + timedelta(seconds=0.6)
    bottle_right = make_track(
        8,
        "bottle",
        BoundingBox(x1=320, y1=80, x2=340, y2=120),
        changed_at,
    )
    changed = engine.update(make_scene(changed_at, [left, right], [bottle_right]))

    assert first[0].person_track_id == 1
    assert changed[0].person_track_id == 2
    assert changed[0].duration_seconds == 0
    assert changed[0].confirmed is False


def test_trajectory_similarity_rewards_joint_motion():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    scorer = AssociationScorer()
    person = make_track(1, "person", BoundingBox(x1=0, y1=0, x2=100, y2=200), timestamp)
    same = make_track(8, "bottle", BoundingBox(x1=60, y1=80, x2=80, y2=120), timestamp)
    opposite = make_track(
        9,
        "bottle",
        BoundingBox(x1=60, y1=80, x2=80, y2=120),
        timestamp,
        movement=(-10, 0),
    )

    _, same_signals = scorer.score(person, same, temporal_consistency=0)
    _, opposite_signals = scorer.score(person, opposite, temporal_consistency=0)

    assert same_signals.trajectory_similarity == 1.0
    assert opposite_signals.trajectory_similarity == pytest.approx(0.35)


def test_hand_proximity_is_optional_and_improves_association_signal():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    scorer = AssociationScorer()
    person = make_track(1, "person", BoundingBox(x1=0, y1=0, x2=100, y2=200), timestamp)
    bottle = make_track(8, "bottle", BoundingBox(x1=75, y1=85, x2=85, y2=95), timestamp)

    score_without_pose, signals_without_pose = scorer.score(person, bottle, temporal_consistency=0)
    person.pose = PoseState(
        track_id=1,
        timestamp=timestamp,
        confidence=0.95,
        right_wrist=PosePoint(x=80, y=90, visibility=0.95),
    )
    score_with_pose, signals_with_pose = scorer.score(person, bottle, temporal_consistency=0)

    assert signals_without_pose.hand_proximity is None
    assert signals_with_pose.hand_proximity == 1.0
    assert score_with_pose > score_without_pose


def test_association_configuration_is_validated():
    with pytest.raises(ValueError, match="sumar más que cero"):
        AssociationWeights(0, 0, 0, 0, 0)
    with pytest.raises(ValueError, match="entre 0 y 1"):
        PersonObjectAssociationEngine(minimum_score=1.1)
    with pytest.raises(ValidationError, match="peso de asociación"):
        Settings(
            ASSOCIATION_BBOX_WEIGHT=0,
            ASSOCIATION_CENTROID_WEIGHT=0,
            ASSOCIATION_TRAJECTORY_WEIGHT=0,
            ASSOCIATION_TEMPORAL_WEIGHT=0,
            ASSOCIATION_HAND_WEIGHT=0,
        )
