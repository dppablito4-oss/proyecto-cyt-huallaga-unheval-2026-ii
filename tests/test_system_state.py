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
        pose_available=True,
        local_event_candidates=2,
        confirmed_local_events=1,
    )

    status = state.to_dict()
    assert status["association_candidates"] == 2
    assert status["confirmed_associations"] == 1
    assert status["active_pose_tracks"] == 1
    assert status["pose_available"] is True
    assert status["local_event_candidates"] == 2
    assert status["confirmed_local_events"] == 1


def test_system_state_counts_local_and_openai_event_paths():
    state = SystemState()

    state.record_analysis_result(confidence=0.9, openai_used=False, local_confirmed=True)
    state.record_analysis_result(confidence=0.6, openai_used=True, local_confirmed=False)

    status = state.to_dict()
    assert status["total_events_processed"] == 2
    assert status["events_confirmed_local"] == 1
    assert status["events_sent_openai"] == 1

    state.set_audio_source("local_template")
    assert state.to_dict()["last_audio_source"] == "local_template"


def test_system_state_exposes_isolated_performance_snapshot():
    state = SystemState()
    performance = {
        "capture_fps": 29.7,
        "detector_fps": 9.8,
        "cpu_percent": 18.2,
        "openai_percentage": 25.0,
    }

    state.set_performance(performance)
    performance["capture_fps"] = 0.0

    assert state.to_dict()["performance"] == {
        "capture_fps": 29.7,
        "detector_fps": 9.8,
        "cpu_percent": 18.2,
        "openai_percentage": 25.0,
    }
