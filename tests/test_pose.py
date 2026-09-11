from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

from app.models.event import BoundingBox
from app.models.pose import PosePoint, PoseState
from app.models.scene import SceneState
from app.models.tracking import Point, TrackState
from app.vision.pose import MediaPipePoseAnalyzer, NullPoseAnalyzer, create_pose_analyzer


def make_track(track_id: int, label: str, timestamp: datetime, zone: str | None = None) -> TrackState:
    bbox = BoundingBox(x1=10, y1=10, x2=90, y2=190)
    return TrackState(
        track_id=track_id,
        class_id=0 if label == "person" else 39,
        label=label,
        confidence=0.9,
        first_seen=timestamp,
        last_seen=timestamp,
        bbox=bbox,
        centroid=Point(x=50, y=100),
        current_zone=zone,
    )


def make_analyzer(**overrides) -> MediaPipePoseAnalyzer:
    options = {
        "model_path": Path("unused.task"),
        "trigger_zones": ("observation",),
        "fps": 5,
        "result_ttl_seconds": 0.5,
    }
    options.update(overrides)
    return MediaPipePoseAnalyzer(**options)


def fake_pose(person: TrackState, timestamp: datetime) -> PoseState:
    return PoseState(
        track_id=person.track_id,
        timestamp=timestamp,
        confidence=0.9,
        left_wrist=PosePoint(x=30, y=80, visibility=0.9),
        right_wrist=PosePoint(x=70, y=80, visibility=0.9),
    )


def test_pose_only_runs_for_a_relevant_reason_and_respects_rate_and_ttl():
    started = datetime(2026, 9, 10, 12, 0, 0)
    frame = np.zeros((200, 100, 3), dtype=np.uint8)
    person = make_track(1, "person", started)
    scene = SceneState(camera_id="CAM_TEST", timestamp=started, persons={1: person})
    analyzer = make_analyzer()
    calls = []
    analyzer._analyze_person = lambda frame, track, timestamp: calls.append(track.track_id) or fake_pose(track, timestamp)

    assert analyzer.update(frame, scene) == {}
    assert calls == []

    person.current_zone = "observation"
    first = analyzer.update(frame, scene)
    scene.timestamp = started + timedelta(seconds=0.1)
    cached = analyzer.update(frame, scene)
    person.current_zone = None
    scene.timestamp = started + timedelta(seconds=0.6)
    expired = analyzer.update(frame, scene)

    assert list(first) == [1]
    assert list(cached) == [1]
    assert calls == [1]
    assert expired == {}


def test_near_object_and_future_event_request_activate_pose():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    frame = np.zeros((220, 300, 3), dtype=np.uint8)
    person = make_track(1, "person", timestamp)
    near_object = make_track(8, "bottle", timestamp)
    near_object.bbox = BoundingBox(x1=95, y1=80, x2=105, y2=100)
    near_object.centroid = Point(x=100, y=90)
    scene = SceneState(
        camera_id="CAM_TEST",
        timestamp=timestamp,
        persons={1: person},
        objects={8: near_object},
    )
    analyzer = make_analyzer()
    analyzer._analyze_person = lambda frame, track, timestamp: fake_pose(track, timestamp)

    assert list(analyzer.update(frame, scene)) == [1]

    analyzer.reset()
    scene.objects = {}
    assert list(analyzer.update(frame, scene, force_track_ids={1})) == [1]


def test_pose_fails_safe_when_model_is_missing():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    person = make_track(1, "person", timestamp, zone="observation")
    scene = SceneState(camera_id="CAM_TEST", timestamp=timestamp, persons={1: person})
    analyzer = make_analyzer(model_path=Path("definitely-missing.task"))

    assert analyzer.update(np.zeros((200, 100, 3), dtype=np.uint8), scene) == {}
    assert analyzer.available is False


def test_disabled_pose_factory_has_no_external_dependency():
    analyzer = create_pose_analyzer(enabled=False)

    assert isinstance(analyzer, NullPoseAnalyzer)
    assert analyzer.available is False
