from datetime import datetime, timedelta

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.events.engine import EventEngine, EventScoreWeights
from app.events.object_state import ObjectStateMachine
from app.models.association import AssociationSignals, PersonObjectAssociation
from app.models.event import BoundingBox
from app.models.reasoning import EventCandidateState, ObjectLifecycleState
from app.models.scene import SceneState
from app.models.tracking import Point, TrackState, TrajectoryPoint


def make_track(
    track_id: int,
    label: str,
    timestamp: datetime,
    x: float,
    y: float = 100,
    zone: str | None = None,
    trajectory: list[tuple[datetime, float, float]] | None = None,
) -> TrackState:
    half_width = 30 if label == "person" else 8
    half_height = 70 if label == "person" else 8
    return TrackState(
        track_id=track_id,
        class_id=0 if label == "person" else 39,
        label=label,
        confidence=0.9,
        first_seen=timestamp - timedelta(seconds=2),
        last_seen=timestamp,
        bbox=BoundingBox(
            x1=x - half_width,
            y1=y - half_height,
            x2=x + half_width,
            y2=y + half_height,
        ),
        centroid=Point(x=x, y=y),
        current_zone=zone,
        trajectory=[
            TrajectoryPoint(position=Point(x=px, y=py), timestamp=observed_at, zone=zone)
            for observed_at, px, py in (trajectory or [(timestamp, x, y)])
        ],
    )


def make_association(
    started: datetime,
    timestamp: datetime,
    score: float = 0.9,
) -> PersonObjectAssociation:
    return PersonObjectAssociation(
        person_track_id=1,
        object_track_id=8,
        association_score=score,
        signals=AssociationSignals(
            bbox_proximity=0.9,
            centroid_proximity=0.9,
            trajectory_similarity=0.9,
            temporal_consistency=1.0,
        ),
        first_seen=started,
        last_seen=timestamp,
        duration_seconds=(timestamp - started).total_seconds(),
        confirmed=True,
    )


def make_scene(
    timestamp: datetime,
    person_x: float | None,
    object_x: float | None,
    association: PersonObjectAssociation | None = None,
    zone: str = "riverbank",
    trajectory: list[tuple[datetime, float, float]] | None = None,
) -> SceneState:
    person = make_track(1, "person", timestamp, person_x) if person_x is not None else None
    obj = (
        make_track(8, "bottle", timestamp, object_x, zone=zone, trajectory=trajectory)
        if object_x is not None
        else None
    )
    return SceneState(
        camera_id="CAM_TEST",
        timestamp=timestamp,
        persons={1: person} if person is not None else {},
        objects={8: obj} if obj is not None else {},
        associations=[association] if association is not None else [],
    )


def make_machine(**overrides) -> ObjectStateMachine:
    options = {
        "carried_score": 0.7,
        "carried_seconds": 0.5,
        "release_score": 0.35,
        "release_grace_seconds": 0.3,
        "stationary_seconds": 1.0,
        "stationary_max_distance_px": 5.0,
        "moving_away_seconds": 1.0,
        "moving_away_min_distance_px": 30.0,
        "state_ttl_seconds": 3.0,
        "relevant_zones": ("riverbank",),
    }
    options.update(overrides)
    return ObjectStateMachine(**options)


def carry_object(machine: ObjectStateMachine, started: datetime) -> None:
    carried_at = started + timedelta(seconds=0.6)
    association = make_association(started, carried_at)
    states = machine.update(make_scene(carried_at, 100, 105, association))
    assert states[8].state is ObjectLifecycleState.CARRIED


def release_object(machine: ObjectStateMachine, started: datetime) -> datetime:
    low_started = started + timedelta(seconds=1.0)
    machine.update(make_scene(low_started, 150, 110))
    released_at = started + timedelta(seconds=1.4)
    states = machine.update(
        make_scene(
            released_at,
            170,
            110,
            trajectory=[(released_at, 110, 100)],
        )
    )
    assert states[8].state is ObjectLifecycleState.RELEASED
    return released_at


def test_missing_carried_object_uses_short_grace_before_probable_release():
    started = datetime(2026, 9, 10, 12, 0, 0)
    machine = make_machine()
    carry_object(machine, started)

    states = machine.update(make_scene(started + timedelta(seconds=0.8), 140, None))

    assert states[8].state is ObjectLifecycleState.CARRIED
    assert states[8].release_detected is False

    states = machine.update(make_scene(started + timedelta(seconds=1.0), 180, None))

    assert states[8].state is ObjectLifecycleState.RELEASED
    assert states[8].release_detected is True
    assert states[8].release_zone == "riverbank"


