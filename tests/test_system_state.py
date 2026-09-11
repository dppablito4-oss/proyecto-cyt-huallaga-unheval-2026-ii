from app.state import SystemState
from datetime import datetime


def test_system_state_exposes_multiclass_detection_counts():
    state = SystemState()

    state.set_detection_status(
        persons=2,
        objects=3,
        counts_by_label={"person": 2, "bottle": 2, "cup": 1},
    )

    status = state.to_dict()
    assert status["persons_detected"] == 2
    assert status["objects_detected"] == 3
    assert status["detection_counts"] == {"person": 2, "bottle": 2, "cup": 1}


def test_system_state_exposes_association_counters():
    state = SystemState()
    timestamp = datetime(2026, 9, 10, 12, 0, 0)

    state.set_scene_status(
        active_persons=1,
        active_objects=2,
        track_ids=[1, 8, 9],
        zone_occupancy={"riverbank": 3},
        timestamp=timestamp,
        association_candidates=2,
        confirmed_associations=1,
        active_pose_tracks=1,
    )

    status = state.to_dict()
    assert status["association_candidates"] == 2
    assert status["confirmed_associations"] == 1
    assert status["active_pose_tracks"] == 1
