from datetime import datetime, timedelta

import pytest

from app.models.event import BoundingBox, LocalDetection
from app.models.detection import Detection
from app.models.tracking import Point
from app.vision.tracker import ByteTrackAdapter, NullTracker, create_tracker


def person_at(x: float, confidence: float = 0.9) -> LocalDetection:
    return LocalDetection(
        label="person",
        confidence=confidence,
        bbox=BoundingBox(x1=x, y1=10, x2=x + 30, y2=90),
    )


def bottle_at(x: float, confidence: float = 0.85) -> Detection:
    bbox = BoundingBox(x1=x, y1=20, x2=x + 15, y2=55)
    return Detection(
        class_id=39,
        label="bottle",
        confidence=confidence,
        bbox=bbox,
        centroid=Point(x=x + 7.5, y=37.5),
    )


def test_bytetrack_preserves_anonymous_id_and_history_between_frames():
    tracker = ByteTrackAdapter(
        track_activation_threshold=0.2,
        minimum_consecutive_frames=1,
        history_seconds=10,
    )
    started_at = datetime(2026, 9, 10, 12, 0, 0)

    assert tracker.update([person_at(10)], started_at) == []  # Track tentativo.
    second = tracker.update([person_at(12)], started_at + timedelta(seconds=1 / 30))
    third = tracker.update([person_at(14)], started_at + timedelta(seconds=2 / 30))

    assert len(second) == len(third) == 1
    assert second[0].track_id == third[0].track_id
    assert second[0].first_seen == second[0].last_seen
    state = tracker.active_states[0]
    assert state.track_id == second[0].track_id
    assert len(state.trajectory) == 2
    assert state.distance_travelled > 0
    assert state.visible is True


def test_bytetrack_tracks_two_people_with_different_ids():
    tracker = ByteTrackAdapter(
        track_activation_threshold=0.2,
        minimum_consecutive_frames=1,
    )
    started_at = datetime(2026, 9, 10, 12, 0, 0)

    tracker.update([person_at(10), person_at(300)], started_at)
    tracked = tracker.update(
        [person_at(12), person_at(298)],
        started_at + timedelta(seconds=1 / 30),
    )

    assert len(tracked) == 2
    assert len({item.track_id for item in tracked}) == 2


def test_bytetrack_preserves_multiclass_metadata():
    tracker = ByteTrackAdapter(
        track_activation_threshold=0.2,
        minimum_consecutive_frames=1,
    )
    started_at = datetime(2026, 9, 10, 12, 0, 0)

    tracker.update([bottle_at(100)], started_at)
    tracked = tracker.update(
        [bottle_at(102)],
        started_at + timedelta(seconds=1 / 30),
    )

    assert len(tracked) == 1
    assert tracked[0].class_id == 39
    assert tracked[0].label == "bottle"


def test_bytetrack_expires_local_history_after_ttl():
    tracker = ByteTrackAdapter(
        track_activation_threshold=0.2,
        minimum_consecutive_frames=1,
        track_ttl_seconds=1,
    )
    started_at = datetime(2026, 9, 10, 12, 0, 0)
    tracker.update([person_at(10)], started_at)
    tracked = tracker.update([person_at(11)], started_at + timedelta(seconds=1 / 30))
    track_id = tracked[0].track_id

    tracker.update([], started_at + timedelta(seconds=2))

    assert tracker.retained_states == []
    assert tracker.last_expired_track_ids == (track_id,)


def test_bytetrack_adds_zone_to_latest_history_point():
    tracker = ByteTrackAdapter(
        track_activation_threshold=0.2,
        minimum_consecutive_frames=1,
    )
    started_at = datetime(2026, 9, 10, 12, 0, 0)
    tracker.update([person_at(10)], started_at)
    tracked = tracker.update([person_at(12)], started_at + timedelta(seconds=1 / 30))

    tracker.assign_zones({tracked[0].track_id: "riverbank"})

    state = tracker.active_states[0]
    assert state.current_zone == "riverbank"
    assert state.trajectory[-1].zone == "riverbank"


def test_tracker_factory_supports_disabled_mode_and_rejects_unknown_type():
    assert isinstance(create_tracker(enabled=False), NullTracker)
    with pytest.raises(ValueError, match="no soportado"):
        create_tracker(tracker_type="unknown")
