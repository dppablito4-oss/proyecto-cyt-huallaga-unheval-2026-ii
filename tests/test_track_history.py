from datetime import datetime, timedelta

import pytest

from app.models.tracking import Point
from app.vision.track_history import TrackHistory


def test_track_history_derives_motion_and_prunes_old_points():
    started_at = datetime(2026, 9, 10, 12, 0, 0)
    history = TrackHistory(track_id=7, window_seconds=2)

    history.add(Point(x=0, y=0), started_at, zone="walkway")
    history.add(Point(x=10, y=0), started_at + timedelta(seconds=1), zone="walkway")
    history.add(Point(x=20, y=0), started_at + timedelta(seconds=2), zone="riverbank")
    history.add(Point(x=30, y=0), started_at + timedelta(seconds=3), zone="riverbank")

    assert [point.position.x for point in history.trajectory] == [10, 20, 30]
    assert history.visible_duration == 2.0
    assert history.velocity == (10.0, 0.0)
    assert history.speed == 10.0
    assert history.direction == Point(x=1.0, y=0.0)
    assert history.distance_travelled == 20.0
    assert history.current_zone == "riverbank"
    assert history.previous_zone == "walkway"


def test_track_history_rejects_out_of_order_observations():
    started_at = datetime(2026, 9, 10, 12, 0, 0)
    history = TrackHistory(track_id=3)
    history.add(Point(x=1, y=1), started_at)

    with pytest.raises(ValueError, match="cronológicas"):
        history.add(Point(x=2, y=2), started_at - timedelta(seconds=1))
