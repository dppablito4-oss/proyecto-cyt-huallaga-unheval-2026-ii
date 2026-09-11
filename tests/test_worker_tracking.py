from datetime import datetime

import numpy as np

from app.camera.worker import VideoPipelineWorker
from app.models.event import BoundingBox, LocalDetection, LocalDetectionSummary
from app.models.tracking import Point, TrackedObject, TrackState
from app.state import system_state


def test_worker_publishes_tracking_summary_without_changing_detection_contract():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    detection = LocalDetection(
        label="person",
        confidence=0.9,
        bbox=BoundingBox(x1=10, y1=20, x2=30, y2=60),
    )
    summary = LocalDetectionSummary(persons=1, max_confidence=0.9, detections=[detection])
    tracked = TrackedObject(
        track_id=17,
        class_id=0,
        label="person",
        confidence=0.9,
        bbox=detection.bbox,
        centroid=Point(x=20, y=40),
        first_seen=timestamp,
        last_seen=timestamp,
    )
    track_state = TrackState(**tracked.model_dump())

    class FakeTracker:
        last_created_track_ids = (17,)
        last_expired_track_ids = ()

        def update(self, detections, timestamp, frame=None):
            assert detections == summary.detections
            return [tracked]

        def assign_zones(self, assignments):
            track_state.current_zone = assignments[17]

        @property
        def active_states(self):
            return [track_state]

        def reset(self):
            return None

    worker = VideoPipelineWorker()
    worker._tracker = FakeTracker()
    try:
        result = worker._update_tracking(summary, np.zeros((100, 100, 3)), timestamp)

        assert result.persons[17].track_id == tracked.track_id
        assert result.persons[17].current_zone == "observation"
        status = system_state.to_dict()
        assert status["active_tracks"] == 1
        assert status["active_track_ids"] == [17]
        assert status["active_person_tracks"] == 1
        assert status["zone_occupancy"] == {"observation": 1, "riverbank": 0}
        worker.stop()
        assert worker.current_scene.active_tracks == 0
    finally:
        system_state.set_scene_status(
            active_persons=0,
            active_objects=0,
            track_ids=[],
            zone_occupancy={},
            timestamp=timestamp,
        )
