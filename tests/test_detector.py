from datetime import datetime
from types import SimpleNamespace

import numpy as np
import pytest

from app.vision.detector import LocalDetector


def fake_box(class_id: int, confidence: float, xyxy: list[float]):
    return SimpleNamespace(
        cls=np.asarray([class_id]),
        conf=np.asarray([confidence]),
        xyxy=np.asarray([xyxy], dtype=np.float32),
    )


class FakeYolo:
    names = {0: "person", 2: "car", 24: "backpack", 39: "bottle", 41: "cup"}

    def __init__(self):
        self.calls = []

    def __call__(self, frame, **kwargs):
        self.calls.append(kwargs)
        return [
            SimpleNamespace(
                boxes=[
                    fake_box(0, 0.91, [10, 20, 50, 100]),
                    fake_box(39, 0.82, [60, 40, 80, 90]),
                    # Simula un backend que no respetó el filtro: debe descartarse.
                    fake_box(2, 0.99, [0, 0, 20, 20]),
                ]
            )
        ]


class FakeYoloE:
    def __init__(self):
        self.names = {0: "person"}
        self.loaded = []
        self.classes = []

    def load_prompt_embeddings(self, path):
        self.loaded.append(path)
        self.names = {0: "person", 1: "plastic bag"}

    def set_classes(self, classes):
        self.classes = list(classes)
        self.names = dict(enumerate(classes))


def test_detector_returns_configured_classes_with_ids_and_centroids():
    model = FakeYolo()
    detector = LocalDetector(
        confidence_threshold=0.4,
        monitored_classes=("person", "bottle", "cup"),
    )
    detector.model = model
    detector._initialized = True
    timestamp = datetime(2026, 9, 10, 12, 0, 0)

    result = detector.detect(np.zeros((120, 160, 3)), timestamp=timestamp)

    assert result.timestamp == timestamp
    assert [(item.class_id, item.label) for item in result.detections] == [
        (0, "person"),
        (39, "bottle"),
    ]
    assert result.detections[0].centroid.model_dump() == {"x": 30.0, "y": 60.0}
    assert result.counts_by_label == {"person": 1, "bottle": 1}
    assert model.calls[0]["classes"] == [0, 39, 41]
    assert model.calls[0]["conf"] == 0.4
    assert model.calls[0]["imgsz"] == 640


def test_detector_legacy_summary_contains_only_people():
    model = FakeYolo()
    detector = LocalDetector(monitored_classes=("person", "bottle"))
    detector.model = model
    detector._initialized = True

    summary = detector.detect_persons(np.zeros((120, 160, 3)))

    assert summary.persons == 1
    assert summary.max_confidence == 0.91
    assert len(summary.detections) == 1
    assert summary.detections[0].label == "person"


def test_detector_uses_stricter_threshold_for_people_than_waste():
    class LowConfidenceYolo(FakeYolo):
        names = {0: "person", 39: "bottle"}

        def __call__(self, frame, **kwargs):
            self.calls.append(kwargs)
            return [
                SimpleNamespace(
                    boxes=[
                        fake_box(0, 0.30, [10, 20, 50, 100]),
                        fake_box(39, 0.25, [60, 40, 80, 90]),
                    ]
                )
            ]

    model = LowConfidenceYolo()
    detector = LocalDetector(
        confidence_threshold=0.20,
        person_confidence_threshold=0.35,
        monitored_classes=("person", "bottle"),
    )
    detector.model = model
    detector._initialized = True
    result = detector.detect(np.zeros((120, 160, 3)))

    assert [(item.label, item.confidence) for item in result.detections] == [
        ("bottle", pytest.approx(0.25))
    ]


def test_detector_ignores_configured_classes_missing_from_model():
    model = FakeYolo()
    detector = LocalDetector(monitored_classes=("generic_waste",))
    detector.model = model
    detector._initialized = True

    result = detector.detect(np.zeros((120, 160, 3)))

    assert result.detections == []
    assert model.calls == []


def test_detector_validates_threshold_and_requires_classes():
    with pytest.raises(ValueError, match="entre 0 y 1"):
        LocalDetector(confidence_threshold=1.1)
    with pytest.raises(ValueError, match="al menos una clase"):
        LocalDetector(monitored_classes=())
    with pytest.raises(ValueError, match="al menos 160"):
        LocalDetector(image_size=128)
    with pytest.raises(ValueError, match="backend"):
        LocalDetector(backend="unknown")


def test_yoloe_detector_loads_precomputed_prompt_embeddings(tmp_path):
    prompt_path = tmp_path / "prompts.npz"
    prompt_path.touch()
    detector = LocalDetector(
        backend="yoloe",
        monitored_classes=("person", "plastic bag"),
        prompt_embeddings_path=prompt_path,
    )
    detector.model = FakeYoloE()

    detector._configure_open_vocabulary()

    assert detector.model.loaded == [prompt_path]
    assert detector.model.classes == []


def test_yoloe_detector_generates_prompts_when_cache_is_absent(tmp_path):
    detector = LocalDetector(
        backend="yoloe",
        monitored_classes=("person", "plastic bag"),
        prompt_embeddings_path=tmp_path / "missing.npz",
    )
    detector.model = FakeYoloE()

    detector._configure_open_vocabulary()

    assert detector.model.classes == ["person", "plastic bag"]
