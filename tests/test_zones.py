import json
from datetime import datetime

from app.models.event import BoundingBox
from app.models.tracking import Point, TrackedObject
from app.vision.zones import ZoneManager


def tracked(track_id: int, bbox: BoundingBox) -> TrackedObject:
    timestamp = datetime(2026, 9, 10, 12, 0, 0)
    return TrackedObject(
        track_id=track_id,
        class_id=0,
        label="person",
        confidence=0.9,
        bbox=bbox,
        centroid=Point(x=(bbox.x1 + bbox.x2) / 2, y=(bbox.y1 + bbox.y2) / 2),
        first_seen=timestamp,
        last_seen=timestamp,
    )


def test_zone_manager_loads_normalized_polygons_and_applies_priority(tmp_path):
    path = tmp_path / "zones.json"
    path.write_text(
        json.dumps(
            {
                "CAM_TEST": {
                    "zones": {
                        "observation": [[0, 0], [1, 0], [1, 1], [0, 1]],
                        "riverbank": {
                            "polygon": [[0, 0.5], [1, 0.5], [1, 1], [0, 1]],
                            "priority": 10,
                        },
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    manager = ZoneManager.from_json(path, "CAM_TEST")
    upper = tracked(1, BoundingBox(x1=20, y1=10, x2=50, y2=30))
    lower = tracked(2, BoundingBox(x1=80, y1=60, x2=110, y2=90))

    assignments, states = manager.locate([upper, lower], (100, 200, 3))

    assert assignments == {1: "observation", 2: "riverbank"}
    assert states["observation"].track_ids == [1, 2]
    assert states["riverbank"].track_ids == [2]
    assert manager.pixel_polygons((100, 200, 3))["observation"].tolist() == [
        [0, 0], [199, 0], [199, 99], [0, 99]
    ]


def test_zone_manager_degrades_safely_when_config_is_missing(tmp_path):
    manager = ZoneManager.from_json(tmp_path / "missing.json", "CAM_TEST")
    item = tracked(5, BoundingBox(x1=0, y1=0, x2=10, y2=10))

    assignments, states = manager.locate([item], (100, 100, 3))

    assert assignments == {5: None}
    assert states == {}
