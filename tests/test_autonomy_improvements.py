import json
import sqlite3
from datetime import datetime
from types import SimpleNamespace

from app.camera.worker import VideoPipelineWorker
from app.config import settings
from app.models.event import EventModel
from app.models.scene import NormalizedPoint, ZoneDefinition
from app.storage.local_repository import SQLiteEventsRepository
from app.vision.class_config import (
    load_detection_classes,
    normalize_detection_classes,
    save_detection_classes,
)
from app.vision.zones import ZoneManager


def test_zone_calibration_preserves_other_cameras_and_reloads(tmp_path):
    path = tmp_path / "zones.json"
    path.write_text(
        json.dumps({"CAM_OTHER": {"zones": {"safe": [[0, 0], [1, 0], [1, 1]]}}}),
        encoding="utf-8",
    )
    zones = [
        ZoneDefinition(
            name="riverbank",
            priority=10,
            polygon=[
                NormalizedPoint(x=0, y=0.6),
                NormalizedPoint(x=1, y=0.6),
                NormalizedPoint(x=1, y=1),
            ],
        )
    ]

    ZoneManager.save_json(path, "CAM_TEST", zones)
    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded = ZoneManager.from_json(path, "CAM_TEST")

    assert "CAM_OTHER" in payload
    assert loaded.definitions() == zones


def test_dynamic_detection_classes_are_normalized_and_persisted(tmp_path):
    path = tmp_path / "classes.json"

    saved = save_detection_classes(path, ["Bottle", " costal de rafia ", "bottle"])
    loaded = load_detection_classes(path, ("person", "cup"))

    assert saved == ("person", "bottle", "costal de rafia")
    assert loaded == saved
    assert normalize_detection_classes(["person", "llanta"])[1] == "llanta"


def test_sqlite_stores_desistimiento_as_real_column(tmp_path):
    db_path = tmp_path / "events.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """CREATE TABLE events (
                id TEXT PRIMARY KEY, camera_id TEXT, started_at TEXT,
                ended_at TEXT, status TEXT, data_json TEXT
            )"""
        )
    repository = SQLiteEventsRepository(str(db_path))
    event = EventModel(
        id="event-1",
        camera_id="CAM_TEST",
        started_at=datetime.now(),
        desistimiento_confirmado=True,
        post_alert_outcome="RETRIEVED",
    )

    assert repository.save(event) is True
    with sqlite3.connect(db_path) as conn:
        value, outcome = conn.execute(
            "SELECT desistimiento_confirmado, post_alert_outcome FROM events WHERE id = ?",
            (event.id,),
        ).fetchone()

    assert value == 1
    assert outcome == "RETRIEVED"


def test_repository_hydrates_legacy_automatic_previews(tmp_path):
    repository = SQLiteEventsRepository(str(tmp_path / "events.db"))
    event = EventModel(
        id="12345678-abcd",
        camera_id="CAM_TEST",
        started_at=datetime.now(),
    )
    assert repository.save(event)
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    legacy = frames_dir / "auto-preview-12345678-1.jpg"
    legacy.write_bytes(b"jpeg")

    restored = repository.get_by_id(event.id)

    assert restored is not None
    assert restored.capture.frame_paths == [str(legacy.resolve())]


def test_post_alert_observation_marks_retrieved_object(monkeypatch):
    worker = VideoPipelineWorker()
    event = EventModel(
        id="event-nudge",
        camera_id="CAM_TEST",
        object_track_id=7,
        started_at=datetime.now(),
    )
    carried = SimpleNamespace(state=SimpleNamespace(value="CARRIED"))
    monkeypatch.setattr(
        VideoPipelineWorker,
        "current_scene",
        property(lambda self: SimpleNamespace(object_states={7: carried})),
    )
    try:
        worker._observe_post_alert(event)
    finally:
        worker.stop()

    assert event.desistimiento_confirmado is True
    assert event.post_alert_outcome == "RETRIEVED"
    assert event.metrics["desistimiento_confirmado"] is True


def test_event_frames_are_archived_with_stable_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "DATA_DIR", tmp_path)
    worker = VideoPipelineWorker()
    event = EventModel(id="event-frames", camera_id="CAM_TEST", started_at=datetime.now())
    try:
        urls = worker._persist_event_frames(event, [b"jpeg-one", b"jpeg-two"])
    finally:
        worker.stop()

    assert len(event.capture.frame_paths) == 2
    assert all((tmp_path / "frames" / f"event-{event.id}-{index}.jpg").is_file() for index in (1, 2))
    assert urls[0].endswith(f"event-{event.id}-1.jpg")


def test_dynamic_class_update_swaps_detector_after_embeddings_are_ready(tmp_path, monkeypatch):
    class FakeDetector:
        def __init__(self, **kwargs):
            self.monitored_classes = kwargs["monitored_classes"]

        def initialize(self):
            return True

        def save_prompt_embeddings(self, output_path):
            output_path.write_bytes(b"embeddings")
            return output_path

    monkeypatch.setattr("app.camera.worker.LocalDetector", FakeDetector)
    monkeypatch.setattr(settings, "DETECTION_CLASSES", settings.DETECTION_CLASSES)
    worker = VideoPipelineWorker()
    worker._prompt_embeddings_path = tmp_path / "prompts.npz"
    worker._dynamic_classes_path = tmp_path / "classes.json"
    try:
        worker._update_detection_classes(("person", "llanta"))
        status = worker.detection_class_status
    finally:
        worker.stop()

    assert status["status"] == "ready"
    assert status["classes"] == ["person", "llanta"]
    assert worker._prompt_embeddings_path.read_bytes() == b"embeddings"
    assert load_detection_classes(worker._dynamic_classes_path, ()) == ("person", "llanta")


def test_camera_reconnect_retries_until_source_opens(monkeypatch):
    class FakeCamera:
        def __init__(self, opens):
            self.opens = opens
            self.closed = False

        def open(self):
            return self.opens

        def close(self):
            self.closed = True

        def get_metadata(self):
            return {"type": "fake"}

    first = FakeCamera(False)
    second = FakeCamera(True)
    sources = iter((first, second))
    monkeypatch.setattr("app.camera.worker._create_camera_source", lambda: next(sources))
    monkeypatch.setattr(settings, "CAMERA_RECONNECT_SECONDS", 0.001)
    worker = VideoPipelineWorker()
    try:
        assert worker._open_camera_with_retry() is True
        assert worker._camera is second
        assert first.closed is True
    finally:
        worker.stop()