def test_event_engine_confirms_carried_release_stationary_and_moving_away():
    started = datetime(2026, 9, 10, 12, 0, 0)
    machine = make_machine()
    engine = EventEngine(
        machine,
        ignore_threshold=0.35,
        confirm_threshold=0.75,
        relevant_zones=("riverbank",),
    )
    carried_at = started + timedelta(seconds=0.6)
    engine.update(make_scene(carried_at, 100, 105, make_association(started, carried_at)))
    engine.update(make_scene(started + timedelta(seconds=1.0), 150, 110))
    released_at = started + timedelta(seconds=1.4)
    initial = engine.update(
        make_scene(released_at, 170, 110, trajectory=[(released_at, 110, 100)])
    )
    settled_at = started + timedelta(seconds=2.5)
    confirmed = engine.update(
        make_scene(
            settled_at,
            270,
            112,
            trajectory=[
                (released_at, 110, 100),
                (settled_at, 112, 100),
            ],
        )
    )

    assert initial[0].state is EventCandidateState.UNCERTAIN
    assert confirmed[0].id == initial[0].id
    assert confirmed[0].state is EventCandidateState.CONFIRMED
    assert confirmed[0].event_type == "WASTE_DISPOSAL"
    assert confirmed[0].score == pytest.approx(0.8)
    assert confirmed[0].evidence.object_stationary is True
    assert confirmed[0].evidence.person_moving_away is True
    assert engine.object_states[8].state is ObjectLifecycleState.ABANDONED


def test_event_engine_confirms_fast_throw_into_relevant_zone():
    started = datetime(2026, 9, 10, 12, 0, 0)
    machine = make_machine(throw_min_speed_px_s=90, throw_min_distance_px=24)
    engine = EventEngine(machine, relevant_zones=("riverbank",))
    carried_at = started + timedelta(seconds=0.6)
    engine.update(make_scene(carried_at, 100, 105, make_association(started, carried_at)))
    engine.update(make_scene(started + timedelta(seconds=1.0), 150, 110))
    released_at = started + timedelta(seconds=1.4)
    engine.update(
        make_scene(released_at, 170, 110, trajectory=[(released_at, 110, 100)])
    )
    thrown_at = started + timedelta(seconds=1.7)
    thrown_scene = make_scene(
        thrown_at,
        180,
        150,
        trajectory=[
            (released_at, 110, 100),
            (thrown_at, 150, 100),
        ],
    )
    thrown_scene.objects[8].speed = 133.0

    candidates = engine.update(thrown_scene)

    assert candidates[0].state is EventCandidateState.CONFIRMED
    assert candidates[0].event_type == "WASTE_DISPOSAL"
    assert candidates[0].evidence.throw_detected is True
    assert candidates[0].score == pytest.approx(0.76)


def test_preexisting_stationary_object_never_creates_candidate():
    started = datetime(2026, 9, 10, 12, 0, 0)
    machine = make_machine()
    engine = EventEngine(machine, relevant_zones=("riverbank",))

    assert engine.update(make_scene(started, None, 110)) == []
    later = started + timedelta(seconds=2)
    candidates = engine.update(
        make_scene(
            later,
            140,
            111,
            trajectory=[(started, 110, 100), (later, 111, 100)],
        )
    )

    assert candidates == []
    assert engine.object_states[8].state is ObjectLifecycleState.UNKNOWN


def test_recollection_cancels_release_candidate():
    started = datetime(2026, 9, 10, 12, 0, 0)
    machine = make_machine()
    engine = EventEngine(machine, relevant_zones=("riverbank",))
    carried_at = started + timedelta(seconds=0.6)
    engine.update(make_scene(carried_at, 100, 105, make_association(started, carried_at)))
    engine.update(make_scene(started + timedelta(seconds=1.0), 150, 110))
    released_at = started + timedelta(seconds=1.4)
    assert engine.update(make_scene(released_at, 170, 110))

    recollected_at = started + timedelta(seconds=2.2)
    association = make_association(started + timedelta(seconds=1.6), recollected_at)
    candidates = engine.update(make_scene(recollected_at, 120, 115, association))

    assert candidates == []
    assert engine.object_states[8].state is ObjectLifecycleState.CARRIED
    assert engine.object_states[8].release_detected is False


def test_object_state_memory_expires_after_ttl():
    started = datetime(2026, 9, 10, 12, 0, 0)
    machine = make_machine(state_ttl_seconds=1.0)
    machine.update(make_scene(started, None, 110))

    states = machine.update(make_scene(started + timedelta(seconds=1.1), None, None))

    assert states == {}
    assert machine.last_expired_object_ids == (8,)


def test_event_engine_configuration_rejects_unsafe_thresholds():
    with pytest.raises(ValueError, match="0 <= ignore < confirm"):
        EventEngine(make_machine(), ignore_threshold=0.8, confirm_threshold=0.7)
    with pytest.raises(ValueError, match="sumar más que cero"):
        EventScoreWeights(0, 0, 0, 0, 0, 0)
    with pytest.raises(ValidationError, match="LOCAL_IGNORE_THRESHOLD"):
        Settings(LOCAL_IGNORE_THRESHOLD=0.8, LOCAL_CONFIRM_THRESHOLD=0.7)
    with pytest.raises(ValidationError, match="OBJECT_RELEASE_SCORE"):
        Settings(OBJECT_RELEASE_SCORE=0.8, OBJECT_CARRIED_SCORE=0.7)
    with pytest.raises(ValidationError, match="DETECTOR_BACKEND"):
        Settings(DETECTOR_BACKEND="unknown")
