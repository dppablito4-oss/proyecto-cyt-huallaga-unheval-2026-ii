from datetime import datetime, timedelta

import numpy as np

from app.camera.worker import VideoPipelineWorker
from app.models.detection import DetectionFrame
from app.models.event import BoundingBox
from app.models.tracking import Point, TrackedObject, TrackState
from app.state import system_state


def test_worker_publishes_confirmed_person_object_association():
    started = datetime(2026, 9, 10, 12, 0, 0)
    person_bbox = BoundingBox(x1=10, y1=10, x2=80, y2=95)
    object_bbox = BoundingBox(x1=55, y1=55, x2=70, y2=80)
    person_object = TrackedObject(
        track_id=1,
        class_id=0,
        label="person",
        confidence=0.9,
        bbox=person_bbox,
        centroid=Point(x=45, y=52.5),
        first_seen=started,
        last_seen=started,
    )
    bottle_object = TrackedObject(
        track_id=8,
        class_id=39,
        label="bottle",
        confidence=0.85,
        bbox=object_bbox,
        centroid=Point(x=62.5, y=67.5),
        first_seen=started,
        last_seen=started,
    )
    states = [
        TrackState(**person_object.model_dump()),
        TrackState(**bottle_object.model_dump()),
    ]

    class FakeTracker:
        last_created_track_ids = ()
        last_expired_track_ids = ()

        def update(self, detections, timestamp, frame=None):
            return [person_object, bottle_object]

        def assign_zones(self, assignments):
            for state in states:
                state.current_zone = assignments[state.track_id]

        @property
        def active_states(self):
            return states

        def reset(self):
            return None

    worker = VideoPipelineWorker()
    worker._tracker = FakeTracker()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    empty_detection = DetectionFrame(timestamp=started)
    try:
        initial = worker._update_tracking(empty_detection, frame, started)
        confirmed = worker._update_tracking(
            empty_detection,
            frame,
            started + timedelta(seconds=0.6),
        )

        assert initial.associations[0].confirmed is False
        assert confirmed.associations[0].confirmed is True
        assert confirmed.associations[0].person_track_id == 1
        assert confirmed.associations[0].object_track_id == 8
        status = system_state.to_dict()
        assert status["association_candidates"] == 1
        assert status["confirmed_associations"] == 1
    finally:
        worker.stop()
