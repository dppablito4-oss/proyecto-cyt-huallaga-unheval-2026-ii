from datetime import datetime

import numpy as np

from app.camera.worker import VideoPipelineWorker
from app.models.event import BoundingBox, LocalDetection, LocalDetectionSummary
from app.models.tracking import Point, TrackedObject
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

    class FakeTracker:
        last_created_track_ids = (17,)
        last_expired_track_ids = ()

        def update(self, detections, timestamp, frame=None):
            assert detections == summary.detections
            return [tracked]

        def reset(self):
            return None

    worker = VideoPipelineWorker()
    worker._tracker = FakeTracker()
    try:
        result = worker._update_tracking(summary, np.zeros((10, 10, 3)), timestamp)

        assert result == [tracked]
        status = system_state.to_dict()
        assert status["active_tracks"] == 1
        assert status["active_track_ids"] == [17]
    finally:
        system_state.set_tracking_status(active_tracks=0, track_ids=[])
