from datetime import datetime

import numpy as np

from app.models.association import AssociationSignals, PersonObjectAssociation
from app.models.event import BoundingBox
from app.models.scene import NormalizedPoint, SceneState, ZoneDefinition, ZoneState
from app.models.tracking import Point, TrackState, TrajectoryPoint
from app.vision.debug_overlay import VisionDebugOverlay
from app.vision.zones import ZoneManager


def test_debug_overlay_is_optional_and_never_modifies_raw_frame():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    frame = np.zeros((100, 120, 3), dtype=np.uint8)
    track = TrackState(
        track_id=4,
        class_id=0,
        label="person",
        confidence=0.9,
        first_seen=timestamp,
        last_seen=timestamp,
        bbox=BoundingBox(x1=20, y1=20, x2=60, y2=80),
        centroid=Point(x=40, y=50),
        trajectory=[
            TrajectoryPoint(position=Point(x=30, y=45), timestamp=timestamp),
            TrajectoryPoint(position=Point(x=40, y=50), timestamp=timestamp),
        ],
        current_zone="observation",
    )
    object_track = TrackState(
        track_id=9,
        class_id=39,
        label="bottle",
        confidence=0.85,
        first_seen=timestamp,
        last_seen=timestamp,
        bbox=BoundingBox(x1=48, y1=45, x2=58, y2=65),
        centroid=Point(x=53, y=55),
        current_zone="observation",
    )
    association = PersonObjectAssociation(
        person_track_id=4,
        object_track_id=9,
        association_score=0.82,
        signals=AssociationSignals(
            bbox_proximity=1,
            centroid_proximity=0.9,
            trajectory_similarity=0.7,
            temporal_consistency=1,
        ),
        first_seen=timestamp,
        last_seen=timestamp,
        duration_seconds=0.6,
        confirmed=True,
    )
    scene = SceneState(
        camera_id="CAM_TEST",
        timestamp=timestamp,
        persons={4: track},
        objects={9: object_track},
        zones={"observation": ZoneState(name="observation", track_ids=[4])},
        associations=[association],
    )
    manager = ZoneManager(
        "CAM_TEST",
        [
            ZoneDefinition(
                name="observation",
                polygon=[
                    NormalizedPoint(x=0, y=0),
                    NormalizedPoint(x=1, y=0),
                    NormalizedPoint(x=1, y=1),
                    NormalizedPoint(x=0, y=1),
                ],
            )
        ],
    )

    disabled_result = VisionDebugOverlay(enabled=False).annotate(frame, scene, manager)
    enabled_result = VisionDebugOverlay(enabled=True).annotate(frame, scene, manager)

    assert disabled_result is frame
    assert np.count_nonzero(frame) == 0
    assert enabled_result is not frame
    assert np.count_nonzero(enabled_result) > 0
