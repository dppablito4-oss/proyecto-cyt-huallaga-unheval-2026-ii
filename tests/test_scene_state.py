from datetime import datetime

from app.models.event import BoundingBox
from app.models.association import AssociationSignals, PersonObjectAssociation
from app.models.scene import SceneState, ZoneState
from app.models.pose import PosePoint, PoseState
from app.models.tracking import Point, TrackState


def make_state(track_id: int, label: str, timestamp: datetime) -> TrackState:
    return TrackState(
        track_id=track_id,
        class_id=0,
        label=label,
        confidence=0.9,
        first_seen=timestamp,
        last_seen=timestamp,
        bbox=BoundingBox(x1=10, y1=10, x2=30, y2=50),
        centroid=Point(x=20, y=30),
        current_zone="observation",
    )


def test_scene_state_separates_people_objects_and_zones():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    scene = SceneState(camera_id="CAM_TEST")

    scene.update(
        [make_state(1, "person", timestamp), make_state(2, "bottle", timestamp)],
        {"observation": ZoneState(name="observation", track_ids=[1, 2])},
        timestamp,
    )

    assert list(scene.persons) == [1]
    assert list(scene.objects) == [2]
    assert scene.zone_for_track(1) == "observation"
    assert scene.zones["observation"].occupancy == 2
    assert scene.active_tracks == 2


def test_scene_state_drops_tracks_that_are_no_longer_visible():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    hidden = make_state(1, "person", timestamp)
    hidden.visible = False
    scene = SceneState(camera_id="CAM_TEST")

    scene.update([hidden], {}, timestamp)

    assert scene.persons == {}
    assert scene.active_tracks == 0


def test_scene_state_exposes_object_association():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    scene = SceneState(camera_id="CAM_TEST")
    association = PersonObjectAssociation(
        person_track_id=1,
        object_track_id=2,
        association_score=0.8,
        signals=AssociationSignals(
            bbox_proximity=1,
            centroid_proximity=0.8,
            trajectory_similarity=0.7,
            temporal_consistency=1,
        ),
        first_seen=timestamp,
        last_seen=timestamp,
        duration_seconds=0.5,
        confirmed=True,
    )

    scene.set_associations([association])

    assert scene.association_for_object(2) == association
    assert scene.association_for_object(99) is None


def test_scene_state_attaches_only_current_person_poses():
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    scene = SceneState(
        camera_id="CAM_TEST",
        timestamp=timestamp,
        persons={1: make_state(1, "person", timestamp)},
    )
    pose = PoseState(
        track_id=1,
        timestamp=timestamp,
        confidence=0.9,
        left_wrist=PosePoint(x=18, y=30, visibility=0.9),
    )

    scene.set_poses({1: pose, 99: pose.model_copy(update={"track_id": 99})})

    assert scene.persons[1].pose == pose
    assert 99 not in scene.persons
